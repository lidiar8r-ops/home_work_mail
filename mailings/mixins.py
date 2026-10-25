from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class VisibleOwnerQuerysetMixin(LoginRequiredMixin):
    """Списки и карточки: пользователь видит свои объекты, менеджер — все."""

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_manager:
            return queryset
        return queryset.filter(owner=self.request.user)


class OwnerRequiredMixin(LoginRequiredMixin):
    """Изменение и удаление: только владелец, даже если он менеджер."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_manager
