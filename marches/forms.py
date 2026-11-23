
from django import forms

from .models import Emplacement


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
