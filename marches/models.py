import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Commercant(models.Model):
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='profil_commercant',
    )
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    cin = models.CharField("CIN", max_length=8, unique=True)
    telephone = models.CharField(max_length=15, blank=True)
    activite = models.CharField("Type d'activité", max_length=100)
    actif = models.BooleanField("Actif", default=True)

    class Meta:
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Emplacement(models.Model):
    class Statut(models.TextChoices):
        LIBRE = 'libre', 'Libre'
        RESERVE = 'reserve', 'Réservé'

    numero = models.CharField("Numéro", max_length=20)
    zone = models.CharField(max_length=100)
    activite = models.CharField("Type d'activité", max_length=100)
    statut = models.CharField(
        max_length=10, choices=Statut.choices, default=Statut.LIBRE
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    class Meta:
        ordering = ['zone', 'numero']
        constraints = [
            models.UniqueConstraint(
                fields=['zone', 'numero'], name='emplacement_unique_par_zone'
            )
        ]

    def __str__(self):
        return f"Étal {self.numero} - {self.zone}"


class Permis(models.Model):
    class Statut(models.TextChoices):
        ACTIF = 'actif', 'Actif'
        SUSPENDU = 'suspendu', 'Suspendu'
        ANNULE = 'annule', 'Annulé'
        EXPIRE = 'expire', 'Expiré'

    commercant = models.ForeignKey(
        Commercant, on_delete=models.PROTECT, related_name='permis'
    )
    emplacement = models.ForeignKey(
        Emplacement, on_delete=models.PROTECT, related_name='permis'
    )
    date_debut = models.DateField("Date de début")
    date_fin = models.DateField("Date de fin")
    statut = models.CharField(
        max_length=10, choices=Statut.choices, default=Statut.ACTIF
    )
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='permis_crees',
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name_plural = 'permis'

    @property
    def est_valide(self):
        aujourdhui = timezone.localdate()
        return (
            self.statut == self.Statut.ACTIF
            and self.date_debut <= aujourdhui <= self.date_fin
        )

    def clean(self):
        if not (self.date_debut and self.date_fin):
            return
        if self.date_fin <= self.date_debut:
            raise ValidationError(
                "La date de fin doit être après la date de début."
            )
        if self.emplacement_id and self.statut in (
            self.Statut.ACTIF,
            self.Statut.SUSPENDU,
        ):
            conflit = Permis.objects.filter(
                emplacement_id=self.emplacement_id,
                statut__in=[self.Statut.ACTIF, self.Statut.SUSPENDU],
                date_debut__lte=self.date_fin,
                date_fin__gte=self.date_debut,
            ).exclude(pk=self.pk)
            if conflit.exists():
                raise ValidationError(
                    "Cet emplacement a déjà un permis sur cette période."
                )

    def __str__(self):
        return f"Permis {self.commercant} - {self.emplacement}"


class Notification(models.Model):
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications_marches',
    )
    permis = models.ForeignKey(
        Permis, null=True, blank=True, on_delete=models.SET_NULL
    )
    message = models.CharField(max_length=255)
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.destinataire} : {self.message[:40]}"
    
class DemandePermis(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        ACCEPTEE = 'acceptee', 'Acceptée'
        REFUSEE = 'refusee', 'Refusée'

    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='demandes_permis'
    )
    zone_souhaitee = models.CharField("Zone souhaitée", max_length=100)
    activite = models.CharField("Type d'activité", max_length=100)
    date_debut_souhaitee = models.DateField("Date de début souhaitée")
    duree_jours = models.PositiveIntegerField("Durée souhaitée (jours)", default=30)
    commentaire = models.TextField("Commentaire", blank=True)
    statut = models.CharField(
        max_length=15, choices=Statut.choices, default=Statut.EN_ATTENTE
    )
    motif_refus = models.CharField("Motif de refus", max_length=255, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Demande {self.commercant} ({self.get_statut_display()})"