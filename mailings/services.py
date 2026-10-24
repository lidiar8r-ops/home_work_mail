import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Mailing, MailingAttempt

logger = logging.getLogger(__name__)


class MailingError(Exception):
    """Рассылка не может быть запущена."""


def _format_time(value) -> str:
    return timezone.localtime(value).strftime("%d.%m.%Y %H:%M")


def _success_response() -> str:
    backend = settings.MAILERS["default"]["BACKEND"]
    if "console" in backend:
        return "250 OK: письмо выведено в консоль (console backend)"
    return "250 OK: письмо принято почтовым сервером"


def run_mailing(mailing: Mailing) -> list[MailingAttempt]:
    """Отправляет письмо каждому получателю и сохраняет попытки одним batch."""
    now = timezone.now()

    if mailing.is_disabled:
        raise MailingError("Рассылка отключена менеджером.")
    if now < mailing.start_time:
        raise MailingError(
            "Рассылка ещё не началась. "
            f"Старт: {_format_time(mailing.start_time)}."
        )
    if now > mailing.end_time:
        raise MailingError(
            "Время рассылки истекло. "
            f"Окончание: {_format_time(mailing.end_time)}."
        )

    recipients = list(mailing.recipients.all())
    if not recipients:
        raise MailingError("У рассылки нет получателей.")

    attempts: list[MailingAttempt] = []

    for recipient in recipients:
        try:
            sent = send_mail(
                mailing.message.subject,
                mailing.message.body,
                settings.DEFAULT_FROM_EMAIL,
                [recipient.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.warning(
                "Ошибка отправки письма на %s: %s",
                recipient.email,
                exc,
            )
            attempts.append(
                MailingAttempt(
                    mailing=mailing,
                    attempt_time=now,
                    status=MailingAttempt.Status.FAILED,
                    server_response=str(exc) or exc.__class__.__name__,
                )
            )
        else:
            if sent:
                attempts.append(
                    MailingAttempt(
                        mailing=mailing,
                        attempt_time=now,
                        status=MailingAttempt.Status.SUCCESS,
                        server_response=_success_response(),
                    )
                )
            else:
                attempts.append(
                    MailingAttempt(
                        mailing=mailing,
                        attempt_time=now,
                        status=MailingAttempt.Status.FAILED,
                        server_response="Письмо не отправлено",
                    )
                )

    # Попытки сохраняются пакетом, а не по одной.
    MailingAttempt.objects.bulk_create(attempts, batch_size=100)

    logger.info(
        "Рассылка #%s выполнена: писем %s, получателей %s",
        mailing.pk,
        len(attempts),
        len(recipients),
    )
    return attempts
