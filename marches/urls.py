from django.urls import path

from . import views

app_name = 'marches'

urlpatterns = [
    # Emplacements
    path('', views.liste_emplacements, name='list'),
    path('emplacements/ajouter/', views.ajouter_emplacement, name='ajouter_emplacement'),
    path('emplacements/<int:pk>/', views.detail_emplacement, name='detail_emplacement'),
    path(
        'emplacements/<int:pk>/modifier/',
        views.modifier_emplacement,
        name='modifier_emplacement',
    ),
    path(
        'emplacements/<int:pk>/supprimer/',
        views.supprimer_emplacement,
        name='supprimer_emplacement',
    ),

    # Commerçants
    path('commercants/', views.liste_commercants, name='liste_commercants'),
    path('commercants/ajouter/', views.ajouter_commercant, name='ajouter_commercant'),
    path('commercants/<int:pk>/', views.detail_commercant, name='detail_commercant'),
    path(
        'commercants/<int:pk>/modifier/',
        views.modifier_commercant,
        name='modifier_commercant',
    ),
    path(
        'commercants/<int:pk>/supprimer/',
        views.supprimer_commercant,
        name='supprimer_commercant',
    ),

    # Espace Citoyen : Demandes & Mes permis
    path('demandes/nouvelle/', views.soumettre_demande_permis, name='soumettre_demande'),
    path('mes-demandes/', views.mes_demandes_permis, name='mes_demandes'),

    # Espace Agent : Gestion des Demandes & Permis
    path('demandes/', views.liste_demandes_permis, name='liste_demandes_permis'),
    path(
        'demandes/<int:pk>/accepter/',
        views.accepter_demande_permis,
        name='accepter_demande',
    ),
    path(
        'demandes/<int:pk>/refuser/',
        views.refuser_demande_permis,
        name='refuser_demande',
    ),
    path('permis/', views.liste_permis, name='liste_permis'),
    path('permis/creer/', views.creer_permis, name='creer_permis'),
    path('permis/<int:pk>/', views.detail_permis, name='detail_permis'),
    path(
        'permis/<int:pk>/statut/<str:nouveau_statut>/',
        views.changer_statut_permis,
        name='changer_statut_permis',
    ),
]