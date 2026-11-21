from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        CITOYEN = 'citoyen', 'Citoyen'
        AGENT = 'agent', 'Agent municipal'
        CONTROLEUR = 'controleur', 'Contrôleur de marché'
        MODERATEUR = 'moderateur', 'Modérateur'
        COLLECTE = 'collecte', 'Agent de collecte'
        ADMIN = 'admin', 'Administrateur'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITOYEN,
    )
    telephone = models.CharField(max_length=15, blank=True)

    @property
    def est_agent(self):
        return self.is_superuser or self.role in (self.Role.AGENT, self.Role.ADMIN)

    def save(self, *args, **kwargs):
        if self.role in (self.Role.AGENT, self.Role.ADMIN):
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username
