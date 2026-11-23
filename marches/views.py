from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Emplacement


@login_required
def liste_emplacements(request):
    emplacements = Emplacement.objects.all()

    zone = request.GET.get('zone', '').strip()
    statut = request.GET.get('statut', '').strip()

    if zone:
        emplacements = emplacements.filter(zone=zone)
    if statut in (Emplacement.Statut.LIBRE, Emplacement.Statut.RESERVE):
        emplacements = emplacements.filter(statut=statut)

    zones = (
        Emplacement.objects.order_by('zone')
        .values_list('zone', flat=True)
        .distinct()
    )

    return render(request, 'marches/liste_emplacements.html', {
        'emplacements': emplacements,
        'zones': zones,
        'zone_choisie': zone,
        'statut_choisi': statut,
        'statuts': Emplacement.Statut.choices,
    })