from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control, never_cache
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from users.models import User

from .cache import (
    STATS_CACHE_TIMEOUT,
    statistics_totals_key,
    stats_cache_key,
)
from .forms import MailingForm, MessageForm, RecipientForm
from .mixins import (
    ManagerRequiredMixin,
    OwnerRequiredMixin,
    VisibleOwnerQuerysetMixin,
)
from .models import Mailing, MailingAttempt, Message, Recipient
from .services import MailingError, run_mailing


@method_decorator(cache_control(private=True, max_age=60), name="dispatch")
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        if user.is_manager:
            mailings = Mailing.objects.all()
            recipients = Recipient.objects.all()
        else:
            mailings = Mailing.objects.filter(owner=user)
            recipients = Recipient.objects.filter(owner=user)

        attempts = MailingAttempt.objects.filter(mailing__in=mailings)

        cache_key = stats_cache_key(user)
        stats = cache.get(cache_key)
        if stats is None:
            stats = {
                "total_mailings": mailings.count(),
                "active_mailings": mailings.filter(
                    is_disabled=False,
                    start_time__lte=now,
                    end_time__gte=now,
                ).count(),
                "total_recipients": recipients.count(),
                "success_attempts": attempts.filter(
                    status=MailingAttempt.Status.SUCCESS
                ).count(),
            }
            cache.set(cache_key, stats, STATS_CACHE_TIMEOUT)

        context["stats"] = stats
        context["recent_mailings"] = mailings.select_related(
            "message", "owner"
        ).order_by("-created_at")[:5]
        context["recent_attempts"] = attempts.select_related(
            "mailing__message"
        ).order_by("-attempt_time")[:5]
        return context


@method_decorator(cache_control(private=True, max_age=60), name="dispatch")
class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = "mailings/statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_manager:
            mailings = Mailing.objects.all()
            attempts = MailingAttempt.objects.all()
        else:
            mailings = Mailing.objects.filter(owner=user)
            attempts = MailingAttempt.objects.filter(mailing__owner=user)

        mailings = (
            mailings.select_related("message", "owner")
            .annotate(
                attempt_count=Count("attempts"),
                success_count=Count(
                    "attempts",
                    filter=Q(attempts__status=MailingAttempt.Status.SUCCESS),
                ),
                failed_count=Count(
                    "attempts",
                    filter=Q(attempts__status=MailingAttempt.Status.FAILED),
                ),
            )
            .order_by("-start_time")
        )

        totals_key = statistics_totals_key(user)
        totals = cache.get(totals_key)
        if totals is None:
            totals = attempts.aggregate(
                total=Count("id"),
                success=Count(
                    "id", filter=Q(status=MailingAttempt.Status.SUCCESS)
                ),
                failed=Count(
                    "id", filter=Q(status=MailingAttempt.Status.FAILED)
                ),
            )
            cache.set(totals_key, totals, STATS_CACHE_TIMEOUT)

        context["mailings"] = mailings
        context["totals"] = totals
        return context


@method_decorator(cache_control(private=True, max_age=0, must_revalidate=True), name="dispatch")
class RecipientListView(VisibleOwnerQuerysetMixin, ListView):
    model = Recipient
    paginate_by = 15
    context_object_name = "recipients"
    template_name = "mailings/recipient_list.html"


@method_decorator(never_cache, name="dispatch")
class RecipientCreateView(LoginRequiredMixin, CreateView):
    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("mailings:recipient_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Клиент добавлен.")
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
class RecipientUpdateView(OwnerRequiredMixin, UpdateView):
    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("mailings:recipient_list")

    def form_valid(self, form):
        messages.success(self.request, "Данные клиента обновлены.")
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
class RecipientDeleteView(OwnerRequiredMixin, DeleteView):
    model = Recipient
    template_name = "mailings/recipient_confirm_delete.html"
    success_url = reverse_lazy("mailings:recipient_list")

    def form_valid(self, form):
        messages.success(self.request, "Клиент удалён.")
        return super().form_valid(form)


@method_decorator(cache_control(private=True, max_age=0, must_revalidate=True), name="dispatch")
class MessageListView(VisibleOwnerQuerysetMixin, ListView):
    model = Message
    paginate_by = 15
    context_object_name = "messages_list"
    template_name = "mailings/message_list.html"


