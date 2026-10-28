from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationTests(TestCase):
    def test_register_sends_confirmation_and_confirm_allows_login(self):
        response = self.client.post(
            reverse("users:register"),
            {
                "email": "new@example.com",
                "full_name": "Новый Пользователь",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("users:login"))
        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_email_confirmed)
        self.assertEqual(len(mail.outbox), 1)

        response = self.client.get(
            reverse(
                "users:confirm_email",
                args=[user.email_confirmation_token],
            )
        )
        self.assertRedirects(response, reverse("users:login"))

        user.refresh_from_db()
        self.assertTrue(user.is_email_confirmed)
        self.assertTrue(
            self.client.login(
                username="new@example.com",
                password="StrongPass123!",
            )
        )

    def test_unconfirmed_user_cannot_login(self):
        User.objects.create_user(
            email="wait@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("users:login"),
            {"username": "wait@example.com", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "не подтверждён")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_blocked_user_cannot_login(self):
        User.objects.create_user(
            email="blocked@example.com",
            password="StrongPass123!",
            is_email_confirmed=True,
            is_active=False,
        )

        response = self.client.post(
            reverse("users:login"),
            {"username": "blocked@example.com", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_password_reset_sends_email(self):
        User.objects.create_user(
            email="reset@example.com",
            password="StrongPass123!",
            is_email_confirmed=True,
        )

        response = self.client.post(
            reverse("users:password_reset"),
            {"email": "reset@example.com"},
        )

        self.assertRedirects(response, reverse("users:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/users/reset/", mail.outbox[0].body)
