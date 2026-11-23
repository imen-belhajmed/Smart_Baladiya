from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AccepterDemandeForm,
    CommercantForm,
    DemandePermisForm,
    EmplacementForm,
    PermisForm,
    RefuserDemandeForm,
)
from .models import Commercant, DemandePermis, Emplacement, Notification, Permis


def agent_requis(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not getattr(request.user, 'est_agent', False):
            messages.error(
                request,
                "Action réservée aux agents municipaux ou administrateurs.",
            )
            return redirect('marches:list')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ==========================================
# EMPLACEMENTS (Consultation : Tous | Gestion : Agent/Admin)
# ==========================================

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


@agent_requis
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


@agent_requis
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


@agent_requis
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


# ==========================================
# COMMERCANTS (Réservé aux Agents/Admins)
# ==========================================

@agent_requis
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


@agent_requis
def detail_commercant(request, pk):
    commercant = get_object_or_404(Commercant, pk=pk)
    permis_lies = commercant.permis.select_related('emplacement').all()
    demandes_liees = commercant.demandes_permis.all()

    return render(request, 'marches/detail_commercant.html', {
        'commercant': commercant,
        'permis_lies': permis_lies,
        'demandes_liees': demandes_liees,
    })


@agent_requis
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


@agent_requis
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


@agent_requis
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


# ==========================================
# BLOC 4 : ESPACE CITOYEN (Demandes & Mes Permis)
# ==========================================

@login_required
def soumettre_demande_permis(request):
    zone_init = request.GET.get('zone', '').strip()
    activite_init = request.GET.get('activite', '').strip()

    if request.method == 'POST':
        form = DemandePermisForm(request.POST, user=request.user)
        if form.is_valid():
            profil, _ = Commercant.objects.update_or_create(
                utilisateur=request.user,
                defaults={
                    'nom': form.cleaned_data['nom'],
                    'prenom': form.cleaned_data['prenom'],
                    'cin': form.cleaned_data['cin'],
                    'telephone': form.cleaned_data['telephone'],
                    'activite': form.cleaned_data['activite'],
                },
            )
            demande = form.save(commit=False)
            demande.commercant = profil
            demande.save()
            messages.success(
                request,
                "Votre demande de permis a bien été soumise. Un agent municipal la traitera prochainement.",
            )
            return redirect('marches:mes_demandes')
    else:
        initial = {}
        if zone_init:
            initial['zone_souhaitee'] = zone_init
        if activite_init:
            initial['activite'] = activite_init
        form = DemandePermisForm(user=request.user, initial=initial)

    return render(request, 'marches/soumettre_demande.html', {'form': form})


@login_required
def mes_demandes_permis(request):
    profil = getattr(request.user, 'profil_commercant', None)
    demandes = profil.demandes_permis.all() if profil else DemandePermis.objects.none()
    mes_permis = (
        profil.permis.select_related('emplacement').all()
        if profil
        else Permis.objects.none()
    )
    notifications = request.user.notifications_marches.all()[:10]
    request.user.notifications_marches.filter(lue=False).update(lue=True)

    return render(request, 'marches/mes_demandes.html', {
        'profil': profil,
        'demandes': demandes,
        'mes_permis': mes_permis,
        'notifications': notifications,
    })


# ==========================================
# BLOC 4 : ESPACE AGENT / ADMIN (Gestion Demandes & Permis)
# ==========================================

@agent_requis
def liste_demandes_permis(request):
    statut = request.GET.get('statut', '').strip()
    demandes = DemandePermis.objects.select_related('commercant').all()
    if statut in dict(DemandePermis.Statut.choices):
        demandes = demandes.filter(statut=statut)

    return render(request, 'marches/liste_demandes_permis.html', {
        'demandes': demandes,
        'statut_choisi': statut,
        'statuts': DemandePermis.Statut.choices,
    })


@agent_requis
def accepter_demande_permis(request, pk):
    demande = get_object_or_404(DemandePermis, pk=pk)
    if demande.statut != DemandePermis.Statut.EN_ATTENTE:
        messages.warning(request, "Cette demande a déjà été traitée.")
        return redirect('marches:liste_demandes_permis')

    date_fin_estimee = demande.date_debut_souhaitee + timedelta(days=demande.duree_jours)

    if request.method == 'POST':
        form = AccepterDemandeForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                permis = form.save(commit=False)
                permis.commercant = demande.commercant
                permis.statut = Permis.Statut.ACTIF
                permis.cree_par = request.user
                permis.full_clean()
                permis.save()

                emplacement = permis.emplacement
                emplacement.statut = Emplacement.Statut.RESERVE
                emplacement.save(update_fields=['statut'])

                demande.statut = DemandePermis.Statut.ACCEPTEE
                demande.save(update_fields=['statut'])

                if demande.commercant.utilisateur:
                    Notification.objects.create(
                        destinataire=demande.commercant.utilisateur,
                        permis=permis,
                        message=(
                            f"Votre demande a été acceptée ! Étal attribué : "
                            f"{emplacement} (du {permis.date_debut} au {permis.date_fin})."
                        ),
                    )

            messages.success(
                request,
                f"Demande acceptée et permis généré pour {demande.commercant}.",
            )
            return redirect('marches:detail_permis', pk=permis.pk)
    else:
        form = AccepterDemandeForm(initial={
            'date_debut': demande.date_debut_souhaitee,
            'date_fin': date_fin_estimee,
        })

    return render(request, 'marches/accepter_demande.html', {
        'demande': demande,
        'form': form,
    })


@agent_requis
def refuser_demande_permis(request, pk):
    demande = get_object_or_404(DemandePermis, pk=pk)
    if demande.statut != DemandePermis.Statut.EN_ATTENTE:
        messages.warning(request, "Cette demande a déjà été traitée.")
        return redirect('marches:liste_demandes_permis')

    if request.method == 'POST':
        form = RefuserDemandeForm(request.POST)
        if form.is_valid():
            motif = form.cleaned_data['motif_refus']
            demande.statut = DemandePermis.Statut.REFUSEE
            demande.motif_refus = motif
            demande.save(update_fields=['statut', 'motif_refus'])

            if demande.commercant.utilisateur:
                Notification.objects.create(
                    destinataire=demande.commercant.utilisateur,
                    message=f"Votre demande de permis ({demande.zone_souhaitee}) a été refusée : {motif}",
                )

            messages.info(request, "La demande a été refusée et le citoyen notifié.")
            return redirect('marches:liste_demandes_permis')
    else:
        form = RefuserDemandeForm()

    return render(request, 'marches/refuser_demande.html', {
        'demande': demande,
        'form': form,
    })


@agent_requis
def liste_permis(request):
    statut = request.GET.get('statut', '').strip()
    permis_list = Permis.objects.select_related('commercant', 'emplacement').all()
    if statut in dict(Permis.Statut.choices):
        permis_list = permis_list.filter(statut=statut)

    return render(request, 'marches/liste_permis.html', {
        'permis_list': permis_list,
        'statut_choisi': statut,
        'statuts': Permis.Statut.choices,
    })


@agent_requis
def creer_permis(request):
    if request.method == 'POST':
        form = PermisForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                permis = form.save(commit=False)
                permis.cree_par = request.user
                permis.save()

                if permis.statut in (Permis.Statut.ACTIF, Permis.Statut.SUSPENDU):
                    permis.emplacement.statut = Emplacement.Statut.RESERVE
                    permis.emplacement.save(update_fields=['statut'])

                if permis.commercant.utilisateur:
                    Notification.objects.create(
                        destinataire=permis.commercant.utilisateur,
                        permis=permis,
                        message=(
                            f"Un permis vous a été attribué pour {permis.emplacement} "
                            f"(du {permis.date_debut} au {permis.date_fin})."
                        ),
                    )

            messages.success(request, "Le permis a bien été créé.")
            return redirect('marches:detail_permis', pk=permis.pk)
    else:
        form = PermisForm()

    return render(request, 'marches/creer_permis.html', {'form': form})


@login_required
def detail_permis(request, pk):
    permis = get_object_or_404(
        Permis.objects.select_related('commercant', 'emplacement', 'cree_par'),
        pk=pk,
    )
    est_proprietaire = (
        permis.commercant.utilisateur_id is not None
        and permis.commercant.utilisateur_id == request.user.id
    )
    if not getattr(request.user, 'est_agent', False) and not est_proprietaire:
        messages.error(request, "Vous n'avez pas accès à ce permis.")
        return redirect('marches:mes_demandes')

    return render(request, 'marches/detail_permis.html', {'permis': permis})


@agent_requis
def changer_statut_permis(request, pk, nouveau_statut):
    permis = get_object_or_404(Permis, pk=pk)
    statuts_autorises = {
        Permis.Statut.ACTIF,
        Permis.Statut.SUSPENDU,
        Permis.Statut.ANNULE,
    }
    if request.method == 'POST' and nouveau_statut in statuts_autorises:
        with transaction.atomic():
            permis.statut = nouveau_statut
            permis.save(update_fields=['statut'])

            # Libérer l'emplacement si le permis est annulé et qu'aucun autre permis actif/suspendu n'existe
            if nouveau_statut == Permis.Statut.ANNULE:
                autres_actifs = Permis.objects.filter(
                    emplacement=permis.emplacement,
                    statut__in=[Permis.Statut.ACTIF, Permis.Statut.SUSPENDU],
                ).exclude(pk=permis.pk).exists()
                if not autres_actifs:
                    permis.emplacement.statut = Emplacement.Statut.LIBRE
                    permis.emplacement.save(update_fields=['statut'])
            else:
                permis.emplacement.statut = Emplacement.Statut.RESERVE
                permis.emplacement.save(update_fields=['statut'])

            if permis.commercant.utilisateur:
                Notification.objects.create(
                    destinataire=permis.commercant.utilisateur,
                    permis=permis,
                    message=f"Le statut de votre permis ({permis.emplacement}) est désormais : {permis.get_statut_display()}.",
                )

        messages.success(
            request,
            f"Statut du permis mis à jour : {permis.get_statut_display()}.",
        )
    return redirect('marches:detail_permis', pk=permis.pk)