from django.urls import path
from . import views

app_name = 'actualites'

urlpatterns = [
    path('', views.liste_alertes, name='list'),
    path('alertes/', views.liste_alertes, name='liste_alertes'),
    path('alertes/creer/', views.creer_alerte, name='creer_alerte'),
    path('alertes/<int:pk>/', views.detail_alerte, name='detail_alerte'),
    path('alertes/<int:pk>/modifier/', views.modifier_alerte, name='modifier_alerte'),
    path('alertes/<int:pk>/supprimer/', views.supprimer_alerte, name='supprimer_alerte'),
    path('alertes/<int:pk>/archiver/', views.archiver_alerte, name='archiver_alerte'),
]

