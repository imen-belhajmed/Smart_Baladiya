import uuid
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .forms import DemandeAdministrativeForm
from .models import DemandeAdministrative


@login_required
def liste_demandes(request):
    """Affiche la liste des demandes de l'utilisateur connecté."""
    demandes = DemandeAdministrative.objects.filter(
        citoyen=request.user
    ).order_by('-date_creation')
    return render(
        request, 'demandes/liste_demandes.html', {'demandes': demandes}
    )


@login_required
def creer_demande(request):
    """Permet au citoyen de soumettre une nouvelle demande administrative."""
    if request.method == 'POST':
        form = DemandeAdministrativeForm(request.POST, request.FILES)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.citoyen = request.user

            delais_par_type = {
                'extrait_naissance': 2,
                'legalisation': 1,
                'residence': 4,
                'autre': 24,
            }
            demande.delai_estime_heures = delais_par_type.get(
                demande.type_document, 24
            )

            demande.save()
            messages.success(
                request,
                f'Demande enregistrée ! Délai estimé : {demande.delai_estime_heures}h.',
            )
            return redirect('demandes:liste')
    else:
        form = DemandeAdministrativeForm()

    return render(request, 'demandes/creer_demande.html', {'form': form})


@login_required
def modifier_demande(request, pk):
    """Permet au citoyen de modifier sa demande tant qu'elle est en attente."""
    demande = get_object_or_404(DemandeAdministrative, pk=pk, citoyen=request.user)

    if demande.statut != 'en_attente':
        messages.error(
            request,
            'Impossible de modifier une demande déjà en cours ou traitée.',
        )
        return redirect('demandes:liste')

    if request.method == 'POST':
        form = DemandeAdministrativeForm(
            request.POST, request.FILES, instance=demande
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre demande a été mise à jour avec succès.')
            return redirect('demandes:liste')
    else:
        form = DemandeAdministrativeForm(instance=demande)

    return render(
        request,
        'demandes/modifier_demande.html',
        {'form': form, 'demande': demande},
    )


@login_required
def supprimer_demande(request, pk):
    """Permet au citoyen d'annuler/supprimer une demande encore en attente."""
    demande = get_object_or_404(DemandeAdministrative, pk=pk, citoyen=request.user)
    if request.method == 'POST':
        if demande.statut == 'en_attente':
            demande.delete()
            messages.success(request, 'Votre demande a bien été annulée et supprimée.')
        else:
            messages.error(
                request,
                'Impossible de supprimer une demande déjà en cours ou traitée.',
            )
    return redirect('demandes:liste')


def verifier_document(request):
    """Vue publique permettant de vérifier l'authenticité d'un document via son UUID."""
    code = request.GET.get('code', '').strip()
    demande = None
    erreur = None

    if code:
        try:
            uuid_obj = uuid.UUID(code)
            demande = DemandeAdministrative.objects.get(
                empreinte_verification=uuid_obj
            )
        except (ValueError, DemandeAdministrative.DoesNotExist):
            erreur = 'Aucun document valide trouvé avec cette empreinte unique.'

    return render(
        request,
        'demandes/verifier_document.html',
        {
            'demande': demande,
            'erreur': erreur,
            'code': code,
        },
    )


@staff_member_required
def tableau_bord_agent(request):
    """Espace de gestion pour l'agent municipal (réservé au staff/admin)."""
    demandes = DemandeAdministrative.objects.all().order_by('-date_creation')
    return render(
        request, 'demandes/tableau_bord_agent.html', {'demandes': demandes}
    )


@staff_member_required
def traiter_demande(request, pk):
    """Permet à l'agent de changer le statut d'une demande et d'ajouter un commentaire."""
    demande = get_object_or_404(DemandeAdministrative, pk=pk)

    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        commentaire = request.POST.get('commentaire_agent', '')

        if nouveau_statut in dict(DemandeAdministrative.STATUT_CHOICES):
            demande.statut = nouveau_statut
            demande.commentaire_agent = commentaire
            demande.save()
            messages.success(
                request,
                f'La demande de {demande.citoyen} a été mise à jour avec succès.',
            )
        else:
            messages.error(request, 'Statut invalide.')

        return redirect('demandes:tableau_agent')

    return render(request, 'demandes/traiter_demande.html', {'demande': demande})