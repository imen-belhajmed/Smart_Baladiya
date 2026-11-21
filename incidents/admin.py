from django.contrib import admin
from .models import CategorieIncident, Incident

admin.site.register(CategorieIncident)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "statut", "auteur", "date_signalement", "est_archive")
    list_filter = ("statut", "categorie", "est_archive")