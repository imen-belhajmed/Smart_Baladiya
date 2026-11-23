from django.urls import path

from . import views

app_name = "collecte"

urlpatterns = [
    # 1. Gestion des véhicules et équipes
    path("vehicules/nouveau/", views.VehicleCreateView.as_view(), name="vehicle_create"),
    path("equipes/<int:pk>/modifier/", views.TeamUpdateView.as_view(), name="team_update"),

    # 2. Planning et gestion des tournées
    path("tournees/", views.RouteListView.as_view(), name="route_list"),
    path("tournees/nouvelle/", views.RouteCreateView.as_view(), name="route_create"),
    path("tournees/<int:pk>/", views.RouteDetailView.as_view(), name="route_detail"),
    path("tournees/<int:pk>/modifier/", views.RouteUpdateView.as_view(), name="route_update"),
    path("tournees/<int:pk>/supprimer/", views.RouteDeleteView.as_view(), name="route_delete"),

    # 3. Suivi des conteneurs
    path("conteneurs/", views.ContainerListView.as_view(), name="container_list"),

    # 4. Exécution de collecte
    path("arrets/<int:pk>/collecter/", views.MarkStopCollectedView.as_view(), name="mark_stop_collected"),
]
