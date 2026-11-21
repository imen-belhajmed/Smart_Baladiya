from django.conf import settings
from django.db import models


class CategorieIncident(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Catégorie d'incident"
        verbose_name_plural = "Catégories d'incident"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Incident(models.Model):
    class Statut(models.TextChoices):
        SIGNALE = "signale", "Signalé"
        EN_COURS = "en_cours", "En cours"
        RESOLU = "resolu", "Résolu"

    titre = models.CharField(max_length=200)
    categorie = models.ForeignKey(
        CategorieIncident, on_delete=models.PROTECT, related_name="incidents"
    )
    description = models.TextField()
    statut = models.CharField(
        max_length=20, choices=Statut.choices, default=Statut.SIGNALE
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    photo = models.ImageField(upload_to="incidents/%Y/%m/", blank=True, null=True)
    date_signalement = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="incidents"
    )
    est_archive = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_signalement"]

    def __str__(self):
        return f"{self.titre} ({self.get_statut_display()})"