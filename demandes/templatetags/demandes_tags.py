from django import template

register = template.Library()

COULEURS = {
    'en_attente': 'warning text-dark',
    'en_cours': 'info text-dark',
    'validee': 'success',
    'rejetee': 'danger',
    'annulee': 'secondary',
}


@register.simple_tag(takes_context=True)
def nb_notifs(context):
    """Nombre de notifications non lues de l'utilisateur connecté."""
    request = context.get('request')
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return user.notifications_demandes.filter(lue=False).count()
    return 0


@register.filter
def couleur_statut(statut):
    """Couleur Bootstrap associée à un statut de demande."""
    return COULEURS.get(statut, 'secondary')
