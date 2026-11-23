from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Category, Comment, MemberProfile, Thread, ThreadMedia

MAX_MEDIA_FILES_PER_POST = 10
MAX_VIDEO_LINKS_PER_POST = 5


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, list) else [data]
        return [forms.FileField.clean(self, upload, initial) for upload in files]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            "name",
            "description",
            "allow_discussions",
            "allow_events",
        ]


class ThreadForm(forms.ModelForm):
    media_files = MultipleFileField(
        required=False,
        label="Images, GIFs, or videos",
        help_text="Select up to 10 files (25 MB each). Each is inserted at the cursor in the description.",
        widget=MultipleFileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/gif,image/webp,video/mp4,video/webm,video/quicktime",
            }
        ),
    )
    video_links = forms.CharField(
        required=False,
        label="Video links",
        help_text="Add one public YouTube or Vimeo link per line.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = Thread
        fields = [
            "title",
            "category",
            "kind",
            "content",
            "event_start",
            "event_end",
            "location",
            "header_image",
        ]
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 12, "class": "rich-text-input"}
            ),
            "header_image": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/gif,image/webp"}
            ),
            "event_start": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "event_end": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.order_fields(
            [
                "title",
                "category",
                "kind",
                "content",
                "event_start",
                "event_end",
                "location",
                "header_image",
                "media_files",
                "video_links",
            ]
        )
        self.fields["event_start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["event_end"].input_formats = ["%Y-%m-%dT%H:%M"]
        last_media_position = (
            self.instance.media.order_by("-position")
            .values_list("position", flat=True)
            .first()
            if self.instance.pk
            else None
        )
        media_offset = 0 if last_media_position is None else last_media_position + 1
        self.fields["media_files"].widget.attrs["data-media-offset"] = str(media_offset)
        if user is not None and not user.is_staff:
            self.fields["category"].queryset = Category.objects.filter(
                Q(allow_discussions=True) | Q(allow_events=True)
            )

    def clean_media_files(self):
        uploads = self.cleaned_data.get("media_files", [])
        if len(uploads) > MAX_MEDIA_FILES_PER_POST:
            raise forms.ValidationError(
                f"Attach no more than {MAX_MEDIA_FILES_PER_POST} files to a post."
            )
        for upload in uploads:
            media = ThreadMedia(
                kind=ThreadMedia.kind_for_filename(upload.name),
                file=upload,
            )
            try:
                media.full_clean(exclude=("thread", "uploaded_by"))
            except ValidationError as error:
                raise forms.ValidationError(error.messages) from error
            upload.seek(0)
        return uploads

    def clean_video_links(self):
        links = self.cleaned_data.get("video_links", "")
        valid_links = []
        for link in dict.fromkeys(line.strip() for line in links.splitlines() if line.strip()):
            if len(valid_links) >= MAX_VIDEO_LINKS_PER_POST:
                raise forms.ValidationError(
                    f"Add no more than {MAX_VIDEO_LINKS_PER_POST} video links."
                )
            media = ThreadMedia(kind=ThreadMedia.Kind.VIDEO, external_url=link)
            try:
                media.full_clean(exclude=("thread", "uploaded_by", "file"))
            except ValidationError as error:
                raise forms.ValidationError(error.messages) from error
            valid_links.append(link)
        return valid_links

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("kind") == Thread.Kind.DISCUSSION:
            cleaned_data["event_start"] = None
            cleaned_data["event_end"] = None
            cleaned_data["location"] = ""
            cleaned_data["header_image"] = None
        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 8, "class": "rich-text-input"}
            ),
        }


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ["image"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Profile images must be 5 MB or smaller.")
        return image
