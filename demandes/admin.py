from django.contrib import admin
from .models import DemandeAdministrative


@admin.register(DemandeAdministrative)
class DemandeAdministrativeAdmin(admin.ModelAdmin):
    list_display = ('type_document', 'citoyen', 'statut', 'delai_estime_heures', 'date_creation', 'empreinte_verification')
    list_filter = ('statut', 'type_document', 'date_creation')
    search_fields = ('citoyen__username', 'empreinte_verification', 'motif')
    readonly_fields = ('empreinte_verification', 'date_creation', 'date_mise_a_jour')
    list_editable = ('statut',)