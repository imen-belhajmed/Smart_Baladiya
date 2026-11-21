from django import forms

from .models import DemandeAdministrative


class BootstrapMixin:
    """Applique les classes Bootstrap aux champs (apparence du module)."""

    def _bootstrap(self):
        for champ in self.fields.values():
            w = champ.widget
            classe = 'form-select' if isinstance(w, forms.Select) else 'form-control'
            w.attrs['class'] = (w.attrs.get('class', '') + ' ' + classe).strip()


class DemandeAdministrativeForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DemandeAdministrative
        fields = ['type_document', 'motif', 'piece_jointe']
        widgets = {
            'motif': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Précisez le motif de votre demande...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()


class TraitementForm(BootstrapMixin, forms.ModelForm):
    """Formulaire de l'agent municipal : statut, observation, document délivré."""

    class Meta:
        model = DemandeAdministrative
        fields = ['statut', 'commentaire_agent', 'document_delivre']
        widgets = {'commentaire_agent': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['statut'].choices = [c for c in DemandeAdministrative.STATUT_CHOICES if c[0] != 'annulee']
        self._bootstrap()

    def clean(self):
        data = super().clean()
        if data.get('statut') == 'validee' and not (data.get('document_delivre') or self.instance.document_delivre):
            self.add_error('document_delivre',
                           "Joignez le document délivré : il sera sécurisé par une empreinte SHA-256.")
        return data


class VerificationForm(BootstrapMixin, forms.Form):
    code = forms.UUIDField(label="Empreinte unique (code de la demande)")
    document = forms.FileField(label="Document à comparer (facultatif)", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bootstrap()
