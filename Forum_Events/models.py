import os
import re
from urllib.parse import parse_qs, urlsplit

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


MAX_MEDIA_SIZE = 25 * 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}


def validate_upload_size(upload):
    if upload.size > MAX_MEDIA_SIZE:
        raise ValidationError("Each media file must be 25 MB or smaller.")


def get_video_embed_url(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    try:
        port = parsed.port
    except ValueError as error:
        raise ValidationError("Use a secure HTTPS video link.") from error
    if parsed.scheme != "https" or parsed.username or parsed.password or port not in (None, 443):
        raise ValidationError("Use a secure HTTPS video link.")

    video_id = ""
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            match = re.fullmatch(r"/(?:embed|shorts|live)/([A-Za-z0-9_-]{11})/?", parsed.path)
            if match:
                video_id = match.group(1)
        if video_id:
            return f"https://www.youtube-nocookie.com/embed/{video_id}"
    elif host == "youtu.be":
        match = re.fullmatch(r"/([A-Za-z0-9_-]{11})/?", parsed.path)
        if match:
            return f"https://www.youtube-nocookie.com/embed/{match.group(1)}"
    elif host in {"vimeo.com", "www.vimeo.com"}:
        match = re.fullmatch(r"/(?:video/)?([0-9]+)/?", parsed.path)
        if match:
            return f"https://player.vimeo.com/video/{match.group(1)}"

    raise ValidationError("Use a valid YouTube or Vimeo video link.")


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
    header_image = models.ImageField(
        upload_to="forum_events/headers/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_upload_size],
    )
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
            if not self.event_end:
                errors["event_end"] = "Events need an end date and time."
            if self.event_start and self.event_end and self.event_end < self.event_start:
                errors["event_end"] = "The event end must be after its start."
        elif self.event_start or self.event_end or self.location or self.header_image:
            errors["kind"] = "Only events can have event dates, a location, or a header image."

        if errors:
            raise ValidationError(errors)


class ThreadMedia(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image", "Image or GIF"
        VIDEO = "video", "Video"

    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="media"
    )
    position = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(
        upload_to="forum_events/media/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_upload_size],
    )
    external_url = models.URLField(blank=True)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="forum_media",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]
        verbose_name = "Thread media"
        verbose_name_plural = "Thread media"

    def __str__(self):
        return self.caption or f"{self.get_kind_display()} for {self.thread}"

    @classmethod
    def kind_for_filename(cls, filename):
        extension = os.path.splitext(filename)[1].lower()
        if extension in IMAGE_EXTENSIONS:
            return cls.Kind.IMAGE
        if extension in VIDEO_EXTENSIONS:
            return cls.Kind.VIDEO
        return ""

    def clean(self):
        errors = {}
        has_file = bool(self.file)
        has_url = bool(self.external_url)
        if has_file == has_url:
            errors["file"] = "Provide exactly one uploaded file or video link."

        if has_url:
            if self.kind != self.Kind.VIDEO:
                errors["external_url"] = "Only videos can use an external link."
            else:
                try:
                    get_video_embed_url(self.external_url)
                except ValidationError as error:
                    errors["external_url"] = error

        if has_file:
            extension = os.path.splitext(self.file.name)[1].lower()
            if self.kind == self.Kind.IMAGE:
                if extension not in IMAGE_EXTENSIONS:
                    errors["file"] = "Use a JPG, PNG, GIF, or WEBP image."
                else:
                    try:
                        self.file.seek(0)
                        with Image.open(self.file) as image:
                            expected_formats = {
                                ".jpg": "JPEG",
                                ".jpeg": "JPEG",
                                ".png": "PNG",
                                ".gif": "GIF",
                                ".webp": "WEBP",
                            }
                            if image.format != expected_formats[extension]:
                                errors["file"] = "The image format does not match its file extension."
                            image.verify()
                    except (OSError, UnidentifiedImageError, ValueError):
                        errors["file"] = "The uploaded image is invalid."
                    finally:
                        self.file.seek(0)
            elif extension not in VIDEO_EXTENSIONS:
                errors["file"] = "Use an MP4, WEBM, or MOV video."
            else:
                try:
                    self.file.seek(0)
                    signature = self.file.read(12)
                    valid_video = (
                        signature.startswith(b"\x1a\x45\xdf\xa3")
                        if extension == ".webm"
                        else len(signature) >= 8 and signature[4:8] == b"ftyp"
                    )
                    if not valid_video:
                        errors["file"] = "The uploaded video is invalid."
                finally:
                    self.file.seek(0)

        if errors:
            raise ValidationError(errors)

    @property
    def embed_url(self):
        if self.external_url and self.kind == self.Kind.VIDEO:
            try:
                return get_video_embed_url(self.external_url)
            except ValidationError:
                return ""
        return ""

    @property
    def file_content_type(self):
        extension = os.path.splitext(self.file.name)[1].lower() if self.file else ""
        return {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mov": "video/quicktime",
        }.get(extension, "")


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
