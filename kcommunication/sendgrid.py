import json
import logging
from functools import lru_cache
from typing import List, Dict, Union, Optional, Any
import sendgrid  # type: ignore
from django.conf import settings


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_sendgrid_client() -> sendgrid.SendGridAPIClient:
    return sendgrid.SendGridAPIClient(api_key=settings.EMAIL_SENDGRID_API_KEY)  # type: ignore


def get_email_bounce_list() -> List[Dict[str, Union[int, str]]]:
    sg = get_sendgrid_client()
    response = sg.client.suppression.bounces.get()
    if response.status_code >= 300:
        logger.warning("get_email_bounce_list failed:")
        logger.warning(response.status_code)
        logger.warning(response.body)
        logger.warning(response.headers)
        raise Exception(
            f"SendGrid GET suppression/bounces failed: {response.body.decode()}"
        )
    return json.loads(response.body)


def delete_email_bounce_list(
    delete_all: bool = True, emails: Optional[List[str]] = None
):
    sg = get_sendgrid_client()
    data: Dict[str, Any] = {
        "delete_all": delete_all,
    }
    if emails:
        data["emails"] = emails
    response = sg.client.suppression.bounces.delete(data)
    if response.status_code >= 300:
        logger.warning("delete_email_bounce_list failed:")
        logger.warning(response.status_code)
        logger.warning(response.body)
        logger.warning(response.headers)
        raise Exception(
            f"SendGrid DELETE suppression/bounces failed: {response.body.decode()}"
        )
