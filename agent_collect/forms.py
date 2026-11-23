from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import (
    CollectionAgent,
    CollectionRoute,
    CollectionTeam,
    Container,
    RouteStop,
    Vehicle,
    Zone,
)


class VehicleForm(forms.ModelForm):
    """Formulaire de création et mise à jour d'un véhicule de collecte."""

    class Meta:
        model = Vehicle
        fields = ["plate_number", "capacity_kg", "status"]
        labels = {
            "plate_number": "Numéro d'immatriculation",
            "capacity_kg": "Capacité maximale (kg)",
            "status": "Statut du véhicule",
        }
        widgets = {
            "plate_number": forms.TextInput(attrs={"placeholder": "Ex: 123-TN-456"}),
            "capacity_kg": forms.NumberInput(attrs={"min": 1, "step": 50}),
        }


class CollectionRouteForm(forms.ModelForm):
    """Formulaire d'enregistrement et de modification d'une tournée de collecte."""

    class Meta:
        model = CollectionRoute
        fields = ["name", "zone", "team", "vehicle", "scheduled_date", "status"]
        labels = {
            "name": "Nom de la tournée",
            "zone": "Zone géographique",
            "team": "Équipe affectée",
            "vehicle": "Véhicule assigné",
            "scheduled_date": "Date d'intervention",
            "status": "Statut de la tournée",
        }
        widgets = {
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
            "name": forms.TextInput(attrs={"placeholder": "Ex: Tournée Centre-Ville Matin"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available_qs = Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE)
        if self.instance and self.instance.pk and self.instance.vehicle:
            self.fields["vehicle"].queryset = (
                available_qs | Vehicle.objects.filter(pk=self.instance.vehicle.pk)
            ).distinct()
        else:
            self.fields["vehicle"].queryset = available_qs

        self.fields["vehicle"].empty_label = "Sélectionner un véhicule disponible"
        self.fields["team"].empty_label = "Sélectionner une équipe"
        self.fields["zone"].empty_label = "Sélectionner une zone"

    def clean_vehicle(self):
        vehicle = self.cleaned_data.get("vehicle")
        if vehicle:
            is_same_vehicle = (
                self.instance
                and self.instance.pk
                and self.instance.vehicle_id == vehicle.pk
            )
            if not is_same_vehicle and vehicle.status != Vehicle.Status.AVAILABLE:
                raise forms.ValidationError(
                    "Seuls les véhicules avec le statut « Disponible » peuvent être affectés à une tournée."
                )
        return vehicle

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk:
            current_status = (
                CollectionRoute.objects.filter(pk=self.instance.pk)
                .values_list("status", flat=True)
                .first()
            )
            if current_status in [
                CollectionRoute.Status.COMPLETED,
                CollectionRoute.Status.CANCELLED,
            ]:
                raise forms.ValidationError(
                    "Une tournée avec le statut « Terminée » ou « Annulée » ne peut plus être modifiée."
                )
        return cleaned_data


class CollectionTeamForm(forms.ModelForm):
    """Formulaire de gestion d'une équipe de collecte et de ses membres."""

    class Meta:
        model = CollectionTeam
        fields = ["name", "members"]
        labels = {
            "name": "Nom de l'équipe",
            "members": "Agents membres",
        }
        help_texts = {
            "members": "Maintenez la touche Ctrl (ou Cmd sur Mac) enfoncée pour sélectionner plusieurs agents.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = (
            CollectionAgent.objects.filter(is_active=True)
            .select_related("user")
            .order_by("user__last_name", "user__first_name")
        )


class RouteStopForm(forms.ModelForm):
    """Formulaire pour un arrêt individuel de conteneur au sein d'une tournée."""

    class Meta:
        model = RouteStop
        fields = ["container", "order", "urgency", "notes"]
        labels = {
            "container": "Conteneur",
            "order": "Ordre",
            "urgency": "Urgence",
            "notes": "Instructions / Remarques",
        }
        widgets = {
            "order": forms.NumberInput(attrs={"min": 1, "style": "width: 90px;"}),
            "notes": forms.TextInput(attrs={"placeholder": "Remarque d'accès ou sécurité"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["container"].queryset = Container.objects.select_related(
            "collection_point__zone", "waste_type"
        ).order_by("collection_point__name", "code")

    def clean(self):
        cleaned_data = super().clean()
        container = cleaned_data.get("container")
        route = getattr(self.instance, "route", None)
        route_zone = getattr(route, "zone", None) if route else None

        # Règle : Chaque conteneur doit appartenir à la zone de la tournée
        if container and route_zone:
            container_zone = container.collection_point.zone
            if container_zone != route_zone:
                self.add_error(
                    "container",
                    f"Le conteneur {container.code} appartient à la zone « {container_zone.name} », "
                    f"incompatible avec la zone de la tournée (« {route_zone.name} »).",
                )
        return cleaned_data


class BaseRouteStopFormSet(BaseInlineFormSet):
    """Formset validant la cohérence de zone et l'unicité ordre/conteneur sans IntegrityError."""

    def clean(self):
        super().clean()

        orders_seen = {}
        containers_seen = {}

        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data or form.cleaned_data.get("DELETE", False):
                continue

            container = form.cleaned_data.get("container")
            order = form.cleaned_data.get("order")

            # Règle : Unicité de l'ordre de passage au sein de la tournée
            if order is not None:
                if order in orders_seen:
                    form.add_error(
                        "order",
                        f"L'ordre de passage #{order} est déjà attribué à un autre arrêt de cette tournée.",
                    )
                else:
                    orders_seen[order] = form

            # Règle : Unicité du conteneur dans la tournée
            if container:
                if container in containers_seen:
                    form.add_error(
                        "container",
                        f"Le conteneur {container.code} est déjà présent dans la liste des arrêts.",
                    )
                else:
                    containers_seen[container] = form


RouteStopFormSet = inlineformset_factory(
    CollectionRoute,
    RouteStop,
    form=RouteStopForm,
    formset=BaseRouteStopFormSet,
    extra=1,
    can_delete=True,
)


class RouteFilterForm(forms.Form):
    """Formulaire de filtrage pour la page de planning des tournées."""

    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Date d'intervention",
    )
    status = forms.ChoiceField(
        choices=[("", "Tous les statuts")] + list(CollectionRoute.Status.choices),
        required=False,
        label="Statut",
    )
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.all(),
        required=False,
        empty_label="Toutes les zones",
        label="Zone",
    )
