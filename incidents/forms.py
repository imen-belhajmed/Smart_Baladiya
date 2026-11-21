from django import forms
from .models import Incident

MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 Mo
TYPES_PHOTO = ("image/jpeg", "image/png", "image/webp")


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ["titre", "categorie", "description", "latitude", "longitude", "photo"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "latitude": forms.NumberInput(attrs={"step": "any", "placeholder": "ex: 36.806389"}),
            "longitude": forms.NumberInput(attrs={"step": "any", "placeholder": "ex: 10.181667"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def clean_latitude(self):
        lat = self.cleaned_data["latitude"]
        if not -90 <= lat <= 90:
            raise forms.ValidationError("La latitude doit être comprise entre -90 et 90.")
        return lat

    def clean_longitude(self):
        lng = self.cleaned_data["longitude"]
        if not -180 <= lng <= 180:
            raise forms.ValidationError("La longitude doit être comprise entre -180 et 180.")
        return lng

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "content_type"):  # nouvelle photo uploadée
            if photo.size > MAX_PHOTO_SIZE:
                raise forms.ValidationError("La photo ne doit pas dépasser 5 Mo.")
            if photo.content_type not in TYPES_PHOTO:
                raise forms.ValidationError("Formats acceptés : JPEG, PNG ou WebP.")
        return photo