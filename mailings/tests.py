from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .cache import get_stats_cache_version
from .forms import MailingForm
from .models import Mailing, MailingAttempt, Message, Recipient
from .services import MailingError, run_mailing

User = get_user_model()


class BaseDataMixin:
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            full_name="Владелец",
            is_email_confirmed=True,
        )
        self.recipient1 = Recipient.objects.create(
            owner=self.user,
            email="one@example.com",
            full_name="Первый Получатель",
        )
        self.recipient2 = Recipient.objects.create(
            owner=self.user,
            email="two@example.com",
            full_name="Второй Получатель",
        )
        self.message = Message.objects.create(
            owner=self.user,
            subject="Тема письма",
            body="Текст письма",
        )

    def make_mailing(self, start_delta, end_delta, **kwargs):
        now = timezone.now()
        mailing = Mailing.objects.create(
            owner=self.user,
            start_time=now + start_delta,
            end_time=now + end_delta,
            message=self.message,
            **kwargs,
        )
        mailing.recipients.set([self.recipient1, self.recipient2])
        return mailing


class StatusTests(BaseDataMixin, TestCase):
    def test_created_status(self):
        mailing = self.make_mailing(timedelta(hours=1), timedelta(hours=2))
        self.assertEqual(mailing.status, Mailing.Status.CREATED)
        self.assertEqual(mailing.status_label, "Создана")
        self.assertFalse(mailing.can_send)

    def test_started_status(self):
        mailing = self.make_mailing(timedelta(hours=-1), timedelta(hours=1))
        self.assertEqual(mailing.status, Mailing.Status.STARTED)
        self.assertEqual(mailing.status_label, "Запущена")
        self.assertTrue(mailing.can_send)

    def test_finished_status(self):
        mailing = self.make_mailing(timedelta(hours=-2), timedelta(hours=-1))
        self.assertEqual(mailing.status, Mailing.Status.FINISHED)
        self.assertEqual(mailing.status_label, "Завершена")
        self.assertFalse(mailing.can_send)


class MailingFormTests(BaseDataMixin, TestCase):
    def local(self, value):
        return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")

    def form_data(self, start, end):
        return {
            "start_time": start,
            "end_time": end,
            "message": self.message.pk,
            "recipients": [self.recipient1.pk],
        }

    def test_start_in_past_is_invalid(self):
        now = timezone.now()
        form = MailingForm(
            data=self.form_data(
                self.local(now - timedelta(hours=1)),
                self.local(now + timedelta(hours=2)),
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("start_time", form.errors)

    def test_end_must_be_after_start(self):
        now = timezone.now()
        form = MailingForm(
            data=self.form_data(
                self.local(now + timedelta(hours=2)),
                self.local(now + timedelta(hours=1)),
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)

    def test_valid_period(self):
        now = timezone.now()
        form = MailingForm(
            data=self.form_data(
                self.local(now + timedelta(hours=1)),
                self.local(now + timedelta(hours=3)),
            ),
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)


class RunMailingTests(BaseDataMixin, TestCase):
    def test_letters_sent_to_each_recipient(self):
        mailing = self.make_mailing(timedelta(hours=-1), timedelta(hours=1))
        attempts = run_mailing(mailing)

        self.assertEqual(len(attempts), 2)
        self.assertEqual(
            MailingAttempt.objects.filter(mailing=mailing).count(),
            2,
        )
        self.assertTrue(
            all(
                attempt.status == MailingAttempt.Status.SUCCESS
                for attempt in attempts
            )
        )
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            {sent.to[0] for sent in mail.outbox},
            {"one@example.com", "two@example.com"},
        )

    def test_attempts_are_created_with_bulk_create(self):
        mailing = self.make_mailing(timedelta(hours=-1), timedelta(hours=1))
        with patch(
            "mailings.services.MailingAttempt.objects.bulk_create"
        ) as bulk_create:
            run_mailing(mailing)

        bulk_create.assert_called_once()
        self.assertEqual(bulk_create.call_args.kwargs["batch_size"], 100)

    def test_outside_window_raises_error(self):
        mailing = self.make_mailing(timedelta(hours=1), timedelta(hours=2))
        with self.assertRaises(MailingError):
            run_mailing(mailing)
        self.assertEqual(MailingAttempt.objects.count(), 0)

    def test_disabled_mailing_raises_error(self):
        mailing = self.make_mailing(
            timedelta(hours=-1),
            timedelta(hours=1),
            is_disabled=True,
        )
        with self.assertRaises(MailingError):
            run_mailing(mailing)

    def test_mailing_without_recipients_raises_error(self):
        mailing = self.make_mailing(timedelta(hours=-1), timedelta(hours=1))
        mailing.recipients.clear()
        with self.assertRaises(MailingError):
            run_mailing(mailing)

    def test_run_view_shows_error_outside_window(self):
        mailing = self.make_mailing(timedelta(hours=1), timedelta(hours=2))
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("mailings:mailing_run", args=[mailing.pk]),
            follow=True,
        )

        self.assertContains(response, "ещё не началась")
        self.assertEqual(MailingAttempt.objects.count(), 0)


class AccessTests(BaseDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="StrongPass123!",
            role=User.Role.MANAGER,
            is_email_confirmed=True,
        )
        self.other = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            is_email_confirmed=True,
        )
        self.mailing = self.make_mailing(
            timedelta(hours=-1),
            timedelta(hours=1),
        )

    def test_manager_sees_foreign_mailing_but_cannot_edit(self):
        self.client.force_login(self.manager)

        self.assertEqual(
            self.client.get(
                reverse("mailings:mailing_detail", args=[self.mailing.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("mailings:mailing_update", args=[self.mailing.pk])
            ).status_code,
            404,
        )

    def test_regular_user_cannot_view_foreign_mailing(self):
        self.client.force_login(self.other)

        self.assertEqual(
            self.client.get(
                reverse("mailings:mailing_detail", args=[self.mailing.pk])
            ).status_code,
            404,
        )

    def test_manager_can_block_user_and_disable_mailing(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("mailings:user_toggle_block", args=[self.user.pk])
        )
        self.assertRedirects(response, reverse("mailings:manager_users"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

        response = self.client.post(
            reverse("mailings:mailing_disable", args=[self.mailing.pk])
        )
        self.assertRedirects(
            response,
            reverse("mailings:mailing_detail", args=[self.mailing.pk]),
        )
        self.mailing.refresh_from_db()
        self.assertTrue(self.mailing.is_disabled)

    def test_regular_user_cannot_open_manager_page(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("mailings:manager_users"))
        self.assertEqual(response.status_code, 403)


class CacheTests(BaseDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_home_and_lists_have_client_cache_headers(self):
        self.client.force_login(self.user)

        home = self.client.get(reverse("mailings:home"))
        self.assertEqual(home.status_code, 200)
        self.assertIn("private", home["Cache-Control"])
        self.assertIn("max-age=60", home["Cache-Control"])

        mailing_list = self.client.get(reverse("mailings:mailing_list"))
        self.assertIn("must-revalidate", mailing_list["Cache-Control"])

        form_page = self.client.get(reverse("mailings:mailing_create"))
        self.assertIn("no-store", form_page["Cache-Control"])

    def test_stats_cache_invalidated_after_new_mailing(self):
        self.client.force_login(self.user)
        self.client.get(reverse("mailings:home"))
        version_before = get_stats_cache_version()

        self.make_mailing(timedelta(hours=1), timedelta(hours=2))

        self.assertNotEqual(version_before, get_stats_cache_version())
