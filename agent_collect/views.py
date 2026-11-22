from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import (
    CollectionRouteForm,
    CollectionTeamForm,
    RouteFilterForm,
    RouteStopFormSet,
    VehicleForm,
)
from .models import (
    CollectionAgent,
    CollectionRoute,
    CollectionTeam,
    Container,
    RouteStop,
    Vehicle,
    Zone,
)
from .services import mark_stop_collected


def is_municipal_staff(user) -> bool:
    """Vérifie si l'utilisateur fait partie du personnel municipal ou administratif."""
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.is_staff
            or getattr(user, "est_agent", False)
            or getattr(user, "role", "") in ("agent", "admin")
        )
    )


def get_collection_agent(user) -> CollectionAgent | None:
    """Récupère le profil agent de collecte rattaché à l'utilisateur."""
    if not user.is_authenticated:
        return None
    return getattr(user, "agent_profile", None)


class CollecteAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Accès accordé aux agents de collecte et au personnel municipal."""

    def test_func(self):
        user = self.request.user
        return (
            is_municipal_staff(user)
            or get_collection_agent(user) is not None
            or getattr(user, "role", "") == "collecte"
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request,
            "Accès refusé : espace réservé aux agents de collecte et au personnel municipal.",
        )
        return redirect("home")


class StaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Accès restreint au personnel municipal administratif (gestion matériel et équipes)."""

    def test_func(self):
        return is_municipal_staff(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request,
            "Action réservée aux agents administratifs municipaux.",
        )
        return redirect("collecte:route_list")


# ===========================================================================
# 1. Gestion des véhicules et équipes (CRUD Ressources)
# ===========================================================================

class VehicleCreateView(StaffOnlyMixin, CreateView):
    """Enregistrement d'un nouveau véhicule de collecte."""

    model = Vehicle
    form_class = VehicleForm
    template_name = "agent_collect/vehicle_form.html"
    success_url = reverse_lazy("collecte:route_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Le véhicule {self.object.plate_number} ({self.object.capacity_kg} kg) a été enregistré.",
        )
        return response


class TeamUpdateView(StaffOnlyMixin, UpdateView):
    """Modification d'une équipe de collecte et de ses agents membres."""

    model = CollectionTeam
    form_class = CollectionTeamForm
    template_name = "agent_collect/team_form.html"
    context_object_name = "team"
    success_url = reverse_lazy("collecte:route_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"L'équipe « {self.object.name} » a été mise à jour avec succès.",
        )
        return response


# ===========================================================================
# 2. Gestion des tournées de collecte (CRUD Tournées & RouteStops)
# ===========================================================================

class RouteListView(CollecteAccessMixin, ListView):
    """
    Planning des tournées de collecte.
    Les agents de collecte ne voient que les tournées de leurs équipes.
    Le personnel municipal voit l'ensemble des tournées.
    """

    model = CollectionRoute
    template_name = "agent_collect/route_list.html"
    context_object_name = "routes"

    def get_queryset(self):
        qs = (
            CollectionRoute.objects.select_related("zone", "team", "vehicle")
            .prefetch_related("stops__container")
        )

        user = self.request.user
        if not is_municipal_staff(user):
            agent = get_collection_agent(user)
            if agent:
                qs = qs.filter(team__members=agent)
            else:
                qs = qs.none()

        form = RouteFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get("date"):
                qs = qs.filter(scheduled_date=form.cleaned_data["date"])
            if form.cleaned_data.get("status"):
                qs = qs.filter(status=form.cleaned_data["status"])
            if form.cleaned_data.get("zone"):
                qs = qs.filter(zone=form.cleaned_data["zone"])

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = RouteFilterForm(self.request.GET)
        context["is_staff"] = is_municipal_staff(self.request.user)
        return context


class RouteDetailView(CollecteAccessMixin, DetailView):
    """Consultation détaillée d'une tournée et de la liste ordonnée de ses arrêts."""

    model = CollectionRoute
    template_name = "agent_collect/route_detail.html"
    context_object_name = "route"

    def get_queryset(self):
        qs = (
            CollectionRoute.objects.select_related("zone", "team", "vehicle")
            .prefetch_related(
                "stops__container__collection_point",
                "stops__container__waste_type",
            )
        )
        user = self.request.user
        if not is_municipal_staff(user):
            agent = get_collection_agent(user)
            if agent:
                qs = qs.filter(team__members=agent)
            else:
                qs = qs.none()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        route = self.object
        context["stops"] = route.stops.select_related(
            "container__collection_point", "container__waste_type"
        ).order_by("order")
        context["is_staff"] = is_municipal_staff(self.request.user)
        context["can_edit"] = route.status not in [
            CollectionRoute.Status.COMPLETED,
            CollectionRoute.Status.CANCELLED,
        ]
        context["can_delete"] = route.status in [
            CollectionRoute.Status.PLANNED,
            CollectionRoute.Status.CANCELLED,
        ]
        return context


