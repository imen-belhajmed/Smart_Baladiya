from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse

from .forms import IncidentForm
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
            return redirect("admin:index")
    else:
        form = IncidentForm()
    return render(request, "incidents/ajouter_incident.html", {"form": form})

def liste_incidents(request):
    return HttpResponse("Liste des incidents (à implémenter)")