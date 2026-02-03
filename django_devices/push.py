from abc import ABC, abstractmethod
from typing import Any, Type, Callable
import random
from django.utils import translation
from django.utils.module_loading import autodiscover_modules
from django.utils.encoding import force_str
from django.core.exceptions import ImproperlyConfigured

from django_devices.utils import get_notification_types
from django_devices.schemas.notifications.base import PushMessageSchema


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


class BasePushMessageProvider(ABC):
    """
    Abstract base class for a push message provider.

    Each provider is responsible for a specific notification type and must
    define the messages for it.
    """

    @property
    @abstractmethod
    def notification_type(self) -> Any:
        """
        The notification type this provider handles.
        
        Returns:
            Any: The notification type (usually a value from TextChoices).
        """
        raise NotImplementedError

    @abstractmethod
    def get_messages(self) -> list[PushMessageSchema]:
        """
        Returns a list of message templates for PUSH notifications.
        
        Returns:
            list[PushMessageSchema]: A list of PushMessageSchema containing 'title', 'body', and 'image'.
        """
        raise NotImplementedError

    @abstractmethod
    def get_site_message(self) -> PushMessageSchema:
        """
        Returns the SINGLE stable template for notification history in DB.
        
        Returns:
            PushMessageSchema: A PushMessageSchema containing 'title', 'body', and 'image'.
        """
        raise NotImplementedError

    def get_push_text_data(
        self, language_code: str, payload: dict[str, Any]
    ) -> PushMessageSchema:
        """
        Selects a random message for PUSH, translates it, and formats it with the payload.

        Args:
            language_code (str): The language code for translation.
            payload (dict[str, Any]): The data to format the message with.

        Returns:
            PushMessageSchema: The formatted message data.
        """
        translation.activate(language=language_code)
        messages = self.get_messages()
        if not messages:
            raise ImproperlyConfigured(
                f"Provider '{self.__class__.__name__}' for type '{self.notification_type}' "
                f"returned an empty list of messages in get_messages()."
            )

        message_template = random.choice(messages)

        return PushMessageSchema(
            title=force_str(message_template.title).format_map(SafeDict(**payload)),
            body=force_str(message_template.body).format_map(SafeDict(**payload)),
            image=(
                None
                if message_template.image is None
                else force_str(message_template.image).format_map(SafeDict(**payload))
            ),
        )

    def get_site_text_data(
        self, language_code: str, payload: dict[str, Any]
    ) -> PushMessageSchema:
        """
        Selects the stable message for DB, translates it, and formats it with the payload.

        Args:
            language_code (str): The language code for translation.
            payload (dict[str, Any]): The data to format the message with.

        Returns:
            PushMessageSchema: The formatted message data.
        """
        translation.activate(language=language_code)
        template = self.get_site_message()

        return PushMessageSchema(
            title=force_str(template.title).format_map(SafeDict(**payload)),
            body=force_str(template.body).format_map(SafeDict(**payload)),
            image=(
                 None if template.image is None
                 else force_str(template.image).format_map(SafeDict(**payload))
            ),
        )

    def transform_payload_for_push(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Transforms the full payload into a smaller payload suitable for push notifications.

        Args:
            payload (dict[str, Any]): The original notification payload.

        Returns:
            dict[str, Any]: The transformed payload.
        """
        return payload


class PushProviderRegistry:
    """
    A registry for all push message providers.
    """

    def __init__(self) -> None:
        """
        Initializes the registry.
        """
        self._registry: dict[Any, BasePushMessageProvider] = {}

    def register(self, provider_class: Type[BasePushMessageProvider]) -> None:
        """
        Registers a provider class for its notification type.

        Args:
            provider_class (Type[BasePushMessageProvider]): The provider class to register.
        """
        instance = provider_class()

        choices_class = get_notification_types()
        if hasattr(instance, 'notification_type') and instance.notification_type not in choices_class.values:
             pass

        if instance.notification_type in self._registry:
            return
        self._registry[instance.notification_type] = instance

    def get_provider(self, notification_type: Any) -> BasePushMessageProvider:
        """
        Gets an instance of a provider for a given notification type.

        Args:
            notification_type (Any): The notification type.

        Returns:
            BasePushMessageProvider: The provider instance.
            
        Raises:
            NotImplementedError: If no provider is found for the given type.
        """
        provider = self._registry.get(notification_type)
        if not provider:
            raise NotImplementedError(f"No push provider registered for notification type: {notification_type}")
        return provider

    def autodiscover(self) -> None:
        """
        Auto-discovers 'providers.py' modules in all installed apps.
        """
        autodiscover_modules('providers')


push_provider_registry = PushProviderRegistry()
register = push_provider_registry.register
