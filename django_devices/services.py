import json
import logging
from typing import Any

from firebase_admin.messaging import (
    APNSConfig,
    APNSPayload,
    Aps,
    ApsAlert,
    Message,
    Notification,
)

from django_devices.models import UserDeviceSettings
from django_devices.push import push_provider_registry
from django_devices.schemas.notifications.base import NotificationPushData, PushMessageSchema
from django_devices.utils import get_notification_model

logger = logging.getLogger(__name__)


class PushSender:
    """
    Service for sending push notifications.
    """

    @classmethod
    def _prepare_push_content(
        cls, type_: Any, raw_payload: dict, language_code: str
    ) -> tuple[PushMessageSchema, dict]:
        """
        Prepares the push message content and payload using the appropriate provider.
        
        Returns:
            tuple[PushMessageSchema, dict]: A tuple containing the message (title/body) 
            and the final payload dictionary for the 'data' field.
        
        Raises:
            NotImplementedError: If no provider is found for the given type.
        """
        provider = push_provider_registry.get_provider(type_)
        
        final_payload = provider.transform_payload_for_push(raw_payload)
        push_msg = provider.get_push_text_data(language_code, final_payload)
            
        return push_msg, final_payload

    @classmethod
    def send_push(
        cls,
        device: UserDeviceSettings,
        language_code: str,
        payload: NotificationPushData,
    ) -> None:
        """
        Sends a push notification to a specific device.
        """
        payload_dict = payload.to_push_payload_dict()
        
        push_msg, push_specific_payload = cls._prepare_push_content(
            type_=payload.type,
            raw_payload=payload_dict["payload"],
            language_code=language_code
        )

        payload_dict["payload"] = push_specific_payload
        
        data_for_push = {"data": json.dumps(payload_dict, default=str)}

        try:
            response = device.device.send_message(
                Message(
                    notification=Notification(
                        title=push_msg.title,
                        body=push_msg.body,
                        image=push_msg.image,
                    ),
                    data=data_for_push,
                    apns=APNSConfig(
                        payload=APNSPayload(
                            aps=Aps(
                                alert=ApsAlert(
                                    title=push_msg.title,
                                    body=push_msg.body,
                                    launch_image=push_msg.image,
                                ),
                                sound="default",
                            )
                        )
                    ),
                )
            )
            logger.info(
                f"Push sent to user {device.user_id}, device {device.device.device_id}, msg_id: {response.message_id}"
            )
        except Exception:
            logger.exception(
                f"Unable to send push message to device: {device.id}",
                exc_info=True,
            )

    @classmethod
    def send_to_user(
        cls,
        user_id: int,
        language_code: str,
        payload: NotificationPushData,
    ) -> None:
        """
        Sends a push notification to all active devices of the user.
        """
        devices = (
            UserDeviceSettings.objects.filter(
                user_id=user_id,
                device__registration_id__isnull=False,
                is_receive_notifications=True,
            )
            .select_related(
                "device",
                "user",
            )
            .distinct("id")
        )

        for device in devices:
            cls.send_push(
                device=device,
                language_code=language_code,
                payload=payload,
            )

    @classmethod
    async def send_push_async(
        cls,
        device: UserDeviceSettings,
        language_code: str,
        payload: NotificationPushData,
    ) -> None:
        """
        Asynchronously sends a push notification to a specific device.
        """
        payload_dict = payload.to_push_payload_dict()
        
        push_msg, push_specific_payload = cls._prepare_push_content(
            type_=payload.type,
            raw_payload=payload_dict["payload"],
            language_code=language_code
        )

        payload_dict["payload"] = push_specific_payload

        data_for_push = {"data": json.dumps(payload_dict, default=str)}

        try:
            await device.device.send_message_async(
                Message(
                    notification=Notification(
                        title=push_msg.title,
                        body=push_msg.body,
                        image=push_msg.image,
                    ),
                    data=data_for_push,
                    apns=APNSConfig(
                        payload=APNSPayload(
                            aps=Aps(
                                alert=ApsAlert(
                                    title=push_msg.title,
                                    body=push_msg.body,
                                    launch_image=push_msg.image,
                                ),
                                sound="default",
                            )
                        )
                    ),
                )
            )
            logger.info(
                f"Async push sent to user {device.user_id}, device {device.device.device_id}"
            )
        except Exception:
            logger.exception(
                f"Unable to send push message to device: {device.id}",
                exc_info=True,
            )

    @classmethod
    async def send_to_user_async(
        cls,
        user_id: int,
        language_code: str,
        payload: NotificationPushData,
    ) -> None:
        """
        Asynchronously sends a push notification to all active devices of the user.
        """
        devices = (
            UserDeviceSettings.objects.filter(
                user_id=user_id,
                device__registration_id__isnull=False,
                is_receive_notifications=True,
            )
            .select_related(
                "device",
                "user",
            )
            .distinct("id")
        )

        async for device in devices:
            await cls.send_push_async(
                device=device,
                language_code=language_code,
                payload=payload,
            )


class NotificationService:
    """
    Service for managing notifications.
    """

    @staticmethod
    def create_notification(
        user_id: int,
        type_: Any,
        payload: dict[str, Any] | None = None,
        language_code: str = "en",
        send_push: bool = True,
    ) -> Any:
        """
        Creates a notification in the database and optionally sends a push notification.
        
        Raises:
            NotImplementedError: If no provider is found for the given type.
        """
        NotificationModel = get_notification_model()

        provider = push_provider_registry.get_provider(type_)
        
        site_msg = provider.get_site_text_data(language_code, payload or {})

        notification = NotificationModel.objects.create(
            user_id=user_id,
            type=type_,
            payload=payload or {},
            title=site_msg.title,
            body=site_msg.body,
            image=site_msg.image,
        )

        if send_push:
            PushSender.send_to_user(
                user_id=user_id,
                language_code=language_code,
                payload=notification.get_push_notification_data(),
            )

        return notification

    @staticmethod
    async def acreate_notification(
        user_id: int,
        type_: Any,
        payload: dict[str, Any] | None = None,
        language_code: str = "en",
        send_push: bool = True,
    ) -> Any:
        """
        Asynchronously creates a notification in the database and optionally sends a push notification.
        
        Raises:
            NotImplementedError: If no provider is found for the given type.
        """
        NotificationModel = get_notification_model()

        provider = push_provider_registry.get_provider(type_)
        
        site_msg = provider.get_site_text_data(language_code, payload or {})

        notification = await NotificationModel.objects.acreate(
            user_id=user_id,
            type=type_,
            payload=payload or {},
            title=site_msg.title,
            body=site_msg.body,
            image=site_msg.image,
        )

        if send_push:
            await PushSender.send_to_user_async(
                user_id=user_id,
                language_code=language_code,
                payload=notification.get_push_notification_data(),
            )

        return notification