@method_decorator(never_cache, name="dispatch")
class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("mailings:message_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Сообщение создано.")
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
class MessageUpdateView(OwnerRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("mailings:message_list")

    def form_valid(self, form):
        messages.success(self.request, "Сообщение обновлено.")
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
class MessageDeleteView(OwnerRequiredMixin, DeleteView):
    model = Message
    template_name = "mailings/message_confirm_delete.html"
    success_url = reverse_lazy("mailings:message_list")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Нельзя удалить сообщение: оно используется в рассылках.",
            )
            return redirect("mailings:message_list")
        messages.success(self.request, "Сообщение удалено.")
        return response


@method_decorator(cache_control(private=True, max_age=0, must_revalidate=True), name="dispatch")
class MailingListView(VisibleOwnerQuerysetMixin, ListView):
    model = Mailing
    paginate_by = 10
    context_object_name = "mailings"
    template_name = "mailings/mailing_list.html"

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("message", "owner")
            .prefetch_related("recipients")
        )
        status = self.request.GET.get("status", "")
        now = timezone.now()

        if status == Mailing.Status.CREATED:
            queryset = queryset.filter(start_time__gt=now)
        elif status == Mailing.Status.STARTED:
            queryset = queryset.filter(
                is_disabled=False,
                start_time__lte=now,
                end_time__gte=now,
            )
        elif status == Mailing.Status.FINISHED:
            queryset = queryset.filter(end_time__lt=now)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_status"] = self.request.GET.get("status", "")
        context["statuses"] = Mailing.Status.choices
        return context


@method_decorator(cache_control(private=True, max_age=0, must_revalidate=True), name="dispatch")
class MailingDetailView(VisibleOwnerQuerysetMixin, DetailView):
    model = Mailing
    context_object_name = "mailing"
    template_name = "mailings/mailing_detail.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("message", "owner")
            .prefetch_related("recipients")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mailing = self.object
        attempts = mailing.attempts.all()
        context["can_edit"] = mailing.owner_id == self.request.user.id
        context["can_disable"] = self.request.user.is_manager
        context["attempts"] = attempts[:100]
        context["attempts_total"] = attempts.count()
        context["attempts_success"] = attempts.filter(
            status=MailingAttempt.Status.SUCCESS
        ).count()
        context["attempts_failed"] = attempts.filter(
            status=MailingAttempt.Status.FAILED
        ).count()
        return context


@method_decorator(never_cache, name="dispatch")
class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailings/mailing_form.html"
    success_url = reverse_lazy("mailings:mailing_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Рассылка создана.")
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
class MailingUpdateView(OwnerRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailings/mailing_form.html"
    success_url = reverse_lazy("mailings:mailing_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Рассылка обновлена.")
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
class MailingDeleteView(OwnerRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailings/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailings:mailing_list")

    def form_valid(self, form):
        messages.success(self.request, "Рассылка удалена.")
        return super().form_valid(form)


class MailingRunView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk, owner=request.user)
        try:
            attempts = run_mailing(mailing)
        except MailingError as exc:
            messages.error(request, str(exc))
        else:
            success = sum(
                attempt.status == MailingAttempt.Status.SUCCESS
                for attempt in attempts
            )
            failed = len(attempts) - success
            messages.success(
                request,
                f"Рассылка выполнена: успешно {success}, ошибок {failed}.",
            )
        return redirect("mailings:mailing_detail", pk=pk)


class MailingDisableView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.is_disabled = not mailing.is_disabled
        mailing.save(update_fields=["is_disabled"])
        state = "отключена" if mailing.is_disabled else "включена"
        messages.success(request, f"Рассылка #{mailing.pk} {state}.")
        return redirect("mailings:mailing_detail", pk=mailing.pk)


@method_decorator(cache_control(private=True, max_age=0, must_revalidate=True), name="dispatch")
class ManagerUserListView(ManagerRequiredMixin, ListView):
    model = User
    template_name = "mailings/manager_user_list.html"
    context_object_name = "accounts"
    paginate_by = 20

    def get_queryset(self):
        return User.objects.annotate(
            mailing_count=Count("mailings")
        ).order_by("email")


class UserBlockView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        account = get_object_or_404(User, pk=pk)

        if account == request.user:
            messages.error(request, "Нельзя заблокировать самого себя.")
        elif account.is_superuser:
            messages.error(request, "Нельзя заблокировать суперпользователя.")
        else:
            account.is_active = not account.is_active
            account.save(update_fields=["is_active"])
            state = "заблокирован" if not account.is_active else "разблокирован"
            messages.success(request, f"Пользователь {account.email} {state}.")

        return redirect("mailings:manager_users")
