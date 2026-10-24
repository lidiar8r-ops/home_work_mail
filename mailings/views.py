from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import MailingForm, MessageForm, RecipientForm
from .mixins import OwnerRequiredMixin, VisibleOwnerQuerysetMixin
from .models import Mailing, Message, Recipient


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"


class RecipientListView(VisibleOwnerQuerysetMixin, ListView):
    model = Recipient
    paginate_by = 15
    context_object_name = "recipients"
    template_name = "mailings/recipient_list.html"


class RecipientCreateView(LoginRequiredMixin, CreateView):
    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("mailings:recipient_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Клиент добавлен.")
        return super().form_valid(form)


class RecipientUpdateView(OwnerRequiredMixin, UpdateView):
    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("mailings:recipient_list")

    def form_valid(self, form):
        messages.success(self.request, "Данные клиента обновлены.")
        return super().form_valid(form)


class RecipientDeleteView(OwnerRequiredMixin, DeleteView):
    model = Recipient
    template_name = "mailings/recipient_confirm_delete.html"
    success_url = reverse_lazy("mailings:recipient_list")

    def form_valid(self, form):
        messages.success(self.request, "Клиент удалён.")
        return super().form_valid(form)


class MessageListView(VisibleOwnerQuerysetMixin, ListView):
    model = Message
    paginate_by = 15
    context_object_name = "messages_list"
    template_name = "mailings/message_list.html"


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("mailings:message_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Сообщение создано.")
        return super().form_valid(form)


class MessageUpdateView(OwnerRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("mailings:message_list")

    def form_valid(self, form):
        messages.success(self.request, "Сообщение обновлено.")
        return super().form_valid(form)


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
        context["can_edit"] = mailing.owner_id == self.request.user.id
        context["can_disable"] = self.request.user.is_manager
        return context


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


class MailingDeleteView(OwnerRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailings/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailings:mailing_list")

    def form_valid(self, form):
        messages.success(self.request, "Рассылка удалена.")
        return super().form_valid(form)
