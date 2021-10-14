import logging
from datetime import timedelta
from typing import List
from kcommunication.helpers import send_email
from kcommunication.helpers import csv_to_list
from django.conf import settings
from django.core.management.base import CommandParser
from django.utils.html import strip_tags
from django.utils.timezone import now
from kbackgroundtask.models import BackgroundTask
from jutil.command import SafeCommand
from project.redis_services import get_redis_instance


logger = logging.getLogger(__name__)


class Command(SafeCommand):
    help = "Kills unresponsive tasks"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--email", type=str)
        parser.add_argument("--no-email", action="store_true")
        parser.add_argument("--max-runtime-minutes", type=int, default=30)
        parser.add_argument("--max-consecutive-locks", type=int, default=2)

    def do(self, *args, **options):  # noqa
        time_now = now()
        emails = csv_to_list(options["email"]) if options["email"] else settings.ADMINS

        max_minutes = options["max_runtime_minutes"]
        old = time_now - timedelta(minutes=max_minutes)

        # list tasks stuck in 'executing' state
        exec_tasks: List[BackgroundTask] = list(
            BackgroundTask.objects.filter(created__lt=old, signal__in=["executing"])
        )

        # list tasks which are stuck in locked state
        locked_tasks: List[BackgroundTask] = []
        max_locks = options["max_consecutive_locks"]
        for bt in list(
            BackgroundTask.objects.filter(created__gt=old, signal="locked")
            .order_by("name")
            .distinct("name")
        ):
            assert isinstance(bt, BackgroundTask)
            qs: List[BackgroundTask] = list(
                BackgroundTask.objects.filter(name=bt.name).order_by("-id")[:max_locks]
            )
            qs_locked = [bt for bt in qs if bt.signal == "locked"]
            if len(qs_locked) == max_locks:
                bt = qs[0]
                locked_tasks.append(bt)

        # if we have executing tasks running too long time or stuck in locked state, flush Redis locks
        if exec_tasks or locked_tasks:
            redis = get_redis_instance()
            redis.flushdb()
            logger.info("Redis flushed")
            for bt in exec_tasks:
                assert isinstance(bt, BackgroundTask)
                bt.error = (
                    f"Set as failed since runtime {bt.runtime} exceeds {max_minutes}m. Locks flushed."
                )
                bt.signal = "error"
                bt.last_modified = time_now
                bt.save()
                logger.info("%s: %s", bt, bt.error)
            for bt in locked_tasks:
                assert isinstance(bt, BackgroundTask)
                bt.error = "Set as canceled since task looks stuck in locked state. Locks flushed."
                bt.signal = "canceled"
                bt.last_modified = time_now
                bt.save()
                logger.info("%s: %s", bt, bt.error)

            print("To:", emails)
            subject = f"{settings.SITE_NAME} background tasks unresponsive"
            print("Subject:", subject)
            list_url = settings.API_URL + "/admin/customers/backgroundtask/?state=1"
            html = f'<p><a href="{list_url}">{list_url}</a></p>\n'
            html += '<p>Tasks stuck in "executing" state (now released):</p><ul>\n'
            for bt in exec_tasks:
                assert isinstance(bt, BackgroundTask)
                html += f"  <li>{bt.name} ({bt.signal} {time_now - bt.created})</li>\n"
            if not exec_tasks:
                html += "<li>(no tasks)</li>"
            html += "</ul>\n"
            html += '<p>Tasks stuck in "locked" state (now released):</p><ul>\n'
            for bt in locked_tasks:
                assert isinstance(bt, BackgroundTask)
                html += f"  <li>{bt.name} ({bt.signal} {time_now - bt.created})</li>\n"
            if not locked_tasks:
                html += "<li>(no tasks)</li>"
            html += "</ul>\n"
            text = strip_tags(html.replace("<br>", "\n"))
            print(html)
            if not options["no_email"]:
                if exec_tasks:
                    send_email(emails, subject, text, html)
                else:
                    print("Not sending email since no tasks in error state")
