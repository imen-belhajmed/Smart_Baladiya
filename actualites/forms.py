import os
from django import forms
from django.utils import timezone
from django.utils.text import get_valid_filename
from .models import Alerte

# Formats de fichiers autorisés pour les uploads de pièces jointes
EXTENSIONS_AUTORISEES = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.doc', '.docx']
# Taille maximale autorisée : 5 Mo
TAILLE_MAX_FICHIER = 5 * 1024 * 1024  # 5 Mo


class PermissiveClearableFileInput(forms.ClearableFileInput):
    """
    Widget de téléversement permissif :
    Si l'utilisateur coche la case 'Supprimer' et sélectionne en même temps
    un nouveau fichier, le nouveau fichier remplace l'existant sans déclencher
    l'erreur de contradiction standard de Django (FILE_INPUT_CONTRADICTION).
    """
    clear_checkbox_label = "Supprimer la pièce jointe actuelle"
    initial_text = "Fichier actuellement associé"
    input_text = "Sélectionner un nouveau fichier"

    def value_from_datadict(self, data, files, name):
        upload = files.get(name)
        # Si un nouveau fichier est téléversé, il a la priorité absolue (remplacement)
        if upload:
            return upload
        # Sinon, si la case d'effacement est cochée, on supprime le fichier
        if not self.is_required and forms.CheckboxInput().value_from_datadict(
            data, files, self.clear_checkbox_name(name)
        ):
            return False
        return upload


class AlerteForm(forms.ModelForm):
    class Meta:
        model = Alerte
        fields = ['titre', 'contenu', 'niveau_urgence', 'date_expiration', 'piece_jointe']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Ex : Alerte météo - Fortes intempéries prévues",
                'maxlength': '200',
            }),
            'contenu': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': "Précisez l'objet de l'alerte, les mesures à respecter et les secteurs concernés...",
            }),
            'niveau_urgence': forms.Select(attrs={
                'class': 'form-control form-select',
            }),
            'date_expiration': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'piece_jointe': PermissiveClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.png,.jpg,.jpeg,.webp,.doc,.docx',
            }),
        }
        labels = {
            'titre': "Titre de l'alerte",
            'contenu': "Contenu détaillé",
            'niveau_urgence': "Niveau d'urgence",
            'date_expiration': "Date et heure d'expiration",
            'piece_jointe': "Pièce jointe (Arrêté, schéma, communiqué)",
        }
        help_texts = {
            'titre': "Un intitulé clair et explicite pour les citoyens.",
            'contenu': "Fournissez toutes les informations nécessaires à la sécurité ou à l'information des administrés.",
            'date_expiration': "L'alerte ne doit pas expirer dans le passé.",
            'piece_jointe': "Formats acceptés : PDF, PNG, JPG, JPEG, WEBP, DOC, DOCX (Max : 5 Mo).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Assure un pré-remplissage compatible avec le format datetime-local de HTML5
        if self.instance and self.instance.pk and self.instance.date_expiration:
            self.initial['date_expiration'] = self.instance.date_expiration.strftime('%Y-%m-%dT%H:%M')

    def clean_titre(self):
        titre = self.cleaned_data.get('titre', '').strip()
        if len(titre) < 5:
            raise forms.ValidationError("Le titre doit comporter au moins 5 caractères.")
        return titre

    def clean_contenu(self):
        contenu = self.cleaned_data.get('contenu', '').strip()
        if len(contenu) < 10:
            raise forms.ValidationError("Le contenu doit comporter au moins 10 caractères explicatifs.")
        return contenu

    def clean_date_expiration(self):
        date_expiration = self.cleaned_data.get('date_expiration')
        if not date_expiration:
            raise forms.ValidationError("La date d'expiration est obligatoire.")
        if date_expiration <= timezone.now():
            # Si l'alerte existe déjà et qu'on ne modifie pas sa date déjà passée
            if not (self.instance.pk and self.instance.date_expiration == date_expiration):
                raise forms.ValidationError("La date d'expiration doit être ultérieure à la date et heure actuelles.")
        return date_expiration

    def clean_piece_jointe(self):
        piece_jointe = self.cleaned_data.get('piece_jointe')
        if piece_jointe:
            # 1. Validation de la taille du fichier
            if piece_jointe.size > TAILLE_MAX_FICHIER:
                taille_mo = piece_jointe.size / (1024 * 1024)
                raise forms.ValidationError(
                    f"Le fichier est trop volumineux ({taille_mo:.1f} Mo). La taille maximale autorisée est de 5 Mo."
                )

            # 2. Validation de l'extension de fichier
            nom_fichier = piece_jointe.name
            extension = os.path.splitext(nom_fichier)[1].lower()
            if extension not in EXTENSIONS_AUTORISEES:
                formats_str = ", ".join([ext.upper().replace('.', '') for ext in EXTENSIONS_AUTORISEES])
                raise forms.ValidationError(
                    f"Le format '{extension}' n'est pas autorisé. Formats acceptés : {formats_str}."
                )

            # 3. Sécurisation du nom de fichier
            piece_jointe.name = get_valid_filename(nom_fichier)

        return piece_jointe

