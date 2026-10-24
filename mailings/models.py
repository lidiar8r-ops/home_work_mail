from django.conf import settings
from django.db import models
from django.utils import timezone


class Recipient(models.Model):
    """Получатель рассылки."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipients",
        verbose_name="Владелец",
    )
    email = models.EmailField("Email", unique=True)
    full_name = models.CharField("Ф. И. О.", max_length=150)
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Получатель"
        verbose_name_plural = "Получатели"
        ordering = ("full_name",)

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


class Message(models.Model):
    """Шаблон письма для рассылки."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Владелец",
    )
    subject = models.CharField("Тема письма", max_length=255)
    body = models.TextField("Тело письма")
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ("-created_at",)

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    """Рассылка: период, сообщение и список получателей."""

    class Status(models.TextChoices):
        CREATED = "created", "Создана"
        STARTED = "started", "Запущена"
        FINISHED = "finished", "Завершена"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="Владелец",
    )
    start_time = models.DateTimeField("Дата и время начала")
    end_time = models.DateTimeField("Дата и время окончания")
    message = models.ForeignKey(
        Message,
        on_delete=models.PROTECT,
        related_name="mailings",
        verbose_name="Сообщение",
    )
    recipients = models.ManyToManyField(
        Recipient,
        related_name="mailings",
        verbose_name="Получатели",
    )
    is_disabled = models.BooleanField("Отключена менеджером", default=False)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ("-start_time",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_time__lt=models.F("end_time")),
                name="mailing_start_before_end",
            ),
        ]

    def __str__(self):
        if not self.pk:
            return "Новая рассылка"
        return f"Рассылка #{self.pk} — {self.message.subject}"

    @property
    def status(self) -> str:
        """Статус вычисляется динамически по текущему времени."""
        now = timezone.now()
        if now < self.start_time:
            return self.Status.CREATED
        if now <= self.end_time:
            return self.Status.STARTED
        return self.Status.FINISHED

    @property
    def status_label(self) -> str:
        return self.Status(self.status).label

    @property
    def can_send(self) -> bool:
        if self.is_disabled:
            return False
        return self.start_time <= timezone.now() <= self.end_time


class MailingAttempt(models.Model):
    """Попытка отправки письма в рамках рассылки."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Успешно"
        FAILED = "failed", "Не успешно"

    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Рассылка",
    )
    attempt_time = models.DateTimeField(
        "Дата и время попытки",
        default=timezone.now,
    )
    status = models.CharField(
        "Статус",
        max_length=10,
        choices=Status.choices,
    )
    server_response = models.TextField("Ответ почтового сервера", blank=True)

    class Meta:
        verbose_name = "Попытка отправки"
        verbose_name_plural = "Попытки отправки"
        ordering = ("-attempt_time",)
        indexes = [
            models.Index(
                fields=["mailing", "-attempt_time"],
                name="attempt_mailing_time_idx",
            ),
        ]

    def __str__(self):
        return f"Попытка #{self.pk}: {self.get_status_display()}"
