from django.urls import path
from . import views

app_name = 'demandes'

urlpatterns = [
    path('', views.liste_demandes, name='liste'),
    path('nouvelle/', views.creer_demande, name='creer'),
    path('modifier/<int:pk>/', views.modifier_demande, name='modifier'),  # Ajout de l'Update
    path('supprimer/<int:pk>/', views.supprimer_demande, name='supprimer'),
    path('verifier/', views.verifier_document, name='verifier'),
    path('agent/tableau/', views.tableau_bord_agent, name='tableau_agent'),  # Espace agent
    path('agent/traiter/<int:pk>/', views.traiter_demande, name='traiter_demande'),  # Traitement agent
]