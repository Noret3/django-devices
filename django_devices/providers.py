from django.utils.translation import gettext_lazy as _
from django_devices.push import BasePushMessageProvider, register
from django_devices.schemas.notifications.base import PushMessageSchema
from django_devices.utils import get_notification_types


class UnknownPushProvider(BasePushMessageProvider):
    """
    Provider for UNKNOWN notification type.
    """
    
    @property
    def notification_type(self):
        return get_notification_types().UNKNOWN

    def get_messages(self) -> list[PushMessageSchema]:
        return [
            PushMessageSchema(
                title=_("Unknown Notification"),
                body=_("You have a new notification."),
                image=None
            )
        ]

    def get_site_message(self) -> PushMessageSchema:
        return PushMessageSchema(
            title=_("Unknown Notification"),
            body=_("You have a new notification."),
            image=None
        )

register(UnknownPushProvider)
