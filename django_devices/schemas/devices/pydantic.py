from pydantic import BaseModel, Field, ConfigDict
from fcm_django.models import DeviceType


class BaseDeviceSchema(BaseModel):
    """
    Base schema for device data.
    """
    device_id: str = Field(
        ...,
        description="Unique device identifier",
    )


class CreateDeviceSchema(BaseDeviceSchema):
    """
    Schema for creating a new device.
    """
    platform: DeviceType = Field(
        DeviceType.WEB,
        description="Device platform type",
    )
    registration_id: str | None = Field(
        None,
        description="Registration token"
    )


class BaseUpdateDeviceSettingsSchema(BaseDeviceSchema):
    """
    Schema for updating device settings.
    """
    model_config = ConfigDict(extra="allow")

    is_receive_notifications: bool | None = Field(
        None,
        description="Indicate whether notifications should be received or not.",
    )
