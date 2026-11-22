from django.core.management.base import BaseCommand

from demandes.services import notifier_retards


class Command(BaseCommand):
    help = "Notifie les demandes dont le délai estimé est dépassé"

    def handle(self, *args, **options):
        self.stdout.write(f"{notifier_retards()} demande(s) en retard notifiée(s).")
