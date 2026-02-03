from datetime import datetime
from typing import Any

from django.utils import timezone
from django.utils.functional import Promise
from pydantic import BaseModel, field_validator, ConfigDict, Field, AnyHttpUrl

from django_devices.utils import get_notification_types, cleanhtml


class PushMessageSchema(BaseModel):
    """
    Schema for a push message template or formatted message.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str
    body: str
    image: str | None = None

    @field_validator("title", "body", "image", mode="before")
    @classmethod
    def convert_promise(cls, v: Any) -> Any:
        """
        Converts Django Promise (lazy translation) objects to string.
        """
        if isinstance(v, Promise):
            return str(v)
        return v

    @field_validator("title", "body", mode="after")
    @classmethod
    def clean_html_content(cls, v: str) -> str:
        """
        Cleans HTML tags from title and body.
        """
        return cleanhtml(v)


class NotificationPushData(BaseModel):
    """
    Schema for notification push data.
    """

    id: int | None = None
    type: Any  # Can be Enum or str
    payload: dict = Field(default_factory=dict)
    created_at: datetime

    def to_push_payload_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation suitable for push payload.
        Converts datetime to timestamp.
        """
        data = self.model_dump()
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].timestamp()
        return data

    @classmethod
    def create_without_object(
        cls,
        type_: Any,
        payload: dict | None = None,
        created_at: datetime | None = None,
    ) -> "NotificationPushData":
        """
        Creates a NotificationPushData instance without a database object.
        """
        return cls(
            type=type_,
            payload=payload if payload is not None else dict(),
            created_at=created_at if created_at is not None else timezone.now(),
        )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Any) -> Any:
        """
        Validates that the notification type exists in the configured choices.
        """
        choices_class = get_notification_types()
        valid_values = set(choices_class.values)
        valid_names = set(choices_class.names)

        is_valid = False
        if hasattr(v, "value"):
            if v.value in valid_values:
                is_valid = True
        elif v in valid_values or v in valid_names:
            is_valid = True

        if not is_valid:
            raise ValueError(
                f"Invalid notification type: {v}. Must be one of {valid_values}"
            )

        return v


class NotificationResponseSchema(BaseModel):
    """
    Schema for notification response.
    """

    id: int
    type: Any
    body: str
    title: str
    image: AnyHttpUrl | None
    payload: dict | None
    created_at: float
    is_viewed: bool
