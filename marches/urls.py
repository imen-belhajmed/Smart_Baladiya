from django.urls import path

from . import views

app_name = 'marches'

urlpatterns = [
    path('', views.liste_emplacements, name='list'),
   
    path(
        'emplacements/ajouter/',
        views.ajouter_emplacement,
        name='ajouter_emplacement'
    ),
]