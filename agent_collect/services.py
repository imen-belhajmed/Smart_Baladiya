from django.db import transaction
from django.utils import timezone

from .models import RouteStop


@transaction.atomic
def mark_stop_collected(
    stop: RouteStop,
    collected_kg: float | None = None,
    notes: str = "",
) -> RouteStop:
    """
    Marque un arrêt comme collecté, consigne le poids collecté,
    puis réinitialise le conteneur associé (fill_level=0, status='ok', last_emptied_at=now).
    """
    now = timezone.now()
    stop.collected_at = now
    if collected_kg is not None:
        stop.collected_kg = collected_kg
    if notes:
        stop.notes = notes
    stop.save()

    container = stop.container
    container.last_emptied_at = now
    container.fill_level = 0
    container.status = container.Status.OK
    container.save()

    return stop
