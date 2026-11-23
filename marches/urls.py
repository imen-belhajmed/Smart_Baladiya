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
]