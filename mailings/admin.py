from django.contrib import admin

from .models import Mailing, MailingAttempt, Message, Recipient


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "owner", "created_at")
    list_filter = ("owner",)
    search_fields = ("email", "full_name")
    readonly_fields = ("created_at",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "owner", "created_at")
    list_filter = ("owner",)
    search_fields = ("subject", "body")
    readonly_fields = ("created_at",)


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "owner",
        "start_time",
        "end_time",
        "status_label",
        "is_disabled",
    )
    list_filter = ("is_disabled", "owner")
    search_fields = ("message__subject", "owner__email")
    filter_horizontal = ("recipients",)
    readonly_fields = ("status_label", "created_at")


@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "mailing", "attempt_time", "status", "server_response")
    list_filter = ("status",)
    search_fields = ("mailing__message__subject", "server_response")
    readonly_fields = ("mailing", "attempt_time", "status", "server_response")

    def has_add_permission(self, request):
        return False
