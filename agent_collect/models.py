from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base: adds created_at / updated_at to every model."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Places
# ---------------------------------------------------------------------------

class Zone(TimeStampedModel):
    """A neighborhood / sector used to group collection points and routes."""
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=120)

    class Meta:
        ordering = ["city", "name"]
        constraints = [
            models.UniqueConstraint(fields=["city", "name"], name="unique_zone_per_city"),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"


class WasteType(TimeStampedModel):
    """Plastic, paper, glass, organic, hazardous, ..."""
    name = models.CharField(max_length=60, unique=True)
    is_hazardous = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CollectionPoint(TimeStampedModel):
    """A physical place where containers are installed (street corner, square...)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        MAINTENANCE = "maintenance", "Under maintenance"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=150)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="collection_points")
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        ordering = ["zone", "name"]
        indexes = [models.Index(fields=["zone", "status"])]

    def __str__(self):
        return f"{self.name} - {self.zone}"


class Container(TimeStampedModel):
    """A bin at a collection point, dedicated to one waste type."""

    class Status(models.TextChoices):
        OK = "ok", "Operational"
        FULL = "full", "Full"
        DAMAGED = "damaged", "Damaged"
        OUT_OF_SERVICE = "out_of_service", "Out of service"

    code = models.CharField(max_length=40, unique=True, help_text="Unique label / QR code value")
    collection_point = models.ForeignKey(CollectionPoint, on_delete=models.CASCADE, related_name="containers")
    waste_type = models.ForeignKey(WasteType, on_delete=models.PROTECT, related_name="containers")
    capacity_liters = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    fill_level = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100)], help_text="Latest known fill level, in %",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OK, db_index=True)
    last_emptied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["collection_point", "code"]
        indexes = [models.Index(fields=["status", "fill_level"])]

    def __str__(self):
        return f"{self.code} ({self.waste_type})"


class FillLevelEstimate(TimeStampedModel):
    """History of fill-level readings, from a photo analysed by AI or a manual check."""

    class Source(models.TextChoices):
        AI_PHOTO = "ai_photo", "AI photo analysis"
        AGENT = "agent", "Agent inspection"
        CITIZEN = "citizen", "Citizen report"

    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="fill_estimates")
    fill_level = models.PositiveSmallIntegerField(validators=[MaxValueValidator(100)])
    confidence = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Model confidence (0-1), only for AI estimates",
    )
    source = models.CharField(max_length=15, choices=Source.choices)
    photo = models.ImageField(upload_to="fill_estimates/%Y/%m/", null=True, blank=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="fill_estimates",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["container", "-created_at"])]

    def __str__(self):
        return f"{self.container.code}: {self.fill_level}% ({self.get_source_display()})"


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class Citizen(TimeStampedModel):
    """Profile of a registered person who throws trash. Linked to the auth user."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="citizen_profile")
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.SET_NULL, related_name="citizens")

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return self.user.get_full_name() or self.user.get_username()


class CollectionAgent(TimeStampedModel):
    """Municipal staff member who drives or works on collection routes."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_profile")
    employee_id = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name() or self.user.get_username()}"


class WasteDeposit(TimeStampedModel):
    """Records that a citizen threw trash into a container."""
    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE, related_name="deposits")
    container = models.ForeignKey(Container, on_delete=models.PROTECT, related_name="deposits")
    waste_type = models.ForeignKey(WasteType, on_delete=models.PROTECT, related_name="deposits")
    quantity_kg = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)],
    )
    deposited_at = models.DateTimeField(default=timezone.now, db_index=True)
    photo = models.ImageField(upload_to="deposits/%Y/%m/", null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-deposited_at"]
        indexes = [
            models.Index(fields=["citizen", "-deposited_at"]),
            models.Index(fields=["container", "-deposited_at"]),
        ]

    def __str__(self):
        return f"{self.citizen} -> {self.container.code} on {self.deposited_at:%Y-%m-%d}"


# ---------------------------------------------------------------------------
# Collection resources and routes
# ---------------------------------------------------------------------------

class Vehicle(TimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ON_ROUTE = "on_route", "On route"
        MAINTENANCE = "maintenance", "Under maintenance"
        RETIRED = "retired", "Retired"

    plate_number = models.CharField(max_length=20, unique=True)
    capacity_kg = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE, db_index=True)

    class Meta:
        ordering = ["plate_number"]

    def __str__(self):
        return self.plate_number


class CollectionTeam(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(CollectionAgent, related_name="teams", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CollectionRoute(TimeStampedModel):
    """A 'tournée': a planned run of a team and vehicle over a set of containers."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=120)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="routes")
    team = models.ForeignKey(CollectionTeam, null=True, blank=True, on_delete=models.SET_NULL, related_name="routes")
    vehicle = models.ForeignKey(Vehicle, null=True, blank=True, on_delete=models.SET_NULL, related_name="routes")
    scheduled_date = models.DateField(db_index=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PLANNED, db_index=True)
    containers = models.ManyToManyField(Container, through="RouteStop", related_name="routes")

    class Meta:
        ordering = ["-scheduled_date", "name"]
        indexes = [models.Index(fields=["zone", "scheduled_date", "status"])]

    def __str__(self):
        return f"{self.name} - {self.scheduled_date}"


class RouteStop(TimeStampedModel):
    """One container to empty during a route, with its order and urgency."""

    class Urgency(models.IntegerChoices):
        LOW = 1, "Low"
        NORMAL = 2, "Normal"
        HIGH = 3, "High"
        CRITICAL = 4, "Critical"

    route = models.ForeignKey(CollectionRoute, on_delete=models.CASCADE, related_name="stops")
    container = models.ForeignKey(Container, on_delete=models.PROTECT, related_name="route_stops")
    order = models.PositiveSmallIntegerField(help_text="Visit order within the route")
    urgency = models.PositiveSmallIntegerField(choices=Urgency.choices, default=Urgency.NORMAL)
    collected_at = models.DateTimeField(null=True, blank=True)
    collected_kg = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)],
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["route", "order"]
        constraints = [
            models.UniqueConstraint(fields=["route", "order"], name="unique_stop_order_per_route"),
            models.UniqueConstraint(fields=["route", "container"], name="unique_container_per_route"),
        ]

    def __str__(self):
        return f"{self.route} #{self.order}: {self.container.code}"