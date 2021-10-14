from typing import Optional, Sequence

from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from jutil.modelfields import SafeCharField, SafeTextField
from datetime import datetime, timedelta
import logging
from time import sleep

logger = logging.getLogger(__name__)


class BackgroundTaskManager(models.Manager):
    def filter_unfinished(self):
        return self.filter(signal__in=BackgroundTask.UNFINISHED_TASK_SIGNALS)

    def filter_executing(self):
        return self.filter(signal="executing")

    def wait_tasks(
        self,
        wait_s: int = 0,
        signals: Optional[Sequence[str]] = None,
        poll_s: float = 1.0,
        verbose: bool = True,
    ):
        """
        Waits for tasks to finish specified signal(s) state.
        :param wait_s: Max seconds to wait. Default: 0
        :param signals: Signals to wait. Default: ['executing']
        :param poll_s: Polling interval seconds. Default: 1.0
        :param verbose: Print logger.info output about wait.
        :return: BackgroundTask in specified signal or None if all finished
        """
        if signals is None:
            signals = ["executing"]
        task: Optional[BackgroundTask] = None
        time_now = now()
        end_time = time_now + timedelta(seconds=wait_s) if wait_s else time_now
        while time_now <= end_time:
            task = self.all().filter(signal__in=signals).first()
            if task is None:
                break
            if verbose:
                logger.info(
                    "Waiting %s tasks %s: %s", signals, end_time - time_now, task
                )
            sleep(poll_s)
            time_now = now()
        return task


class BackgroundTask(models.Model):
    ACTIVE_TASK_SIGNALS = ["executing", "scheduled", "retrying"]
    UNFINISHED_TASK_SIGNALS = ACTIVE_TASK_SIGNALS + ["error"]

    objects = BackgroundTaskManager()
    name = SafeCharField(_("name"), max_length=64, db_index=True)
    task_id = SafeCharField(_("task"), max_length=64, db_index=True)
    created = models.DateTimeField(_("created"), default=now, blank=True, db_index=True)
    last_modified = models.DateTimeField(
        verbose_name=_("last modified"),
        auto_now=True,
        db_index=True,
        editable=False,
        blank=True,
    )
    signal = SafeCharField(_("signal"), max_length=64, db_index=True)
    executing = models.DateTimeField(
        _("executing"), default=None, blank=True, null=True, db_index=True
    )
    complete = models.DateTimeField(
        _("complete"), default=None, blank=True, null=True, db_index=True
    )
    locked = models.DateTimeField(
        _("locked"), default=None, blank=True, null=True, db_index=True
    )
    scheduled = models.DateTimeField(
        _("scheduled"), default=None, blank=True, null=True, db_index=True
    )
    retrying = models.DateTimeField(
        _("retrying"), default=None, blank=True, null=True, db_index=True
    )
    canceled = models.DateTimeField(
        _("canceled"), default=None, blank=True, null=True, db_index=True
    )
    revoked = models.DateTimeField(
        _("revoked"), default=None, blank=True, null=True, db_index=True
    )
    failed = models.DateTimeField(
        _("failed"), default=None, blank=True, null=True, db_index=True
    )
    error = SafeTextField(_("error"), blank=True)

    class Meta:
        verbose_name = _("background task")
        verbose_name_plural = _("background tasks")

    def __str__(self):
        return f"{self.signal} {self.name} ({self.task_id})"

    def is_newer_ok(self) -> bool:
        """
        Returns True if there is newer task with same name that has succeed.
        """
        return (
            bool(self.complete)
            or BackgroundTask.objects.filter(
                name=self.name, complete__gt=self.created
            ).exists()
        )

    @property
    def error_brief(self) -> str:
        if self.error:
            lines = str(self.error).strip().split("\n")
            return lines.pop()
        return ""

    error_brief.fget.short_description = _("error")  # type: ignore

    @property
    def end_time(self) -> Optional[datetime]:
        max_t: Optional[datetime] = None
        for t in [self.complete, self.locked, self.revoked, self.canceled, self.failed]:
            if max_t is None or t is not None and t > max_t:
                max_t = t
        return max_t

    end_time.fget.short_description = _("end time")  # type: ignore

    @property
    def runtime(self) -> Optional[timedelta]:
        min_t, max_t = self.executing, self.end_time
        if max_t is None:
            max_t = now()
        return max_t - min_t if min_t is not None and max_t is not None else None

    runtime.fget.short_description = _("runtime")  # type: ignore
