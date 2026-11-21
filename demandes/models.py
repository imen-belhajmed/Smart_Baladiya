import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from . import services


class DemandeAdministrative(models.Model):
    TYPE_CHOICES = [
        ('extrait_naissance', 'Extrait de naissance'),
        ('legalisation', 'Légalisation de signature / copie conforme'),
        ('residence', 'Certificat de résidence'),
        ('autre', 'Autre document administratif'),
    ]

    STATUT_CHOICES = [
        ('en_attente', 'En attente de traitement'),
        ('en_cours', 'En cours de vérification'),
        ('validee', 'Validée / Prête'),
        ('rejetee', 'Rejetée'),
        ('annulee', 'Annulée'),
    ]

    citoyen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='demandes_administratives',
        verbose_name="Citoyen demandeur"
    )
    type_document = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name="Type de document"
    )
    motif = models.TextField(
        blank=True,
        verbose_name="Motif ou précisions"
    )
    piece_jointe = models.FileField(
        upload_to='demandes/pieces_jointes/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Pièce justificative"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )
    delai_estime_heures = models.PositiveIntegerField(
        default=24,
        verbose_name="Délai estimé (en heures)"
    )
    empreinte_verification = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="Empreinte unique de vérification"
    )
    commentaire_agent = models.TextField(
        blank=True,
        verbose_name="Observation de l'agent municipal"
    )
    # ----- Ajouts : suivi intelligent des délais -----
    date_prevue = models.DateTimeField(
        null=True, blank=True, editable=False,
        verbose_name="Date de traitement prévue"
    )
    retard_notifie = models.BooleanField(default=False, editable=False)
    # ----- Ajouts : sécurisation des documents -----
    agent_traitant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, editable=False,
        on_delete=models.SET_NULL,
        related_name='demandes_traitees',
        verbose_name="Agent traitant"
    )
    document_delivre = models.FileField(
        upload_to='demandes/documents_delivres/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Document délivré"
    )
    empreinte_document = models.CharField(
        max_length=64, blank=True, editable=False,
        verbose_name="Empreinte SHA-256 du document délivré"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Demande administrative"
        verbose_name_plural = "Demandes administratives"

    def __str__(self):
        return f"{self.get_type_document_display()} - {self.citoyen} ({self.get_statut_display()})"

    def get_absolute_url(self):
        return reverse('demandes:detail', args=[self.pk])

    @property
    def modifiable(self):
        return self.statut == 'en_attente'

    @property
    def en_retard(self):
        return (self.statut in ('en_attente', 'en_cours') and self.date_prevue is not None
                and timezone.now() > self.date_prevue)

    def save(self, *args, **kwargs):
        nouveau = self.pk is None
        ancien_statut = None
        if not nouveau:
            ancien_statut = type(self).objects.filter(pk=self.pk).values_list('statut', flat=True).first()
        if nouveau:
            self.delai_estime_heures = services.estimer_delai_heures(self.type_document)
            self.date_prevue = timezone.now() + timedelta(hours=self.delai_estime_heures)
        super().save(*args, **kwargs)
        if nouveau:
            services.notifier_creation(self)
        elif ancien_statut and ancien_statut != self.statut:
            services.notifier_changement_statut(self)


class Notification(models.Model):
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications_demandes',
    )
    message = models.CharField(max_length=255)
    lien = models.CharField(max_length=255, blank=True)
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return self.message
