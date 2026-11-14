from django import forms
from .models import DemandeAdministrative


class DemandeAdministrativeForm(forms.ModelForm):
    class Meta:
        model = DemandeAdministrative
        fields = ['type_document', 'motif', 'piece_jointe']
        widgets = {
            'type_document': forms.Select(attrs={'class': 'form-select'}),
            'motif': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Précisez le motif de votre demande...'
            }),
            'piece_jointe': forms.FileInput(attrs={'class': 'form-control'}),
        }