from django.contrib import admin
from accounts.admin import smart_admin_site

from .models import DemandeAdministrative, Notification


@admin.register(DemandeAdministrative, site=smart_admin_site)
class DemandeAdministrativeAdmin(admin.ModelAdmin):
    list_display = ('type_document', 'citoyen', 'statut', 'delai_estime_heures', 'date_prevue',
                    'date_creation', 'empreinte_verification')
    list_filter = ('statut', 'type_document', 'date_creation')
    search_fields = ('citoyen__username', 'empreinte_verification', 'motif')
    readonly_fields = ('empreinte_verification', 'empreinte_document', 'date_prevue', 'agent_traitant',
                       'date_creation', 'date_mise_a_jour')
    list_editable = ('statut',)


@admin.register(Notification, site=smart_admin_site)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('destinataire', 'message', 'lue', 'date_creation')
    list_filter = ('lue',)
