
from django import forms

from .models import Commercant, Emplacement


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