import logging
from typing import Union, Tuple, Sequence, Optional
from huey import crontab  # type: ignore
from huey.contrib.djhuey import db_periodic_task, task  # type: ignore
from kcommunication.helpers import send_email, send_email_with_template
from kcommunication.sendgrid import delete_email_bounce_list

logger = logging.getLogger(__name__)

@task(retries=3, retry_delay=60, priority=10)
def send_email_with_template_task(email, subject, template, body):
    send_email_with_template(email, subject, template, body)


@task(retries=3, retry_delay=60, priority=10)
def send_email_task(  # noqa
    recipients: Sequence[Union[str, Tuple[str, str]]],
    subject: str,
    text: str = "",
    html: str = "",
    sender: Union[str, Tuple[str, str]] = "",
    files: Optional[Sequence[str]] = None,
    cc_recipients: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
    bcc_recipients: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
    exceptions: bool = False,
):
    send_email(
        recipients=recipients,
        subject=subject,
        text=text,
        html=html,
        sender=sender,
        files=files,
        cc_recipients=cc_recipients,
        bcc_recipients=bcc_recipients,
        exceptions=exceptions,
    )


@db_periodic_task(crontab(minute=0, hour=4))
def sendgrid_delete_bounce_list_daily_task():
    delete_email_bounce_list()
