from django import forms

from .models import Message, Recipient


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
