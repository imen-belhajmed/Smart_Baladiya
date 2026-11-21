from django.urls import path
from . import views

app_name = "incidents"

urlpatterns = [
    path("ajouter/", views.ajouter_incident, name="ajouter"),
    path("", views.liste_incidents, name="liste"),
]