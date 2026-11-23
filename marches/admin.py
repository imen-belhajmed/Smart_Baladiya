from django.contrib import admin

from .models import Commercant, DemandePermis, Emplacement, Notification, Permis


@admin.register(Commercant)
class CommercantAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'cin', 'activite', 'utilisateur')
    search_fields = ('nom', 'prenom', 'cin')


@admin.register(Emplacement)
class EmplacementAdmin(admin.ModelAdmin):
    list_display = ('numero', 'zone', 'activite', 'statut')
    list_filter = ('zone', 'statut')


@admin.register(Permis)
class PermisAdmin(admin.ModelAdmin):
    list_display = ('commercant', 'emplacement', 'date_debut', 'date_fin', 'statut')
    list_filter = ('statut',)
    readonly_fields = ('code', 'date_creation')

    search_fields = ('commercant__nom', 'commercant__prenom', 'emplacement__numero')

@admin.register(DemandePermis)
class DemandePermisAdmin(admin.ModelAdmin):
    list_display = ('commercant', 'zone_souhaitee', 'activite', 'date_debut_souhaitee', 'statut')
    list_filter = ('statut',)
    search_fields = ('commercant__nom', 'commercant__prenom', 'commercant__cin')

admin.site.register(Notification)

