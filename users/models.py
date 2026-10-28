import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Менеджер пользователей, у которых вход выполняется по email."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_confirmed", True)
        extra_fields.setdefault("role", User.Role.MANAGER)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Пользователь сервиса: обычный клиент или менеджер."""

    class Role(models.TextChoices):
        USER = "user", "Пользователь"
        MANAGER = "manager", "Менеджер"

    username = None
    email = models.EmailField("Email", unique=True)
    full_name = models.CharField("Ф. И. О.", max_length=150, blank=True)
    role = models.CharField(
        "Роль",
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )
    is_email_confirmed = models.BooleanField("Email подтверждён", default=False)
    email_confirmation_token = models.UUIDField(
        "Токен подтверждения",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    email_confirmation_sent_at = models.DateTimeField(
        "Письмо подтверждения отправлено",
        null=True,
        blank=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("email",)

    def __str__(self):
        return self.email

    @property
    def is_manager(self) -> bool:
        return self.is_superuser or self.role == self.Role.MANAGER

    def issue_confirmation_token(self) -> None:
        self.email_confirmation_token = uuid.uuid4()
        self.email_confirmation_sent_at = timezone.now()
        self.save(
            update_fields=[
                "email_confirmation_token",
                "email_confirmation_sent_at",
            ]
        )

    def confirmation_token_expired(self, timeout_hours: int) -> bool:
        if not self.email_confirmation_sent_at:
            return True
        return timezone.now() > self.email_confirmation_sent_at + timedelta(
            hours=timeout_hours
        )

    def confirm_email(self) -> None:
        self.is_email_confirmed = True
        self.email_confirmation_sent_at = None
        self.save(update_fields=["is_email_confirmed", "email_confirmation_sent_at"])
