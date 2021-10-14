import logging
from huey.contrib.djhuey import HUEY as huey  # type: ignore
from django.utils.timezone import now
import traceback
from kbackgroundtask.models import BackgroundTask

TASKS_TO_IGNORE = {"run_check"}


logger = logging.getLogger(__name__)


@huey.signal()
def all_signal_handler(signal, task, exc=None):
    """
    task.__dict__ == {
        'args': (),
        'eta': None,
        'id': '01d685e1-aefe-4fbd-b37c-8700392781d2',
        'kwargs': {},
        'name': 'dummy_db_periodic_task_1',
        'on_complete': None,
        'on_error': None,
        'priority': None,
        'retries': 0,
        'retry_delay': 0,
        'revoke_id': 'r:01d685e1-aefe-4fbd-b37c-8700392781d2'
    }
    """
    time_now = now()
    err = ""
    if exc:
        try:
            err = traceback.format_exc()
        except Exception:
            err = str(exc)
    if err or task.name not in TASKS_TO_IGNORE:
        if signal == "executing":
            logger.info(
                "Executing task id=%s: %s(*%s, **%s)",
                task.id,
                task.name,
                task.args,
                task.kwargs,
            )
        update_fields = ["signal", "last_modified"]
        obj = BackgroundTask.objects.get_or_create(
            task_id=task.id, defaults={"name": task.name}
        )[0]
        assert isinstance(obj, BackgroundTask)
        obj.signal = signal
        if not hasattr(obj, signal):
            logger.error("Object %s does not have member %s (signal)", obj, signal)
        else:
            setattr(obj, signal, time_now)
            update_fields.append(signal)
        obj.last_modified = time_now
        if err:
            obj.error = err
            obj.failed = time_now
            update_fields.append("error")
            update_fields.append("failed")
        obj.save(update_fields=update_fields)