class RouteCreateView(CollecteAccessMixin, CreateView):
    """Enregistrement d'une nouvelle tournée de collecte avec ses arrêts initiaux."""

    model = CollectionRoute
    form_class = CollectionRouteForm
    template_name = "agent_collect/route_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = RouteStopFormSet(self.request.POST)
        else:
            context["formset"] = RouteStopFormSet()
        context["titre_action"] = "Planifier une nouvelle tournée"
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
            messages.success(
                self.request,
                f"La tournée « {self.object.name} » a été planifiée avec succès.",
            )
            return redirect("collecte:route_detail", pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class RouteUpdateView(CollecteAccessMixin, UpdateView):
    """Modification d'une tournée et réaffectation de son équipe, véhicule ou arrêts."""

    model = CollectionRoute
    form_class = CollectionRouteForm
    template_name = "agent_collect/route_form.html"
    context_object_name = "route"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.status in [CollectionRoute.Status.COMPLETED, CollectionRoute.Status.CANCELLED]:
            messages.error(
                request,
                "Une tournée avec le statut « Terminée » ou « Annulée » ne peut plus être modifiée.",
            )
            return redirect("collecte:route_detail", pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = RouteStopFormSet(self.request.POST, instance=self.object)
        else:
            context["formset"] = RouteStopFormSet(instance=self.object)
        context["titre_action"] = f"Modifier la tournée : {self.object.name}"
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
            messages.success(
                self.request,
                f"La tournée « {self.object.name} » a été mise à jour avec succès.",
            )
            return redirect("collecte:route_detail", pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class RouteDeleteView(CollecteAccessMixin, DeleteView):
    """Suppression d'une tournée obsolète (autorisée uniquement pour 'planned' ou 'cancelled')."""

    model = CollectionRoute
    template_name = "agent_collect/route_confirm_delete.html"
    context_object_name = "route"
    success_url = reverse_lazy("collecte:route_list")

    def dispatch(self, request, *args, **kwargs):
        route = self.get_object()
        if route.status not in [CollectionRoute.Status.PLANNED, CollectionRoute.Status.CANCELLED]:
            messages.error(
                request,
                "Seules les tournées avec le statut « Planifiée » ou « Annulée » peuvent être supprimées.",
            )
            return redirect("collecte:route_detail", pk=route.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nom_tournee = self.object.name
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"La tournée « {nom_tournee} » a été supprimée de la base de données.",
        )
        return response


# ===========================================================================
# 3. Suivi des conteneurs
# ===========================================================================

class ContainerListView(CollecteAccessMixin, ListView):
    """Affichage des conteneurs avec leur niveau de remplissage et filtres par zone/statut."""

    model = Container
    template_name = "agent_collect/container_list.html"
    context_object_name = "containers"

    def get_queryset(self):
        qs = (
            Container.objects.select_related("collection_point__zone", "waste_type")
            .order_by("-fill_level", "code")
        )

        zone_id = self.request.GET.get("zone", "").strip()
        if zone_id:
            qs = qs.filter(collection_point__zone_id=zone_id)

        statut = self.request.GET.get("statut", "").strip()
        if statut:
            qs = qs.filter(status=statut)

        recherche = self.request.GET.get("q", "").strip()
        if recherche:
            qs = qs.filter(
                Q(code__icontains=recherche)
                | Q(collection_point__name__icontains=recherche)
                | Q(waste_type__name__icontains=recherche)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["zones"] = Zone.objects.all()
        context["statuts"] = Container.Status.choices
        context["zone_active"] = self.request.GET.get("zone", "")
        context["statut_actif"] = self.request.GET.get("statut", "")
        context["recherche"] = self.request.GET.get("q", "")
        return context


# ===========================================================================
# 4. Exécution de collecte
# ===========================================================================

class MarkStopCollectedView(CollecteAccessMixin, View):
    """Valide la collecte d'un arrêt, consigne le poids et réinitialise le conteneur."""

    def post(self, request, pk, *args, **kwargs):
        stop = get_object_or_404(
            RouteStop.objects.select_related("route", "container"),
            pk=pk,
        )

        collected_kg_raw = request.POST.get("collected_kg", "").strip()
        collected_kg = None
        if collected_kg_raw:
            try:
                collected_kg = float(collected_kg_raw)
            except ValueError:
                pass

        notes = request.POST.get("notes", "").strip()

        mark_stop_collected(stop, collected_kg=collected_kg, notes=notes)
        messages.success(
            request,
            f"Arrêt #{stop.order} (conteneur {stop.container.code}) collecté avec succès. "
            "Le conteneur a été réinitialisé à 0%.",
        )
        return redirect("collecte:route_detail", pk=stop.route.pk)
