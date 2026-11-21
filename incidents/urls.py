from django.urls import path
from . import views

app_name = "incidents"

urlpatterns = [
    path("", views.liste_incidents, name="list"),
    path("ajouter/", views.ajouter_incident, name="ajouter"),
    path("<int:pk>/", views.detail_incident, name="detail"),
]