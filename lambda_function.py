"""Set a Cognito user's custom:student_id after Arcus Attendance registration.

arcus-attendance invokes this asynchronously with:

    {"username": "<cognito username>", "sub": "<cognito sub>", "student_id": "<student number>"}

username is preferred. sub is accepted when username is absent. Re-setting the
same value is success.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

STUDENT_ID_ATTRIBUTE = "custom:student_id"
DEFAULT_REGION = "ap-southeast-1"


def lambda_handler(event: dict[str, Any] | None, context: Any, cognito_client: Any = None) -> dict[str, Any]:
    payload = event if isinstance(event, dict) else {}
    student_id = _text(payload.get("student_id"))
    username = _text(payload.get("username")) or _text(payload.get("sub"))

    if student_id is None:
        logger.info("Rejected student id sync: student_id is missing")
        return {"statusCode": 400, "error": "student_id is required"}

    if username is None:
        logger.info("Rejected student id sync: username and sub are missing")
        return {"statusCode": 400, "error": "username or sub is required"}

    user_pool_id = os.environ.get("USER_POOL_ID", "").strip()
    if not user_pool_id:
        logger.error("Rejected student id sync: USER_POOL_ID is not configured")
        return {"statusCode": 500, "error": "USER_POOL_ID is not configured"}

    client = cognito_client if cognito_client is not None else _cognito_client()

    try:
        client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[{"Name": STUDENT_ID_ATTRIBUTE, "Value": student_id}],
        )
    except Exception as error:
        if _is_unchanged(error):
            logger.info("Cognito student id attribute unchanged")
            return {"statusCode": 200, "unchanged": True}
        logger.exception("Cognito student id update failed")
        raise

    logger.info("Cognito student id attribute updated")
    return {"statusCode": 200, "updated": True}


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _is_unchanged(error: Exception) -> bool:
    response = getattr(error, "response", None)
    message = ""
    if isinstance(response, dict):
        details = response.get("Error", {})
        if isinstance(details, dict):
            message = str(details.get("Message", ""))
    if "unchanged" in message.lower():
        return True
    return "unchanged" in str(error).lower()


def _cognito_client() -> Any:
    import boto3

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or DEFAULT_REGION
    return boto3.client("cognito-idp", region_name=region)
