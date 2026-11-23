from django.urls import path

from django.urls import path

from . import views

app_name = 'marches'

urlpatterns = [
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
]