from django import forms
from django.utils import timezone

from .models import Commercant, DemandePermis, Emplacement, Permis


class EmplacementForm(forms.ModelForm):
    class Meta:
        model = Emplacement
        fields = [
            'numero',
            'zone',
            'activite',
            'statut',
            'latitude',
            'longitude',
        ]
        widgets = {
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : A3',
            }),
            'zone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Centre-ville',
            }),
            'activite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Fruits et légumes',
            }),
            'statut': forms.Select(attrs={
                'class': 'form-control',
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'Latitude',
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'Longitude',
            }),
        }


class CommercantForm(forms.ModelForm):
    class Meta:
        model = Commercant
        fields = [
            'nom',
            'prenom',
            'cin',
            'telephone',
            'activite',
            'actif',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Ben Ali',
            }),
            'prenom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Ahmed',
            }),
            'cin': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '8',
                'placeholder': 'Ex : 09876543',
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : 20 123 456',
            }),
            'activite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Fruits et légumes',
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_cin(self):
        cin = self.cleaned_data['cin'].strip()
        if not cin.isdigit() or len(cin) != 8:
            raise forms.ValidationError(
                "Le numéro de CIN doit contenir exactement 8 chiffres."
            )
        return cin


# ==========================================
# FORMULAIRES BLOC 4 : DEMANDES & PERMIS
# ==========================================

class DemandePermisForm(forms.ModelForm):
    """Formulaire citoyen : crée/met à jour le profil commerçant si besoin + la demande."""
    nom = forms.CharField(
        label="Nom",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre nom'}),
    )
    prenom = forms.CharField(
        label="Prénom",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre prénom'}),
    )
    cin = forms.CharField(
        label="CIN (8 chiffres)",
        max_length=8,
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '8', 'placeholder': 'Ex : 09876543'}),
    )
    telephone = forms.CharField(
        label="Téléphone",
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : 20 123 456'}),
    )

    class Meta:
        model = DemandePermis
        fields = [
            'zone_souhaitee',
            'activite',
            'date_debut_souhaitee',
            'duree_jours',
            'commentaire',
        ]
        widgets = {
            'zone_souhaitee': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Centre-ville, Zone A...',
            }),
            'activite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Fruits et légumes, Artisanat...',
            }),
            'date_debut_souhaitee': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'duree_jours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '365',
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Précisions éventuelles sur votre stand ou vos besoins...',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        profil = getattr(user, 'profil_commercant', None) if user else None
        if profil:
            self.fields['nom'].initial = profil.nom
            self.fields['prenom'].initial = profil.prenom
            self.fields['cin'].initial = profil.cin
            self.fields['telephone'].initial = profil.telephone
            self.fields['activite'].initial = profil.activite
        elif user:
            self.fields['nom'].initial = user.last_name
            self.fields['prenom'].initial = user.first_name

    def clean_cin(self):
        cin = self.cleaned_data['cin'].strip()
        if not cin.isdigit() or len(cin) != 8:
            raise forms.ValidationError("Le numéro de CIN doit contenir exactement 8 chiffres.")
        profil = getattr(self.user, 'profil_commercant', None) if self.user else None
        qs = Commercant.objects.filter(cin=cin)
        if profil:
            qs = qs.exclude(pk=profil.pk)
        if qs.exists():
            raise forms.ValidationError("Ce numéro de CIN est déjà associé à un autre commerçant.")
        return cin

    def clean_date_debut_souhaitee(self):
        date_debut = self.cleaned_data['date_debut_souhaitee']
        if date_debut < timezone.localdate():
            raise forms.ValidationError("La date de début souhaitée ne peut pas être dans le passé.")
        return date_debut


class PermisForm(forms.ModelForm):
    """Formulaire agent : création directe ou validation d'une demande."""
    class Meta:
        model = Permis
        fields = [
            'commercant',
            'emplacement',
            'date_debut',
            'date_fin',
            'statut',
        ]
        widgets = {
            'commercant': forms.Select(attrs={'class': 'form-control'}),
            'emplacement': forms.Select(attrs={'class': 'form-control'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, uniquement_libres=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['commercant'].queryset = Commercant.objects.filter(actif=True)
        if uniquement_libres:
            self.fields['emplacement'].queryset = Emplacement.objects.filter(
                statut=Emplacement.Statut.LIBRE
            )


class AccepterDemandeForm(forms.ModelForm):
    """Formulaire agent pour attribuer un emplacement libre et accepter une demande."""
    class Meta:
        model = Permis
        fields = ['emplacement', 'date_debut', 'date_fin']
        widgets = {
            'emplacement': forms.Select(attrs={'class': 'form-control'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['emplacement'].queryset = Emplacement.objects.filter(
            statut=Emplacement.Statut.LIBRE
        )


class RefuserDemandeForm(forms.Form):
    motif_refus = forms.CharField(
        label="Motif du refus",
        max_length=255,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Expliquez la raison du refus au citoyen...',
        }),
    )