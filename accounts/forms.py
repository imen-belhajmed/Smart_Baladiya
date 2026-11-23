from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from Forum_Events.models import MemberProfile


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(label="Prenom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    email = forms.EmailField(label="Adresse e-mail", required=False)
    telephone = forms.CharField(label="Telephone", max_length=15, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "telephone",
        )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse e-mail est deja utilisee.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip()
        user.telephone = self.cleaned_data.get("telephone", "").strip()
        user.role = get_user_model().Role.CITOYEN
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "telephone")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if get_user_model().objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Cette adresse e-mail est deja utilisee.")
        return email


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ("image",)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La photo ne doit pas depasser 5 Mo.")
        return image
