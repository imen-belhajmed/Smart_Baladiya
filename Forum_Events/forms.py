from django import forms

from .models import Category, Comment, MemberProfile, Thread


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
        ]
        widgets = {
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
        super().__init__(*args, **kwargs)
        self.fields["event_start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["event_end"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("kind") == Thread.Kind.DISCUSSION:
            cleaned_data["event_start"] = None
            cleaned_data["event_end"] = None
            cleaned_data["location"] = ""
        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ["image"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Profile images must be 5 MB or smaller.")
        return image
