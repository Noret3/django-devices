import re
from typing import TYPE_CHECKING, Type

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.http.request import HttpRequest

from django_devices.settings import device_settings

if TYPE_CHECKING:
    from django_devices.models import (
        AbstractCustomFCMDevice,
        AbstractUserDeviceSettings,
        AbstractNotification,
    )


def get_device_id_from_request(request: HttpRequest) -> str | None:
    """
    Retrieves the device ID from the request headers.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        str | None: The device ID if found, else None.
    """
    return request.headers.get(device_settings.DEVICE_ID_HEADER)


def get_device_model() -> "type[AbstractCustomFCMDevice]":
    """
    Retrieves the FCM device model configured in settings.

    Returns:
        type[AbstractCustomFCMDevice]: The device model class.

    Raises:
        ImproperlyConfigured: If the model is not found.
    """
    model_name = device_settings.FCM_DEVICE_MODEL
    try:
        return apps.get_model(model_name, require_ready=False)
    except (ValueError, LookupError):
        raise ImproperlyConfigured(
            f"FCM_DEVICE_MODEL refers to model '{model_name}' that is not installed."
        )


def get_user_device_settings_model() -> "type[AbstractUserDeviceSettings]":
    """
    Retrieves the user device settings model configured in settings.

    Returns:
        type[AbstractUserDeviceSettings]: The settings model class.

    Raises:
        ImproperlyConfigured: If the model is not found.
    """
    model_name = device_settings.DEVICE_SETTINGS_MODEL
    try:
        return apps.get_model(model_name, require_ready=False)
    except (ValueError, LookupError):
        raise ImproperlyConfigured(
            f"DEVICE_SETTINGS_MODEL refers to model '{model_name}' that is not installed."
        )


def get_notification_model() -> "type[AbstractNotification]":
    """
    Retrieves the notification model configured in settings.

    Returns:
        type[AbstractNotification]: The notification model class.

    Raises:
        ImproperlyConfigured: If the model is not found.
    """
    model_name = device_settings.NOTIFICATION_MODEL
    try:
        return apps.get_model(model_name, require_ready=False)
    except (ValueError, LookupError):
        raise ImproperlyConfigured(
            f"NOTIFICATION_MODEL refers to model '{model_name}' that is not installed."
        )


def get_notification_types() -> Type[models.TextChoices]:
    """
    Returns the TextChoices class configured in settings.

    Returns:
        Type[models.TextChoices]: The notification types choices class.
    """
    return device_settings.NOTIFICATION_TYPE_CHOICES


def cleanhtml(raw_html: str) -> str:
    """
    Removes HTML tags from a string.

    Args:
        raw_html (str): The string containing HTML.

    Returns:
        str: The cleaned string.
    """
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext
