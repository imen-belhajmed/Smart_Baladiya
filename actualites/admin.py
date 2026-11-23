from django.contrib import admin
from accounts.admin import smart_admin_site
from .models import Alerte


@admin.register(Alerte, site=smart_admin_site)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ('titre', 'niveau_urgence', 'auteur', 'date_publication', 'date_expiration', 'est_active', 'piece_jointe')
    list_filter = ('niveau_urgence', 'date_publication', 'date_expiration')
    search_fields = ('titre', 'contenu', 'auteur__username', 'auteur__first_name', 'auteur__last_name')
    readonly_fields = ('date_publication', 'date_mise_a_jour', 'est_active')
    fieldsets = (
        ('Informations Générales', {
            'fields': ('titre', 'contenu', 'niveau_urgence', 'auteur')
        }),
        ('Validité & Fichiers', {
            'fields': ('date_expiration', 'piece_jointe', 'est_active')
        }),
        ('Métadonnées', {
            'fields': ('date_publication', 'date_mise_a_jour'),
            'classes': ('collapse',)
        }),
    )

    def est_active(self, obj):
        return obj.est_active
    est_active.boolean = True
    est_active.short_description = "Active ?"
