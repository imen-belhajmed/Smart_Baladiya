from django import forms

from .models import DemandeAdministrative


class DemandeAdministrativeForm(forms.ModelForm):
    class Meta:
        model = DemandeAdministrative
        fields = ['type_document', 'motif', 'piece_jointe']
        widgets = {
            'motif': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Précisez le motif de votre demande...'}),
        }


class TraitementForm(forms.ModelForm):
    """Formulaire de l'agent municipal : statut, observation, document délivré."""

    class Meta:
        model = DemandeAdministrative
        fields = ['statut', 'commentaire_agent', 'document_delivre']
        widgets = {'commentaire_agent': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['statut'].choices = [c for c in DemandeAdministrative.STATUT_CHOICES if c[0] != 'annulee']

    def clean(self):
        data = super().clean()
        if data.get('statut') == 'validee' and not (data.get('document_delivre') or self.instance.document_delivre):
            self.add_error('document_delivre',
                           "Joignez le document délivré : il sera sécurisé par une empreinte SHA-256.")
        return data


class VerificationForm(forms.Form):
    code = forms.UUIDField(label="Empreinte unique (code de la demande)")
    document = forms.FileField(label="Document à comparer (facultatif)", required=False)
