from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import AlerteForm
from .models import Alerte


@staff_member_required(login_url='accounts:login')
def creer_alerte(request):
    """
    Vue réservée aux agents municipaux et administrateurs
    permettant de créer et publier une annonce ou alerte officielle.
    """
    if not (request.user.is_superuser or getattr(request.user, 'est_agent', False)):
        messages.error(request, "Accès refusé : la publication d'alertes est strictement réservée aux agents municipaux.")
        return redirect('actualites:list')

    if request.method == 'POST':
        form = AlerteForm(request.POST, request.FILES)
        if form.is_valid():
            alerte = form.save(commit=False)
            alerte.auteur = request.user
            alerte.save()
            messages.success(request, f"L'alerte officielle « {alerte.titre} » a été publiée avec succès.")
            return redirect('actualites:detail_alerte', pk=alerte.pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous avant de publier l'alerte.")
    else:
        form = AlerteForm()

    return render(request, 'actualities/creer_alerte.html', {
        'form': form,
    })


def liste_alertes(request):
    """
    Vue publique du fil d'actualités et des alertes officielles.
    Filtre par défaut les alertes actives et récentes avec filter(est_active=True).
    Propose aussi une recherche par mot-clé, un filtrage par niveau d'urgence,
    et une consultation des échéances / calendrier des événements municipaux.
    """
    # Synchronisation des alertes dont la date d'expiration est dépassée
    maintenant = timezone.now()
    Alerte.objects.filter(est_active=True, date_expiration__lte=maintenant).update(est_active=False)

    # Paramètres de filtre
    statut = request.GET.get('statut', 'actives')
    urgence_filtre = request.GET.get('urgence', '').strip()
    recherche = request.GET.get('q', '').strip()

    # QuerySet principal filtrant les alertes actives et récentes
    if statut == 'archives':
        alertes = Alerte.objects.filter(est_active=False)
    elif statut == 'toutes':
        alertes = Alerte.objects.all()
    else:
        # Par défaut : alertes actives
        alertes = Alerte.objects.filter(est_active=True)

    # Filtrage par mot-clé
    if recherche:
        alertes = alertes.filter(
            Q(titre__icontains=recherche) | Q(contenu__icontains=recherche)
        )

    # Filtrage par niveau d'urgence
    if urgence_filtre and urgence_filtre in dict(Alerte.Urgence.choices):
        alertes = alertes.filter(niveau_urgence=urgence_filtre)

    alertes = alertes.order_by('-date_publication')

    # Alerte urgente vedette active (pour bandeau d'alerte urgente en haut de page)
    alerte_urgente_vedette = Alerte.objects.filter(
        est_active=True,
        niveau_urgence__in=[Alerte.Urgence.CRITIQUE, Alerte.Urgence.ELEVEE],
        date_expiration__gt=maintenant
    ).order_by('-niveau_urgence', '-date_publication').first()

    # Prochaines échéances / calendrier des événements municipaux
    prochaines_echeances = Alerte.objects.filter(
        est_active=True,
        date_expiration__gt=maintenant
    ).order_by('date_expiration')[:5]

    return render(request, 'actualities/liste_alertes.html', {
        'alertes': alertes,
        'alerte_urgente_vedette': alerte_urgente_vedette,
        'prochaines_echeances': prochaines_echeances,
        'urgence_active': urgence_filtre,
        'statut_actif': statut,
        'recherche': recherche,
        'urgences': Alerte.Urgence.choices,
        'total_actives': Alerte.objects.filter(est_active=True).count(),
        'total_archives': Alerte.objects.filter(est_active=False).count(),
    })


def detail_alerte(request, pk):
    """
    Vue publique de détail d'une alerte ou annonce municipale.
    Affiche le texte intégral, les dates de validité, l'auteur
    et offre le téléchargement direct de la pièce jointe.
    """
    alerte = get_object_or_404(Alerte, pk=pk)
    return render(request, 'actualities/detail_alerte.html', {
        'alerte': alerte,
    })


@login_required(login_url='accounts:login')
def modifier_alerte(request, pk):
    """
    Vue réservée aux agents municipaux et administrateurs
    permettant de modifier le contenu d'un communiqué ou d'une alerte.
    L'enregistrement actualise automatiquement l'horodatage de révision (date_mise_a_jour via auto_now=True).
    """
    if not (request.user.is_superuser or getattr(request.user, 'est_agent', False)):
        messages.error(request, "Accès refusé : la modification d'alertes est strictement réservée aux agents municipaux.")
        return redirect('actualites:list')

    alerte = get_object_or_404(Alerte, pk=pk)

    if request.method == 'POST':
        form = AlerteForm(request.POST, request.FILES, instance=alerte)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le communiqué officiel « {alerte.titre} » a été mis à jour avec succès.")
            return redirect('actualites:detail_alerte', pk=alerte.pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous avant d'enregistrer.")
    else:
        form = AlerteForm(instance=alerte)

    return render(request, 'actualities/modifier_alerte.html', {
        'form': form,
        'alerte': alerte,
    })
