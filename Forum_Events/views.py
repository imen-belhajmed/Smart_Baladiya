from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.db.models import Count, Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import CategoryForm, CommentForm, MemberProfileForm, ThreadForm
from accounts.forms import RegistrationForm
from .models import Category, Comment, MemberProfile, Thread, ThreadMedia


def save_thread_media(thread, form, user):
    last_media_position = (
        thread.media.order_by("-position").values_list("position", flat=True).first()
    )
    position = 0 if last_media_position is None else last_media_position + 1
    for upload in form.cleaned_data.get("media_files", []):
        media = ThreadMedia(
            thread=thread,
            position=position,
            kind=ThreadMedia.kind_for_filename(upload.name),
            file=upload,
            uploaded_by=user,
        )
        media.full_clean()
        media.save()
        position += 1
    for video_url in form.cleaned_data.get("video_links", []):
        media = ThreadMedia(
            thread=thread,
            position=position,
            kind=ThreadMedia.Kind.VIDEO,
            external_url=video_url,
            uploaded_by=user,
        )
        media.full_clean()
        media.save()
        position += 1


class IntegratedUserCreationForm(UserCreationForm):
    pass


class DashboardView(TemplateView):
    template_name = "forum_events/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = (
            Category.objects.exclude(name__iexact="Events")
            .annotate(
                thread_count=Count(
                    "threads",
                    filter=Q(threads__kind=Thread.Kind.DISCUSSION),
                    distinct=True,
                )
            )
        )
        context["recent_threads"] = (
            Thread.objects.filter(kind=Thread.Kind.DISCUSSION)
            .exclude(category__name__iexact="Events")
            .select_related("category", "author")[:8]
        )
        context["events"] = (
            Thread.objects.filter(kind=Thread.Kind.EVENT)
            .select_related("category", "author")
            .order_by("event_start")
        )
        return context


