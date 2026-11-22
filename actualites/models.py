import os
from django.conf import settings
from django.db import models
from django.utils import timezone


class Alerte(models.Model):
    class Urgence(models.TextChoices):
        FAIBLE = 'faible', 'Faible'
        MOYENNE = 'moyenne', 'Moyenne'
        ELEVEE = 'elevee', 'Élevée'
        CRITIQUE = 'critique', 'Critique'

    titre = models.CharField(
        max_length=200,
        verbose_name="Titre",
        help_text="Titre résumé de l'alerte ou de l'annonce officielle"
    )
    contenu = models.TextField(
        verbose_name="Contenu",
        help_text="Description complète, consignes et informations importantes"
    )
    niveau_urgency_choices = Urgence.choices
    niveau_urgence = models.CharField(
        max_length=20,
        choices=Urgence.choices,
        default=Urgence.MOYENNE,
        verbose_name="Niveau d'urgence"
    )
    date_expiration = models.DateTimeField(
        verbose_name="Date d'expiration",
        help_text="Date et heure de fin de validité de l'alerte"
    )
    piece_jointe = models.FileField(
        upload_to='alertes/pieces_jointes/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Pièce jointe",
        help_text="Document justificatif, arrêté municipal, photo ou plan (max 5 Mo)"
    )
    est_active = models.BooleanField(
        default=True,
        verbose_name="Est active",
        help_text="Indique si l'alerte est actuellement active"
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alertes',
        verbose_name="Auteur"
    )
    date_publication = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de publication"
    )
    date_mise_a_jour = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière mise à jour"
    )

    class Meta:
        ordering = ['-date_publication']
        verbose_name = "Alerte officielle"
        verbose_name_plural = "Alertes officielles"

    def __str__(self):
        return f"[{self.get_niveau_urgence_display()}] {self.titre}"

    def save(self, *args, **kwargs):
        # Synchronise automatiquement l'état actif selon l'échéance
        if self.date_expiration and self.date_expiration <= timezone.now():
            self.est_active = False
        super().save(*args, **kwargs)

    @property
    def est_expiree(self):
        """Indique si l'alerte est déjà expirée."""
        if self.date_expiration:
            return self.date_expiration <= timezone.now()
        return not self.est_active

    @property
    def est_image_piece_jointe(self):
        """Vérifie si la pièce jointe est une image visualisable."""
        if self.piece_jointe:
            ext = os.path.splitext(self.piece_jointe.name)[1].lower()
            return ext in ['.png', '.jpg', '.jpeg', '.webp']
        return False

    @property
    def extension_piece_jointe(self):
        """Retourne l'extension lisible du fichier attaché."""
        if self.piece_jointe:
            return os.path.splitext(self.piece_jointe.name)[1].lower().replace('.', '').upper()
        return ""

    @property
    def badge_classe(self):
        """Retourne la classe CSS de badge appropriée selon l'urgence."""
        mapping = {
            self.Urgence.FAIBLE: 'badge-faible',
            self.Urgence.MOYENNE: 'badge-moyenne',
            self.Urgence.ELEVEE: 'badge-elevee',
            self.Urgence.CRITIQUE: 'badge-critique',
        }
        return mapping.get(self.niveau_urgence, 'badge-moyenne')
