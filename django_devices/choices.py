from django.db import models
from django.utils.translation import gettext_lazy as _

class DefaultNotificationTypeChoices(models.TextChoices):
    """
    Default choices for notification types.
    Users should override this by setting NOTIFICATION_TYPE_CHOICES in settings.
    """
    UNKNOWN = "UNKNOWN", _("Unknown notification")
