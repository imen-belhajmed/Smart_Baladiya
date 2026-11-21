from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from demandes.models import DemandeAdministrative


class Command(BaseCommand):
    help = "Crée des comptes et demandes de démonstration pour tester le module Demandes"

    def handle(self, *args, **options):
        User = get_user_model()

        def compte(username, role, mdp):
            u, cree = User.objects.get_or_create(username=username, defaults={'role': role})
            if cree:
                u.set_password(mdp)
                u.save()
            return u

        compte('agent1', 'agent', 'demo1234')
        citoyen = compte('citoyen1', 'citoyen', 'demo1234')
        for t, m in [('extrait_naissance', 'Dossier scolaire'), ('legalisation', 'Contrat de location'),
                     ('residence', 'Inscription administrative')]:
            DemandeAdministrative.objects.get_or_create(citoyen=citoyen, type_document=t, motif=m)
        self.stdout.write(self.style.SUCCESS("Comptes : agent1 / citoyen1 (mot de passe : demo1234)"))
