import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from .forms import RegistrationForm, ResendConfirmationForm
from .models import User

logger = logging.getLogger(__name__)


def send_confirmation_email(request, user: User) -> None:
    """Выдаёт новый токен и отправляет письмо со ссылкой подтверждения."""
    user.issue_confirmation_token()
    confirmation_url = request.build_absolute_uri(
        reverse("users:confirm_email", args=[user.email_confirmation_token])
    )
    subject = "Подтверждение регистрации"
    message = render_to_string(
        "users/emails/confirm_email.txt",
        {
            "user": user,
            "confirmation_url": confirmation_url,
            "timeout_hours": settings.EMAIL_CONFIRMATION_TIMEOUT_HOURS,
        },
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("mailings:home")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        try:
            send_confirmation_email(request, user)
        except Exception:
            logger.exception("Не удалось отправить письмо подтверждения")
            messages.error(
                request,
                "Аккаунт создан, но письмо отправить не удалось. "
                "Запросите подтверждение ещё раз.",
            )
            return redirect("users:resend_confirmation")

        messages.success(
            request,
            "Регистрация завершена. Проверьте почту и подтвердите email.",
        )
        return redirect("users:login")

    return render(request, "users/register.html", {"form": form})


def confirm_email(request, token):
    user = get_object_or_404(User, email_confirmation_token=token)

    if user.is_email_confirmed:
        messages.info(request, "Email уже подтверждён. Можно войти.")
        return redirect("users:login")

    if user.confirmation_token_expired(settings.EMAIL_CONFIRMATION_TIMEOUT_HOURS):
        messages.error(
            request,
            "Ссылка подтверждения устарела. Запросите новое письмо.",
        )
        return redirect("users:resend_confirmation")

    user.confirm_email()
    messages.success(request, "Email подтверждён. Теперь можно войти.")
    return redirect("users:login")


def resend_confirmation(request):
    if request.user.is_authenticated:
        return redirect("mailings:home")

    form = ResendConfirmationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.filter(
            email__iexact=email,
            is_email_confirmed=False,
        ).first()
        if user is not None:
            try:
                send_confirmation_email(request, user)
            except Exception:
                logger.exception("Не удалось отправить письмо подтверждения")
        messages.success(
            request,
            "Если аккаунт с таким email существует и ещё не подтверждён, "
            "письмо отправлено.",
        )
        return redirect("users:login")

    return render(request, "users/resend_confirmation.html", {"form": form})


@login_required
def profile(request):
    return render(request, "users/profile.html")
