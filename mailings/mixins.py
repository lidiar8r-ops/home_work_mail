from django.contrib.auth.mixins import LoginRequiredMixin


class VisibleOwnerQuerysetMixin(LoginRequiredMixin):
    """Для списков и карточек: пользователь видит только свои объекты."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class OwnerRequiredMixin(LoginRequiredMixin):
    """Для изменения и удаления: доступ есть только у владельца."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)
