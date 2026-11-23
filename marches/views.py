from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommercantForm, EmplacementForm
from .models import Commercant, Emplacement


@login_required
def liste_emplacements(request):
    emplacements = Emplacement.objects.all()

    numero = request.GET.get('numero', '').strip()
    zone = request.GET.get('zone', '').strip()
    activite = request.GET.get('activite', '').strip()
    statut = request.GET.get('statut', '').strip()

    if numero:
        emplacements = emplacements.filter(numero__icontains=numero)
    if zone:
        emplacements = emplacements.filter(zone=zone)
    if activite:
        emplacements = emplacements.filter(activite__icontains=activite)
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
        'numero_recherche': numero,
        'zone_choisie': zone,
        'activite_recherche': activite,
        'statut_choisi': statut,
        'statuts': Emplacement.Statut.choices,
    })


@login_required
def detail_emplacement(request, pk):
    emplacement = get_object_or_404(Emplacement, pk=pk)
    permis_lies = emplacement.permis.select_related('commercant').all()

    return render(request, 'marches/detail_emplacement.html', {
        'emplacement': emplacement,
        'permis_lies': permis_lies,
    })


@login_required
def ajouter_emplacement(request):
    if request.method == 'POST':
        form = EmplacementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "L'emplacement a bien été ajouté.")
            return redirect('marches:list')
    else:
        form = EmplacementForm()

    return render(
        request,
        'marches/ajouter_emplacement.html',
        {'form': form},
    )


@login_required
def modifier_emplacement(request, pk):
    emplacement = get_object_or_404(Emplacement, pk=pk)
    if request.method == 'POST':
        form = EmplacementForm(request.POST, instance=emplacement)
        if form.is_valid():
            form.save()
            messages.success(request, "L'emplacement a bien été modifié.")
            return redirect('marches:detail_emplacement', pk=emplacement.pk)
    else:
        form = EmplacementForm(instance=emplacement)

    return render(
        request,
        'marches/modifier_emplacement.html',
        {'form': form, 'emplacement': emplacement},
    )


@login_required
def supprimer_emplacement(request, pk):
    emplacement = get_object_or_404(Emplacement, pk=pk)
    if request.method == 'POST':
        try:
            emplacement.delete()
            messages.success(request, "L'emplacement a bien été supprimé.")
            return redirect('marches:list')
        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer cet emplacement car des permis y sont rattachés.",
            )
            return redirect('marches:detail_emplacement', pk=emplacement.pk)

    return render(
        request,
        'marches/supprimer_emplacement.html',
        {'emplacement': emplacement},
    )


@login_required
def liste_demandes_permis(request):
    return render(request, 'marches/liste_demandes_permis.html', {})

@login_required
def liste_commercants(request):
    commercants = Commercant.objects.all()

    recherche = request.GET.get('q', '').strip()
    activite = request.GET.get('activite', '').strip()
    statut = request.GET.get('statut', '').strip()

    if recherche:
        commercants = commercants.filter(
            Q(nom__icontains=recherche)
            | Q(prenom__icontains=recherche)
            | Q(cin__icontains=recherche)
            | Q(telephone__icontains=recherche)
        )
    if activite:
        commercants = commercants.filter(activite__iexact=activite)
    if statut == 'actif':
        commercants = commercants.filter(actif=True)
    elif statut == 'inactif':
        commercants = commercants.filter(actif=False)

    activites = (
        Commercant.objects.order_by('activite')
        .values_list('activite', flat=True)
        .distinct()
    )

    return render(request, 'marches/liste_commercants.html', {
        'commercants': commercants,
        'activites': activites,
        'recherche': recherche,
        'activite_selectionnee': activite,
        'statut_selectionne': statut,
    })


@login_required
def detail_commercant(request, pk):
    commercant = get_object_or_404(Commercant, pk=pk)
    permis_lies = commercant.permis.select_related('emplacement').all()
    demandes_liees = commercant.demandes_permis.all()

    return render(request, 'marches/detail_commercant.html', {
        'commercant': commercant,
        'permis_lies': permis_lies,
        'demandes_liees': demandes_liees,
    })


@login_required
def ajouter_commercant(request):
    if request.method == 'POST':
        form = CommercantForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Le commerçant a bien été ajouté.")
            return redirect('marches:liste_commercants')
    else:
        form = CommercantForm()

    return render(
        request,
        'marches/ajouter_commercant.html',
        {'form': form},
    )


@login_required
def modifier_commercant(request, pk):
    commercant = get_object_or_404(Commercant, pk=pk)
    if request.method == 'POST':
        form = CommercantForm(request.POST, instance=commercant)
        if form.is_valid():
            form.save()
            messages.success(request, "Le commerçant a bien été modifié.")
            return redirect('marches:detail_commercant', pk=commercant.pk)
    else:
        form = CommercantForm(instance=commercant)

    return render(
        request,
        'marches/modifier_commercant.html',
        {'form': form, 'commercant': commercant},
    )


@login_required
def supprimer_commercant(request, pk):
    commercant = get_object_or_404(Commercant, pk=pk)
    if request.method == 'POST':
        try:
            commercant.delete()
            messages.success(request, "Le commerçant a bien été supprimé.")
            return redirect('marches:liste_commercants')
        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer ce commerçant car des permis y sont rattachés.",
            )
            return redirect('marches:detail_commercant', pk=commercant.pk)

    return render(
        request,
        'marches/supprimer_commercant.html',
        {'commercant': commercant},
    )