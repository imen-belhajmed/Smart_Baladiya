from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.admin.views.decorators import staff_member_required

from .forms import IncidentForm, IncidentUpdateForm
from .models import CategorieIncident, Incident


@login_required
def ajouter_incident(request):
    if request.method == "POST":
        form = IncidentForm(request.POST, request.FILES)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.auteur = request.user
            incident.statut = Incident.Statut.SIGNALE
            incident.save()
            messages.success(request, "Votre signalement a bien été enregistré.")
            return redirect("incidents:list")
    else:
        form = IncidentForm()
    return render(request, "incidents/ajouter_incident.html", {"form": form})


@login_required
def liste_incidents(request):
    incidents = Incident.objects.filter(est_archive=False).select_related("categorie", "auteur")

    statut = request.GET.get("statut", "")
    categorie = request.GET.get("categorie", "")
    if statut in Incident.Statut.values:
        incidents = incidents.filter(statut=statut)
    if categorie.isdigit():
        incidents = incidents.filter(categorie_id=int(categorie))

    return render(request, "incidents/liste_incidents.html", {
        "incidents": incidents,
        "categories": CategorieIncident.objects.all(),
        "statuts": Incident.Statut.choices,
        "statut_actif": statut,
        "categorie_active": categorie,
    })


@login_required
def detail_incident(request, pk):
    incident = get_object_or_404(Incident, pk=pk, est_archive=False)
    return render(request, "incidents/detail_incident.html", {"incident": incident})


@staff_member_required
def modifier_incident(request, pk):
    incident = get_object_or_404(Incident, pk=pk, est_archive=False)
    if request.method == "POST":
        form = IncidentUpdateForm(request.POST, request.FILES, instance=incident)
        if form.is_valid():
            form.save()
            messages.success(request, "L'incident a été mis à jour.")
            return redirect("incidents:detail", pk=incident.pk)
    else:
        form = IncidentUpdateForm(instance=incident)
    return render(request, "incidents/modifier_incident.html", {"form": form, "incident": incident})