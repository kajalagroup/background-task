import logging
from typing import Optional, Sequence, Union, Tuple, List
import re
from django.conf import settings
from django.template.loader import render_to_string
from jutil.email import (
    send_email as send_email_impl,
)

logger = logging.getLogger(__name__)


def send_email(  # noqa
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

    if not settings.EMAIL_SENDING_ENABLED:
        logger.info(
            "Email sending disabled (EMAIL_SENDING_ENABLED=%s, DEBUG=%s):",
            settings.EMAIL_SENDING_ENABLED,
            settings.DEBUG,
        )
        logger.info("To: %s", recipients)
        logger.info("Subject: %s", subject)
        if sender:
            logger.info("Sender: %s", sender)
        if cc_recipients:
            logger.info("Cc: %s", cc_recipients)
        if bcc_recipients:
            logger.info("Bcc: %s", bcc_recipients)
        logger.info("%s", html or text)
        return

    return send_email_impl(
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


def send_email_with_template(  # noqa
    recipients: Sequence[Union[str, Tuple[str, str]]],
    subject: str,
    html_template: Optional[str] = None,
    body_params: Optional[dict] = None,
    sender: Union[str, Tuple[str, str]] = "",
    files: Optional[Sequence[str]] = None,
    cc_recipients: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
    bcc_recipients: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
    exceptions: bool = False,
):
    body_params = body_params if body_params is not None else {}
    if html_template is not None:
        html = render_to_string(html_template, body_params)

    send_email(
        recipients=recipients,
        subject=subject,
        html=html,
        sender=sender,
        files=files,
        cc_recipients=cc_recipients,
        bcc_recipients=bcc_recipients,
        exceptions=exceptions,
    )




def csv_to_list(value_list_str: str) -> List[str]:
    """
    Splits string by 1) ' ' 2) ';' 3) ','
    and returns list of strings.
    :param value_list_str: E.g. "john@gmail.com, henry@gmail.com"
    :return: List of emails
    """
    value_list_str = value_list_str.replace(",", " ")
    value_list_str = value_list_str.replace(";", " ")
    value_list_str = re.sub(r"\s+", " ", value_list_str)
    vals = []
    for val in value_list_str.split(" "):
        val = val.strip()
        if val:
            vals.append(val)
    return vals