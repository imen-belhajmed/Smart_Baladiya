import uuid
from django.db import models
from django.conf import settings


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
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Demande administrative"
        verbose_name_plural = "Demandes administratives"

    def __str__(self):
        return f"{self.get_type_document_display()} - {self.citoyen} ({self.get_statut_display()})"