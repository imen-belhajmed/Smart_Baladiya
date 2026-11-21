def notifications_demandes(request):
    """Nombre de notifications non lues, affiché dans la barre de navigation."""
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return {'nb_notifs_demandes': user.notifications_demandes.filter(lue=False).count()}
    return {}
