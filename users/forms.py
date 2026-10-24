from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import User


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name")
        labels = {
            "email": "Email",
            "full_name": "Ф. И. О.",
        }
        widgets = {
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "autofocus": True}
            ),
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
        }
        help_texts = {
            "email": "На этот адрес придёт письмо для подтверждения регистрации.",
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_email_confirmed = False
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "autofocus": True}
        ),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_email_confirmed:
            raise ValidationError(
                "Email не подтверждён. Проверьте почту и перейдите по ссылке "
                "из письма.",
                code="email_not_confirmed",
            )


class ResendConfirmationForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
