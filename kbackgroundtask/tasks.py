from huey import crontab  # type: ignore
from huey.contrib.djhuey import db_periodic_task  # type: ignore
from django.core.management import call_command


@db_periodic_task(crontab(minute=5))
def kill_unresponsive_tasks_task():
    call_command("kill_unresponsive_tasks")
