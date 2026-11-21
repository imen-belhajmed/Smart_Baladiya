from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
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
    Vue publique listant les annonces et alertes officielles.
    """
    alertes = Alerte.objects.all().order_by('-date_publication')
    urgence_filtre = request.GET.get('urgence')
    if urgence_filtre:
        alertes = alertes.filter(niveau_urgence=urgence_filtre)

    return render(request, 'actualities/liste_alertes.html', {
        'alertes': alertes,
        'urgence_active': urgence_filtre,
        'urgences': Alerte.Urgence.choices,
    })


def detail_alerte(request, pk):
    """
    Vue détaillée d'une alerte avec affichage complet et téléchargement des pièces jointes.
    """
    alerte = get_object_or_404(Alerte, pk=pk)
    return render(request, 'actualities/detail_alerte.html', {
        'alerte': alerte,
    })
