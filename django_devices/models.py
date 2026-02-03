from typing import Any, Union

import firebase_admin
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError

from fcm_django.models import AbstractFCMDevice, _validate_exception_for_deactivation

from django_devices.schemas.notifications.base import NotificationPushData, NotificationResponseSchema
from django_devices.settings import device_settings
from django_devices.utils import get_notification_types


class AbstractCustomFCMDevice(AbstractFCMDevice):
    """
    Abstract base class for custom FCM devices.
    """
    registration_id = models.TextField(
        verbose_name=_("Registration token"),
        null=True,
    )
    device_id = models.CharField(
        verbose_name=_("Device ID"),
        db_index=True,
        help_text=_("Unique device identifier"),
        max_length=255,
    )

    class Meta:
        abstract = True
        verbose_name = _("FCM device")
        verbose_name_plural = _("FCM devices")
        indexes = [
            models.Index(fields=["registration_id", "user"]),
            models.Index(fields=["device_id", "user"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["registration_id"],
                condition=models.Q(registration_id__isnull=False),
                name="%(app_label)s_%(class)s_unique_real_registration_id",
            ),
            models.UniqueConstraint(
                fields=["device_id", "user"],
                name="%(app_label)s_%(class)s_unique_device_id_for_user",
            ),
        ]

    async def send_message_async(
            self,
            message: messaging.Message,
            app: firebase_admin.App | None = None,
            **more_send_message_kwargs: dict[str, Any],
    ) -> messaging.SendResponse:
        """
        Asynchronously sends a message to the device.
        """
        app = app or device_settings.DEFAULT_FIREBASE_APP

        if not self.active:
            return messaging.SendResponse(None, None)

        message.token = self.registration_id
        try:
            batch_response = await messaging.send_each_async(
                [message], app=app, **more_send_message_kwargs
            )
            response = batch_response.responses[0]
            if response.exception:
                if isinstance(response.exception, BaseException):
                    raise response.exception
                else:
                    raise RuntimeError(f"Push send failed: {response.exception}")
            return messaging.SendResponse(
                {"name": batch_response.responses[0]},
                None,
            )
        except FirebaseError as e:
            await self.deactivate_devices_with_error_result_async(
                [self.registration_id],
                [messaging.SendResponse({"name": None}, e)]
            )
            raise

    async def deactivate_devices_with_error_result_async(
            self,
            registration_ids: list[str],
            results: list[Union[messaging.SendResponse, messaging.ErrorInfo]],
    ) -> list[str]:
        """
        Deactivates devices that failed to receive a message.
        """
        if not results:
            return []

        if isinstance(results[0], messaging.SendResponse):
            deactivated_ids = [
                token
                for item, token in zip(results, registration_ids)
                if _validate_exception_for_deactivation(item.exception)
            ]
        else:
            deactivated_ids = [
                registration_ids[x.index]
                for x in results
                if _validate_exception_for_deactivation(x.reason)
            ]

        await self.__class__.objects.filter(
            registration_id__in=deactivated_ids
        ).aupdate(active=False)

        await self._delete_inactive_devices_if_requested(deactivated_ids)
        return deactivated_ids

    async def _delete_inactive_devices_if_requested(self, registration_ids: list[str]) -> None:
        """
        Deletes inactive devices if configured to do so.
        """
        if device_settings.DELETE_INACTIVE_DEVICES:
            await self.__class__.objects.filter(registration_id__in=registration_ids).adelete()


class CustomFCMDevice(AbstractCustomFCMDevice):
    """
    Concrete implementation of AbstractCustomFCMDevice.
    """
    class Meta(AbstractCustomFCMDevice.Meta):
        abstract = False
        verbose_name = _("FCM device")
        verbose_name_plural = _("FCM devices")


class AbstractUserDeviceSettings(models.Model):
    """
    Abstract base class for user device settings.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name="%(app_label)s_%(class)s_set",
    )
    device = models.ForeignKey(
        device_settings.FCM_DEVICE_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("Device"),
        related_name="user_settings",
    )
    is_receive_notifications = models.BooleanField(
        default=True,
        verbose_name=_("Receive notifications"),
        help_text=_(
            "An indicator that indicates that the user wants to receive notifications"
        ),
    )
    created_at = models.DateTimeField(
        verbose_name=_("Created at"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        verbose_name=_("Updated at"),
        auto_now=True,
    )

    def __str__(self) -> str:
        return f"Device settings: {self.user} - {self.device}"

    class Meta:
        abstract = True
        verbose_name = _("User device settings")
        verbose_name_plural = _("User devices settings")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'device'],
                name='%(app_label)s_%(class)s_unique_user_device'
            )
        ]


class UserDeviceSettings(AbstractUserDeviceSettings):
    """
    Concrete implementation of AbstractUserDeviceSettings.
    """
    class Meta(AbstractUserDeviceSettings.Meta):
        abstract = False
        db_table = "user_device_settings"
        verbose_name = _("User device settings")
        verbose_name_plural = _("User devices settings")


class NotificationsQuerySet(models.QuerySet):
    """
    Custom QuerySet for Notification model.
    """
    def mark_viewed(self) -> int:
        """
        Marks all notifications in the queryset as viewed.
        """
        return self.update(is_viewed=True)


class NotificationsManager(models.Manager):
    """
    Custom Manager for Notification model.
    """
    def get_queryset(self) -> NotificationsQuerySet:
        """
        Returns a NotificationsQuerySet instance.
        """
        return NotificationsQuerySet(self.model, using=self._db)

    def mark_viewed(self) -> int:
        """
        Marks all notifications as viewed.
        """
        return self.get_queryset().mark_viewed()


class AbstractNotification(models.Model):
    """
    Abstract base class for user notifications.
    """
    type = models.CharField(
        max_length=255,
        verbose_name=_("Type"),
        choices=get_notification_types().choices,
    )
    is_viewed = models.BooleanField(
        default=False,
        verbose_name=_("Is viewed"),
        help_text=_("Indication that notification has been viewed by user"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )
    payload = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name=_("Payload"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name="notifications",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Title snapshot"),
    )
    body = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Body snapshot"),
    )
    image = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("Image snapshot"),
        max_length=500,
    )

    objects = NotificationsManager()

    def __str__(self) -> str:
        return f"Notification: {self.type} - {self.created_at}"

    class Meta:
        abstract = True
        verbose_name = _("User notification")
        verbose_name_plural = _("User notifications")
    
    @property
    def push_provider(self) -> Any:
        """
        Returns the push provider for this notification type.
        """
        from django_devices.push import push_provider_registry
        return push_provider_registry.get_provider(self.type)

    def get_push_notification_data(self) -> NotificationPushData:
        return NotificationPushData(
            id=self.pk,
            type=self.type,
            payload=self.payload,
            created_at=self.created_at,
        )

    def to_pydantic(self) -> NotificationResponseSchema:
        schema = NotificationResponseSchema(
            id=self.pk,
            type=self.type,
            body=self.body,
            title=self.title,
            image=self.image,
            payload=self.payload,
            created_at=self.created_at.timestamp(),
            is_viewed=self.is_viewed
        )
        return schema
class Notification(AbstractNotification):
    """
    Concrete implementation of AbstractNotification.
    """
    class Meta(AbstractNotification.Meta):
        abstract = False
        db_table = "user_notifications"
