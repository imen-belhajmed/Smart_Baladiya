from django.utils import timezone
from .models import Alerte


def alerte_urgente_contexte(request):
    """
    Fournit l'alerte urgente active au template global base.html
    pour afficher le bandeau d'alerte officielle urgente sur toutes les pages.
    """
    try:
        # Met à jour les alertes échues
        Alerte.objects.filter(est_active=True, date_expiration__lte=timezone.now()).update(est_active=False)

        alerte_urgente = Alerte.objects.filter(
            est_active=True,
            niveau_urgence__in=[Alerte.Urgence.CRITIQUE, Alerte.Urgence.ELEVEE],
            date_expiration__gt=timezone.now()
        ).order_by('-niveau_urgence', '-date_publication').first()
    except Exception:
        alerte_urgente = None

    return {
        'alerte_urgente_bandeau': alerte_urgente,
    }

