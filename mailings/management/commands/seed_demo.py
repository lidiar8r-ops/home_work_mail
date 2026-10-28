from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from mailings.cache import bump_stats_cache
from mailings.models import Mailing, MailingAttempt, Message, Recipient
from users.models import User


class Command(BaseCommand):
    help = "Создаёт демонстрационных пользователей, клиентов и рассылки"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить прежние демо-рассылки пользователя",
        )

    def get_user(self, email, password, full_name, role):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": full_name,
                "role": role,
                "is_email_confirmed": True,
                "is_active": True,
            },
        )
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user

    def handle(self, *args, **options):
        manager = self.get_user(
            "manager@example.com",
            "Manager12345!",
            "Мария Менеджерова",
            User.Role.MANAGER,
        )
        user = self.get_user(
            "user@example.com",
            "User12345!",
            "Иван Пользователь",
            User.Role.USER,
        )

        if options["reset"]:
            Mailing.objects.filter(owner=user).delete()

        recipients = []
        for email, full_name in [
            ("anna@example.com", "Анна Смирнова"),
            ("boris@example.com", "Борис Петров"),
            ("vera@example.com", "Вера Орлова"),
        ]:
            recipient, _ = Recipient.objects.get_or_create(
                email=email,
                defaults={"owner": user, "full_name": full_name},
            )
            recipients.append(recipient)

        message, _ = Message.objects.get_or_create(
            owner=user,
            subject="Ноябрьские новости",
            defaults={
                "body": (
                    "Здравствуйте!\n\n"
                    "Рассказываем, что нового у нас в ноябре: обновления "
                    "сервиса и полезные материалы."
                )
            },
        )

        now = timezone.now()
        if not Mailing.objects.filter(owner=user).exists():
            active = Mailing.objects.create(
                owner=user,
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(days=2),
                message=message,
            )
            active.recipients.set(recipients)

            future = Mailing.objects.create(
                owner=user,
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=3),
                message=message,
            )
            future.recipients.set(recipients[:2])

            finished = Mailing.objects.create(
                owner=user,
                start_time=now - timedelta(days=3),
                end_time=now - timedelta(days=1),
                message=message,
            )
            finished.recipients.set(recipients)

            MailingAttempt.objects.bulk_create(
                [
                    MailingAttempt(
                        mailing=finished,
                        attempt_time=now - timedelta(days=2),
                        status=MailingAttempt.Status.SUCCESS,
                        server_response="250 OK: письмо принято почтовым сервером",
                    ),
                    MailingAttempt(
                        mailing=finished,
                        attempt_time=now - timedelta(days=2),
                        status=MailingAttempt.Status.SUCCESS,
                        server_response="250 OK: письмо принято почтовым сервером",
                    ),
                    MailingAttempt(
                        mailing=finished,
                        attempt_time=now - timedelta(days=2),
                        status=MailingAttempt.Status.FAILED,
                        server_response="550 Mailbox unavailable",
                    ),
                ],
                batch_size=100,
            )

        bump_stats_cache()

        active = Mailing.objects.filter(
            owner=user,
            is_disabled=False,
            start_time__lte=now,
            end_time__gte=now,
        ).first()

        self.stdout.write(self.style.SUCCESS("Демо-данные готовы."))
        self.stdout.write("Пользователь: user@example.com / User12345!")
        self.stdout.write("Менеджер: manager@example.com / Manager12345!")
        if active:
            self.stdout.write(
                f"Активная рассылка: #{active.pk} — {active.message.subject}"
            )
            self.stdout.write(
                f"Запуск: python manage.py send_mailing {active.pk}"
            )
