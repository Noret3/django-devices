from typing import Protocol, runtime_checkable, Any
from fcm_django.models import DeviceType


@runtime_checkable
class DeviceDataProtocol(Protocol):
    device_id: str


@runtime_checkable
class CreateDeviceProtocol(DeviceDataProtocol, Protocol):
    platform: DeviceType
    registration_id: str | None


@runtime_checkable
class UpdateDeviceSettingsProtocol(DeviceDataProtocol, Protocol):
    payload: Any
