from django.core.management.base import BaseCommand, CommandError

from mailings.models import Mailing, MailingAttempt
from mailings.services import MailingError, run_mailing


class Command(BaseCommand):
    help = "Запускает рассылку по её id"

    def add_arguments(self, parser):
        parser.add_argument("mailing_id", type=int, help="Идентификатор рассылки")

    def handle(self, *args, **options):
        mailing_id = options["mailing_id"]
        try:
            mailing = Mailing.objects.get(pk=mailing_id)
        except Mailing.DoesNotExist:
            raise CommandError(f"Рассылка #{mailing_id} не найдена.")

        try:
            attempts = run_mailing(mailing)
        except MailingError as exc:
            raise CommandError(f"Ошибка: {exc}")

        success = sum(
            attempt.status == MailingAttempt.Status.SUCCESS
            for attempt in attempts
        )
        failed = len(attempts) - success

        self.stdout.write(
            self.style.SUCCESS(
                f"Рассылка #{mailing.pk}: успешно {success}, ошибок {failed}."
            )
        )
        for attempt in attempts:
            self.stdout.write(
                f"  {attempt.get_status_display()}: {attempt.server_response}"
            )
