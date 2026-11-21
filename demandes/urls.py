from django.urls import path

from . import views

app_name = 'demandes'

urlpatterns = [
    path('', views.liste_demandes, name='liste'),
    path('nouvelle/', views.creer_demande, name='creer'),
    path('<int:pk>/', views.detail_demande, name='detail'),
    path('modifier/<int:pk>/', views.modifier_demande, name='modifier'),
    path('annuler/<int:pk>/', views.annuler_demande, name='annuler'),
    path('supprimer/<int:pk>/', views.supprimer_demande, name='supprimer'),
    path('document/<int:pk>/', views.telecharger_document, name='telecharger'),
    path('notifications/', views.notifications, name='notifications'),
    path('verifier/', views.verifier_document, name='verifier'),
    path('agent/tableau/', views.tableau_bord_agent, name='tableau_agent'),  # Espace agent
    path('agent/traiter/<int:pk>/', views.traiter_demande, name='traiter_demande'),  # Traitement agent
]
