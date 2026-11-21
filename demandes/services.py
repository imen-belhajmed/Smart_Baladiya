"""Logique métier du module Demandes : estimation des délais, empreinte, notifications."""
import hashlib
import math

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

# Délais de base par type de document (en heures)
DELAIS_BASE_HEURES = {
    'extrait_naissance': 2,
    'legalisation': 1,
    'residence': 4,
    'autre': 24,
}


def estimer_delai_heures(type_document):
    """Estimation intelligente du délai de traitement (en heures).

    1. délai de base selon le type de document ;
    2. affiné par la durée moyenne réelle des demandes déjà validées (si >= 3) ;
    3. majoré selon la charge actuelle (+1 h par tranche de 5 demandes en attente).
    """
    from .models import DemandeAdministrative as D

    base = DELAIS_BASE_HEURES.get(type_document, 24)
    validees = D.objects.filter(type_document=type_document, statut='validee').order_by('-date_mise_a_jour')[:50]
    durees = [
        max(1, math.ceil((d.date_mise_a_jour - d.date_creation).total_seconds() / 3600))
        for d in validees
    ]
    if len(durees) >= 3:
        base = round(0.5 * base + 0.5 * sum(durees) / len(durees))
    charge = D.objects.filter(statut__in=['en_attente', 'en_cours']).count()
    return max(1, base + charge // 5)


def empreinte_fichier(fichier):
    """Empreinte SHA-256 d'un fichier (UploadedFile ou FieldFile)."""
    h = hashlib.sha256()
    fichier.seek(0)
    for bloc in iter(lambda: fichier.read(8192), b''):
        h.update(bloc)
    fichier.seek(0)
    return h.hexdigest()


def agents():
    User = get_user_model()
    return User.objects.filter(Q(role__in=['agent', 'admin']) | Q(is_superuser=True)).distinct()


def notifier(utilisateur, message, lien=''):
    from .models import Notification
    Notification.objects.create(destinataire=utilisateur, message=message[:255], lien=lien)


def notifier_creation(d):
    lien = reverse('demandes:detail', args=[d.pk])
    notifier(d.citoyen,
             f"Demande « {d.get_type_document_display()} » enregistrée. Délai estimé : "
             f"{d.delai_estime_heures} h (avant le {timezone.localtime(d.date_prevue):%d/%m/%Y %H:%M}).", lien)
    for a in agents():
        if a.pk != d.citoyen_id:
            notifier(a, f"Nouvelle demande à traiter : {d.get_type_document_display()} ({d.citoyen})", lien)


def notifier_changement_statut(d):
    notifier(d.citoyen,
             f"Votre demande « {d.get_type_document_display()} » est maintenant : {d.get_statut_display()}.",
             reverse('demandes:detail', args=[d.pk]))


def notifier_retards():
    """Prévient le citoyen et les agents quand le délai estimé est dépassé (une seule fois par demande)."""
    from .models import DemandeAdministrative as D
    liste_agents = list(agents())
    n = 0
    en_retard = D.objects.filter(statut__in=['en_attente', 'en_cours'], retard_notifie=False,
                                 date_prevue__lt=timezone.now())
    for d in en_retard:
        lien = reverse('demandes:detail', args=[d.pk])
        notifier(d.citoyen, f"Retard : votre demande « {d.get_type_document_display()} » dépasse le délai estimé.", lien)
        for a in liste_agents:
            notifier(a, f"Demande en retard : {d.get_type_document_display()} ({d.citoyen})", lien)
        D.objects.filter(pk=d.pk).update(retard_notifie=True)
        n += 1
    return n
