from typing import Any

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from dataclasses import asdict, is_dataclass

from django_devices.schemas import CreateDeviceProtocol, UpdateDeviceSettingsProtocol
from django_devices.settings import device_settings
from django_devices.utils import get_device_model, get_user_device_settings_model


class DeviceHandler:
    def __init__(
        self,
        user_id: int,
    ) -> None:
        self.user_id = user_id
        self.Device = get_device_model()
        self.UserDeviceSettings = get_user_device_settings_model()

    def check_existence(
        self,
        device_id: str,
    ) -> bool:
        return self.UserDeviceSettings.objects.filter(
            user_id=self.user_id, device__device_id=device_id
        ).exists()

    async def acheck_existence(
        self,
        device_id: str,
    ) -> bool:
        return await sync_to_async(self.check_existence)(device_id)

    def create(self, payload: CreateDeviceProtocol) -> None:
        with transaction.atomic():
            if device_settings.ONE_DEVICE_PER_USER:
                self.Device.objects.filter(user_id=self.user_id).exclude(
                    device_id=payload.device_id
                ).update(active=False)

            if payload.registration_id:
                self.Device.objects.filter(
                    registration_id=payload.registration_id,
                ).exclude(device_id=payload.device_id, user_id=self.user_id).update(
                    registration_id=None, active=False
                )

            device, created = self.Device.objects.get_or_create(
                device_id=payload.device_id,
                user_id=self.user_id,
                defaults={
                    "registration_id": payload.registration_id,
                    "type": payload.platform,
                    "active": bool(payload.registration_id),
                },
            )

            if not created:
                device.registration_id = payload.registration_id
                device.type = payload.platform
                device.active = bool(payload.registration_id)
                device.save(update_fields=["registration_id", "type", "active"])

            settings_qs = self.UserDeviceSettings.objects.filter(
                user_id=self.user_id, device__device_id=device.device_id
            )

            if not settings_qs.exists():
                initial_settings = {}
                last_user_setting = (
                    self.UserDeviceSettings.objects.filter(user_id=self.user_id)
                    .exclude(device__device_id=device.device_id)
                    .order_by("-updated_at")
                    .first()
                )

                if last_user_setting:
                    for field in self.UserDeviceSettings._meta.get_fields():
                        if (
                            field.name not in ["id", "user", "device"]
                            and not field.is_relation
                        ):
                            initial_settings[field.name] = getattr(
                                last_user_setting, field.name
                            )

                self.UserDeviceSettings.objects.create(
                    user_id=self.user_id, device=device, **initial_settings
                )

    async def acreate(
        self,
        payload: CreateDeviceProtocol,
    ) -> None:
        await sync_to_async(self.create)(payload)

    @staticmethod
    def _normalize_payload(
        data_source: Any,
    ) -> dict:
        if hasattr(data_source, "model_dump"):
            return data_source.model_dump(exclude_unset=True)
        if hasattr(data_source, "dict"):
            return data_source.dict(exclude_unset=True)
        if is_dataclass(data_source):
            return asdict(data_source)
        if isinstance(data_source, dict):
            return data_source
        return {
            k: v
            for k, v in data_source.__dict__.items()
            if not k.startswith("_") and not callable(v)
        }

    def update(
        self,
        payload: UpdateDeviceSettingsProtocol,
        force: bool = False,
    ) -> None:
        update_data = self._normalize_payload(data_source=payload.payload)
        if not update_data:
            return

        if not force:
            update_data = {k: v for k, v in update_data.items() if v is not None}

        if not update_data:
            return

        valid_fields = {f.name for f in self.UserDeviceSettings._meta.get_fields()}
        filtered_data = {k: v for k, v in update_data.items() if k in valid_fields}

        if not filtered_data:
            return

        filtered_data["updated_at"] = timezone.now()
        filter_kwargs = {
            "user_id": self.user_id,
            "device__device_id": payload.device_id,
        }
        self.UserDeviceSettings.objects.filter(**filter_kwargs).update(**filtered_data)

    async def aupdate(
        self,
        payload: UpdateDeviceSettingsProtocol,
        force: bool = False,
    ) -> None:
        await sync_to_async(self.update)(payload, force=force)
