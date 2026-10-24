from django import forms
from django.utils import timezone

from .models import Mailing, Message, Recipient


def _to_minute(value):
    return value.replace(second=0, microsecond=0)


class RecipientForm(forms.ModelForm):
    class Meta:
        model = Recipient
        fields = ("email", "full_name", "comment")
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("subject", "body")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 10}),
        }


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ("start_time", "end_time", "message", "recipients")
        widgets = {
            "start_time": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "end_time": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "recipients": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and user.is_authenticated:
            self.fields["message"].queryset = Message.objects.filter(owner=user)
            self.fields["recipients"].queryset = Recipient.objects.filter(
                owner=user
            )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        now = timezone.now()

        if start_time:
            previous_start = (
                self.instance.start_time if self.instance.pk else None
            )
            start_changed = previous_start is None or (
                _to_minute(start_time) != _to_minute(previous_start)
            )
            if start_changed and start_time < now:
                self.add_error(
                    "start_time",
                    "Дата начала не может быть в прошлом.",
                )

        if start_time and end_time and start_time >= end_time:
            self.add_error(
                "end_time",
                "Дата окончания должна быть позже даты начала.",
            )

        return cleaned_data
