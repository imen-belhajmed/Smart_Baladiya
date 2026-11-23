from django.contrib import admin
from accounts.admin import smart_admin_site
from .models import CategorieIncident, Incident

smart_admin_site.register(CategorieIncident)


@admin.register(Incident, site=smart_admin_site)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "statut", "auteur", "date_signalement", "est_archive")
    list_filter = ("statut", "categorie", "est_archive")