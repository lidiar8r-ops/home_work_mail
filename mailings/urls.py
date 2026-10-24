from django.urls import path

from . import views

app_name = "mailings"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path(
        "recipients/",
        views.RecipientListView.as_view(),
        name="recipient_list",
    ),
    path(
        "recipients/create/",
        views.RecipientCreateView.as_view(),
        name="recipient_create",
    ),
    path(
        "recipients/<int:pk>/edit/",
        views.RecipientUpdateView.as_view(),
        name="recipient_update",
    ),
    path(
        "recipients/<int:pk>/delete/",
        views.RecipientDeleteView.as_view(),
        name="recipient_delete",
    ),
    path("messages/", views.MessageListView.as_view(), name="message_list"),
    path(
        "messages/create/",
        views.MessageCreateView.as_view(),
        name="message_create",
    ),
    path(
        "messages/<int:pk>/edit/",
        views.MessageUpdateView.as_view(),
        name="message_update",
    ),
    path(
        "messages/<int:pk>/delete/",
        views.MessageDeleteView.as_view(),
        name="message_delete",
    ),
]
