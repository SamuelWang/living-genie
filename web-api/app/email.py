from email.message import EmailMessage

import aiosmtplib

from app.models import User
from app.observability import get_logger
from app.settings import get_settings

logger = get_logger(__name__)

_EMAIL_COPY = {
    "en": {
        "email_verification": {
            "subject": "Verify your email",
            "heading": "Verify your email address",
            "body": "Your verification code is:",
            "footer": "This code expires in {minutes} minutes. If you didn't request this, you can ignore this email.",
            "link_label": "Or verify your email here:",
        },
        "password_reset": {
            "subject": "Reset your password",
            "heading": "Reset your password",
            "body": "Your password reset code is:",
            "footer": "This code expires in {minutes} minutes. If you didn't request this, you can ignore this email.",
            "link_label": "Or reset your password here:",
        },
    },
    "zh-Hant": {
        "email_verification": {
            "subject": "驗證您的電子郵件",
            "heading": "驗證您的電子郵件地址",
            "body": "您的驗證碼是：",
            "footer": "此驗證碼將在 {minutes} 分鐘後過期。如果您沒有提出此請求，請忽略此郵件。",
            "link_label": "或點此驗證您的電子郵件：",
        },
        "password_reset": {
            "subject": "重設您的密碼",
            "heading": "重設您的密碼",
            "body": "您的密碼重設碼是：",
            "footer": "此重設碼將在 {minutes} 分鐘後過期。如果您沒有提出此請求，請忽略此郵件。",
            "link_label": "或點此重設您的密碼：",
        },
    },
}


async def _send_code_email(
    user: User, code: str, *, purpose: str, expire_minutes: int, path: str
) -> None:
    settings = get_settings()
    copy = _EMAIL_COPY.get(user.locale, _EMAIL_COPY["zh-Hant"])[purpose]

    message = EmailMessage()
    message["Subject"] = copy["subject"]
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = user.email

    link = f"{settings.frontend_origin}{path}?email={user.email}"
    footer = copy["footer"].format(minutes=expire_minutes)
    message.set_content(
        f"{copy['heading']}\n\n{copy['body']} {code}\n\n{footer}\n\n{copy['link_label']} {link}\n"
    )
    message.add_alternative(
        f"<p>{copy['heading']}</p>"
        f"<p>{copy['body']} <strong>{code}</strong></p>"
        f"<p>{footer}</p>"
        f"<p>{copy['link_label']} <a href=\"{link}\">{link}</a></p>",
        subtype="html",
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
        )
    except Exception:
        logger.exception("failed to send %s email to %s", purpose, user.email)


async def send_verification_email(user: User, code: str) -> None:
    settings = get_settings()
    await _send_code_email(
        user,
        code,
        purpose="email_verification",
        expire_minutes=settings.email_verification_token_expire_minutes,
        path="/verify-email",
    )


async def send_password_reset_email(user: User, code: str) -> None:
    settings = get_settings()
    await _send_code_email(
        user,
        code,
        purpose="password_reset",
        expire_minutes=settings.password_reset_token_expire_minutes,
        path="/reset-password",
    )
