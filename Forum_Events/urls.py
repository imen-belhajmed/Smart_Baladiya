from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/create/",
        views.CategoryCreateView.as_view(),
        name="category-create",
    ),
    path(
        "categories/<int:pk>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category-update",
    ),
    path(
        "categories/<int:pk>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category-delete",
    ),
    path(
        "categories/<int:pk>/threads/",
        views.CategoryThreadListView.as_view(),
        name="category-threads",
    ),
    path("discussions/", views.ThreadListView.as_view(), name="thread-list"),
    path("events/", views.EventListView.as_view(), name="event-list"),
    path(
        "members/<str:username>/edit/",
        views.ProfileUpdateView.as_view(),
        name="profile-edit",
    ),
    path("members/<str:username>/", views.ProfileView.as_view(), name="profile"),
    path("threads/create/", views.ThreadCreateView.as_view(), name="thread-create"),
    path("threads/<int:pk>/", views.ThreadDetailView.as_view(), name="thread-detail"),
    path(
        "threads/<int:pk>/edit/",
        views.ThreadUpdateView.as_view(),
        name="thread-update",
    ),
    path(
        "threads/<int:pk>/delete/",
        views.ThreadDeleteView.as_view(),
        name="thread-delete",
    ),
    path(
        "threads/<int:pk>/toggle-lock/",
        views.toggle_thread_lock,
        name="thread-lock-toggle",
    ),
    path(
        "threads/<int:thread_pk>/comments/create/",
        views.ThreadCommentCreateView.as_view(),
        name="comment-create",
    ),
    path(
        "comments/<int:pk>/edit/",
        views.CommentUpdateView.as_view(),
        name="comment-update",
    ),
    path(
        "comments/<int:pk>/delete/",
        views.CommentDeleteView.as_view(),
        name="comment-delete",
    ),
]