class SignUpView(CreateView):
    form_class = IntegratedUserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("forum:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class ProfileView(TemplateView):
    template_name = "forum_events/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )
        context["profile"] = profile
        context["member_profile"], _ = MemberProfile.objects.get_or_create(
            user=profile
        )
        context["profile_threads"] = Thread.objects.filter(
            author=profile
        ).select_related("category", "author").prefetch_related("comments")
        context["profile_comments"] = (
            Comment.objects.filter(author=profile)
            .select_related("thread", "thread__category")
            .order_by("-created_at")
        )
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    form_class = MemberProfileForm
    template_name = "forum_events/profile_form.html"

    def get_object(self, queryset=None):
        if self.request.user.get_username() != self.kwargs["username"]:
            raise Http404
        profile, _ = MemberProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_success_url(self):
        return reverse(
            "forum:profile", kwargs={"username": self.request.user.username}
        )


class CategoryListView(ListView):
    model = Category
    context_object_name = "categories"
    template_name = "forum_events/category_list.html"

    def get_queryset(self):
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().exclude(name__iexact="Events")


class ThreadListView(ListView):
    model = Thread
    context_object_name = "threads"
    template_name = "forum_events/thread_list.html"
    thread_kind = Thread.Kind.DISCUSSION
    page_title = "Forums"

    def get_queryset(self):
        queryset = (
            Thread.objects.filter(kind=self.thread_kind)
            .select_related("category", "author")
            .prefetch_related("comments")
        )
        if self.thread_kind == Thread.Kind.DISCUSSION:
            queryset = queryset.exclude(category__name__iexact="Events")
        self.search_query = self.request.GET.get("q", "").strip()
        if self.search_query:
            queryset = queryset.filter(
                Q(title__icontains=self.search_query)
                | Q(content__icontains=self.search_query)
                | Q(category__name__icontains=self.search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["search_query"] = getattr(self, "search_query", "")
        category = getattr(self, "category", None)
        context["category"] = category
        context["is_event_list"] = self.thread_kind == Thread.Kind.EVENT
        events = (
            Thread.objects.filter(kind=Thread.Kind.EVENT)
            .select_related("category", "author")
            .prefetch_related("comments")
            .order_by("event_start")
        )
        if context["search_query"]:
            events = events.filter(
                Q(title__icontains=context["search_query"])
                | Q(content__icontains=context["search_query"])
                | Q(category__name__icontains=context["search_query"])
            )
        context["events"] = events
        context["categories"] = (
            []
            if category
            else Category.objects.exclude(name__iexact="Events")
            .annotate(
                thread_count=Count(
                    "threads",
                    filter=Q(threads__kind=Thread.Kind.DISCUSSION),
                    distinct=True,
                ),
                comment_count=Count(
                    "threads__comments",
                    filter=Q(threads__kind=Thread.Kind.DISCUSSION),
                    distinct=True,
                ),
            )
            .prefetch_related(
                Prefetch(
                    "threads",
                    queryset=Thread.objects.select_related("category", "author")
                    .prefetch_related("comments")
                    .filter(kind=Thread.Kind.DISCUSSION)
                    .order_by("-created_at")[:5],
                    to_attr="preview_threads",
                )
            )
        )
        context["create_label"] = "Add discussion or event"
        return context


class CategoryThreadListView(ThreadListView):
    def get_queryset(self):
        self.category = get_object_or_404(Category, pk=self.kwargs["pk"])
        if self.category.name.casefold() == "events":
            self.thread_kind = Thread.Kind.EVENT
            self.page_title = "Upcoming events"
        return super().get_queryset().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not context["is_event_list"]:
            context["page_title"] = f"{self.category.name} threads"
        return context


class EventListView(ThreadListView):
    thread_kind = Thread.Kind.EVENT
    page_title = "Upcoming events"


class ThreadDetailView(DetailView):
    model = Thread
    context_object_name = "thread"
    template_name = "forum_events/thread_detail.html"

    def get_queryset(self):
        return Thread.objects.select_related("category", "author").prefetch_related(
            "comments__author"
        )


@method_decorator(staff_member_required, name="dispatch")
class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "forum_events/object_form.html"
    success_url = reverse_lazy("forum:category-list")
    extra_context = {
        "page_title": "Add category",
        "cancel_url": reverse_lazy("forum:category-list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Category added.")
        return super().form_valid(form)


@method_decorator(staff_member_required, name="dispatch")
class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "forum_events/object_form.html"
    success_url = reverse_lazy("forum:category-list")
    extra_context = {
        "page_title": "Edit category",
        "cancel_url": reverse_lazy("forum:category-list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Category updated.")
        return super().form_valid(form)


@method_decorator(staff_member_required, name="dispatch")
class CategoryDeleteView(DeleteView):
    model = Category
    template_name = "forum_events/confirm_delete.html"
    success_url = reverse_lazy("forum:category-list")
    extra_context = {"cancel_url": reverse_lazy("forum:category-list")}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                "This category still has threads. Move or delete them before deleting the category.",
            )
            return redirect(self.success_url)


class ThreadCreateView(LoginRequiredMixin, CreateView):
    model = Thread
    form_class = ThreadForm
    template_name = "forum_events/object_form.html"
    extra_context = {
        "page_title": "Add discussion or event",
        "cancel_url": reverse_lazy("forum:thread-list"),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_staff:
            context["page_title"] = "Add discussion or event"
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(
            self.request,
            f"{form.instance.get_kind_display()} added.",
        )
        response = super().form_valid(form)
        save_thread_media(self.object, form, self.request.user)
        return response

    def get_success_url(self):
        return reverse("forum:thread-detail", kwargs={"pk": self.object.pk})


@method_decorator(staff_member_required, name="dispatch")
class ThreadUpdateView(UpdateView):
    model = Thread
    form_class = ThreadForm
    template_name = "forum_events/object_form.html"
    extra_context = {
        "page_title": "Edit discussion or event",
        "cancel_url": reverse_lazy("forum:thread-list"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Discussion or event updated.")
        response = super().form_valid(form)
        save_thread_media(self.object, form, self.request.user)
        return response

    def get_success_url(self):
        return reverse("forum:thread-detail", kwargs={"pk": self.object.pk})


@method_decorator(staff_member_required, name="dispatch")
class ThreadDeleteView(DeleteView):
    model = Thread
    template_name = "forum_events/confirm_delete.html"
    success_url = reverse_lazy("forum:thread-list")
    extra_context = {"cancel_url": reverse_lazy("forum:thread-list")}

    def form_valid(self, form):
        messages.success(self.request, "Discussion or event deleted.")
        return super().form_valid(form)


@staff_member_required
@require_POST
def toggle_thread_lock(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    thread.is_locked = not thread.is_locked
    thread.save(update_fields=["is_locked", "updated_at"])
    status = "locked" if thread.is_locked else "unlocked"
    messages.success(request, f"Thread {status}.")
    return redirect("forum:thread-detail", pk=thread.pk)


@method_decorator(login_required, name="dispatch")
class ThreadCommentCreateView(CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "forum_events/object_form.html"
    page_title = "Add comment"

    def dispatch(self, request, *args, **kwargs):
        self.thread = get_object_or_404(Thread, pk=kwargs["thread_pk"])
        if self.thread.is_locked:
            messages.error(
                request, "This thread is locked and cannot receive new comments."
            )
            return redirect("forum:thread-detail", pk=self.thread.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["cancel_url"] = reverse(
            "forum:thread-detail", kwargs={"pk": self.thread.pk}
        )
        return context

    def form_valid(self, form):
        form.instance.thread = self.thread
        form.instance.author = self.request.user
        messages.success(self.request, "Comment added.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("forum:thread-detail", kwargs={"pk": self.thread.pk})


@method_decorator(staff_member_required, name="dispatch")
class CommentUpdateView(UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = "forum_events/object_form.html"
    extra_context = {"page_title": "Edit comment"}

    def get_queryset(self):
        return Comment.objects.select_related("thread")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse(
            "forum:thread-detail", kwargs={"pk": self.object.thread_id}
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "Comment updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("forum:thread-detail", kwargs={"pk": self.object.thread_id})


@method_decorator(staff_member_required, name="dispatch")
class CommentDeleteView(DeleteView):
    model = Comment
    template_name = "forum_events/confirm_delete.html"

    def get_queryset(self):
        return Comment.objects.select_related("thread")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse(
            "forum:thread-detail", kwargs={"pk": self.object.thread_id}
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "Comment deleted.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("forum:thread-detail", kwargs={"pk": self.object.thread_id})
