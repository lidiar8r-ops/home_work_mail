from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    model = User
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "role",
        "is_email_confirmed",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_email_confirmed", "is_active", "is_staff")
    search_fields = ("email", "full_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личные данные", {"fields": ("full_name",)}),
        (
            "Права",
            {
                "fields": (
                    "role",
                    "is_email_confirmed",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
