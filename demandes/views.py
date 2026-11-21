from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import DemandeAdministrativeForm, TraitementForm, VerificationForm
from .models import DemandeAdministrative, Notification


def agent_requis(vue):
    """Réservé aux agents municipaux et administrateurs (rôle 'agent' / 'admin')."""
    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        if not request.user.est_agent:
            raise PermissionDenied
        return vue(request, *args, **kwargs)
    return enveloppe


def _demande_visible(request, pk):
    """Une demande est visible par son propriétaire et par les agents."""
    demande = get_object_or_404(DemandeAdministrative, pk=pk)
    if demande.citoyen_id != request.user.pk and not request.user.est_agent:
        raise PermissionDenied
    return demande


# ---------------------------------------------------------------- Citoyen
@login_required
def liste_demandes(request):
    """Historique et statut des demandes de l'utilisateur connecté."""
    demandes = DemandeAdministrative.objects.filter(citoyen=request.user)
    statut = request.GET.get('statut', '')
    if statut in dict(DemandeAdministrative.STATUT_CHOICES):
        demandes = demandes.filter(statut=statut)
    return render(request, 'demandes/liste_demandes.html', {
        'demandes': demandes,
        'statut': statut,
        'statuts': DemandeAdministrative.STATUT_CHOICES,
    })


@login_required
def creer_demande(request):
    """Création d'une demande : le délai est estimé automatiquement."""
    if request.method == 'POST':
        form = DemandeAdministrativeForm(request.POST, request.FILES)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.citoyen = request.user
            demande.save()
            messages.success(
                request,
                f'Demande enregistrée ! Délai estimé : {demande.delai_estime_heures} h.',
            )
            return redirect('demandes:detail', pk=demande.pk)
    else:
        form = DemandeAdministrativeForm()
    return render(request, 'demandes/creer_demande.html', {'form': form})


@login_required
def detail_demande(request, pk):
    demande = _demande_visible(request, pk)
    return render(request, 'demandes/detail_demande.html', {'demande': demande})


@login_required
def modifier_demande(request, pk):
    """Modification possible uniquement par le propriétaire, tant que la demande est en attente."""
    demande = get_object_or_404(DemandeAdministrative, pk=pk, citoyen=request.user)
    if not demande.modifiable:
        messages.error(request, 'Impossible de modifier une demande déjà en cours ou traitée.')
        return redirect('demandes:liste')
    if request.method == 'POST':
        form = DemandeAdministrativeForm(request.POST, request.FILES, instance=demande)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre demande a été mise à jour avec succès.')
            return redirect('demandes:detail', pk=demande.pk)
    else:
        form = DemandeAdministrativeForm(instance=demande)
    return render(request, 'demandes/modifier_demande.html', {'form': form, 'demande': demande})


@login_required
@require_POST
def annuler_demande(request, pk):
    """Annulation d'une demande en attente (elle reste dans l'historique)."""
    demande = get_object_or_404(DemandeAdministrative, pk=pk, citoyen=request.user)
    if demande.modifiable:
        demande.statut = 'annulee'
        demande.save()
        messages.success(request, 'Votre demande a bien été annulée.')
    else:
        messages.error(request, 'Impossible d\'annuler une demande déjà en cours ou traitée.')
    return redirect('demandes:liste')


@login_required
def supprimer_demande(request, pk):
    """Suppression définitive : agent (toute demande) ou propriétaire (demande en attente)."""
    demande = _demande_visible(request, pk)
    if not request.user.est_agent and not demande.modifiable:
        raise PermissionDenied
    if request.method == 'POST':
        demande.delete()
        messages.success(request, 'La demande a été supprimée.')
        return redirect('demandes:tableau_agent' if request.user.est_agent else 'demandes:liste')
    return render(request, 'demandes/supprimer_demande.html', {'demande': demande})


@login_required
def telecharger_document(request, pk):
    """Téléchargement protégé du document délivré (propriétaire ou agent)."""
    demande = _demande_visible(request, pk)
    if not demande.document_delivre:
        raise Http404
    return FileResponse(demande.document_delivre.open('rb'), as_attachment=True,
                        filename=demande.document_delivre.name.rsplit('/', 1)[-1])


@login_required
def notifications(request):
    notifs = list(Notification.objects.filter(destinataire=request.user)[:50])
    Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    return render(request, 'demandes/notifications.html', {'notifs': notifs})


# ---------------------------------------------------------------- Public
def _masquer(nom):
    nom = str(nom)
    return nom[:1] + '*' * max(len(nom) - 1, 2)


def verifier_document(request):
    """Vérification publique d'authenticité : code unique + comparaison facultative de l'empreinte SHA-256."""
    resultat = None
    demande = None
    code = (request.POST.get('code') or request.GET.get('code') or '').strip()
    fichier = request.FILES.get('document')
    form = VerificationForm(initial={'code': code})
    if code:
        form = VerificationForm({'code': code})
        if form.is_valid():
            demande = DemandeAdministrative.objects.filter(
                empreinte_verification=form.cleaned_data['code']).first()
        if not demande:
            resultat = 'inconnu'
        elif fichier:
            ok = demande.statut == 'validee' and demande.empreinte_document \
                and demande.empreinte_document == services.empreinte_fichier(fichier)
            resultat = 'authentique' if ok else 'modifie'
        else:
            resultat = 'trouve'
    return render(request, 'demandes/verifier_document.html', {
        'form': form, 'code': code, 'demande': demande, 'resultat': resultat,
        'citoyen_masque': _masquer(demande.citoyen) if demande else '',
    })


# ---------------------------------------------------------------- Agent
@agent_requis
def tableau_bord_agent(request):
    """Espace de gestion des agents municipaux."""
    demandes = DemandeAdministrative.objects.select_related('citoyen')
    statut = request.GET.get('statut', '')
    q = request.GET.get('q', '').strip()
    if statut in dict(DemandeAdministrative.STATUT_CHOICES):
        demandes = demandes.filter(statut=statut)
    if q:
        demandes = demandes.filter(Q(citoyen__username__icontains=q) | Q(motif__icontains=q))
    toutes = DemandeAdministrative.objects.all()
    stats = {
        'total': toutes.count(),
        'en_attente': toutes.filter(statut='en_attente').count(),
        'en_cours': toutes.filter(statut='en_cours').count(),
        'validee': toutes.filter(statut='validee').count(),
        'rejetee': toutes.filter(statut='rejetee').count(),
    }
    return render(request, 'demandes/tableau_bord_agent.html', {
        'demandes': demandes, 'stats': stats, 'statut': statut, 'q': q,
        'statuts': DemandeAdministrative.STATUT_CHOICES,
    })


@agent_requis
def traiter_demande(request, pk):
    """L'agent change le statut, commente et joint le document délivré (empreinte SHA-256 calculée)."""
    demande = get_object_or_404(DemandeAdministrative, pk=pk)
    form = TraitementForm(request.POST or None, request.FILES or None, instance=demande)
    if request.method == 'POST' and form.is_valid():
        demande = form.save(commit=False)
        demande.agent_traitant = request.user
        if 'document_delivre' in form.changed_data and request.FILES.get('document_delivre'):
            demande.empreinte_document = services.empreinte_fichier(request.FILES['document_delivre'])
        demande.save()
        messages.success(request, f'La demande de {demande.citoyen} a été mise à jour. Le citoyen est notifié.')
        return redirect('demandes:tableau_agent')
    return render(request, 'demandes/traiter_demande.html', {'demande': demande, 'form': form})
