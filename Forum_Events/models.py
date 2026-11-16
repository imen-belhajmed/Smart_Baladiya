from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    allow_discussions = models.BooleanField(default=True)
    allow_events = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Thread(models.Model):
    class Kind(models.TextChoices):
        DISCUSSION = "discussion", "Discussion"
        EVENT = "event", "Event"

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="threads"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="forum_threads",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.DISCUSSION
    )
    event_start = models.DateTimeField(null=True, blank=True)
    event_end = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}
        if self.category_id:
            if self.kind == self.Kind.DISCUSSION and not self.category.allow_discussions:
                errors["category"] = "This category does not allow discussions."
            elif self.kind == self.Kind.EVENT and not self.category.allow_events:
                errors["category"] = "This category does not allow events."

        if self.kind == self.Kind.EVENT:
            if not self.event_start:
                errors["event_start"] = "Events need a start date and time."
            if self.event_start and self.event_end and self.event_end < self.event_start:
                errors["event_end"] = "The event end must be after its start."
        elif self.event_start or self.event_end or self.location:
            errors["kind"] = "Only events can have event dates or a location."

        if errors:
            raise ValidationError(errors)


class Comment(models.Model):
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="forum_comments",
        null=True,
        blank=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.thread}"


class MemberProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member_profile",
    )
    image = models.ImageField(upload_to="profile_images/", blank=True)

    def __str__(self):
        return f"Profile for {self.user}"
