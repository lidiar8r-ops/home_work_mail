from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import MessageForm, RecipientForm
from .mixins import OwnerRequiredMixin, VisibleOwnerQuerysetMixin
from .models import Message, Recipient


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
