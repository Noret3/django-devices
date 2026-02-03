# Django Devices

A robust Django application for managing user devices and sending push notifications via FCM (Firebase Cloud Messaging) and APNS (Apple Push Notification Service).

## Features

*   **Device Management**: Store and manage user devices (FCM tokens).
*   **Push Notifications**: Send notifications to specific users or devices.
*   **Provider Pattern**: Clean architecture for defining notification content and logic.
*   **Localization**: Built-in support for translating notifications based on user language.
*   **Fail-Fast Validation**: System checks ensure all notification types have valid providers.
*   **Async Support**: Full support for asynchronous sending (`acreate_notification`, `send_push_async`).
*   **Data Integrity**: Automatic HTML cleaning and strict typing with Pydantic.

## Installation

### Using pip

```bash
pip install django-devices
```

### Using poetry

```bash
poetry add django-devices
```

### Using uv

```bash
uv add django-devices
```

## Configuration

1.  Add `django_devices` and `fcm_django` to your `INSTALLED_APPS`:

    ```python
    # settings.py
    INSTALLED_APPS = [
        # ...
        "fcm_django",
        "django_devices",
        # ...
    ]
    ```

2.  Configure `DEVICES_SETTINGS` in `settings.py`:

    ```python
    # settings.py
    
    DEVICES_SETTINGS = {
        # Path to your TextChoices Enum defining notification types
        "NOTIFICATION_TYPE_CHOICES": "my_app.choices.NotificationTypeChoices",
        
        # Optional: Path to your custom Notification model
        # "NOTIFICATION_MODEL": "my_app.models.Notification",
    }
    ```

3.  Define your Notification Types (e.g., in `my_app/choices.py`):

    ```python
    from django.db import models
    from django.utils.translation import gettext_lazy as _

    class NotificationTypeChoices(models.TextChoices):
        ORDER_CREATED = "ORDER_CREATED", _("Order Created")
        WELCOME = "WELCOME", _("Welcome")
    ```

## Usage

### 1. Create a Push Provider

Create a `providers.py` file in your app. The library will automatically discover it.

```python
# my_app/providers.py
from django.utils.translation import gettext_lazy as _
from django_devices.push import BasePushMessageProvider, register
from django_devices.schemas.notifications.base import PushMessageSchema
from my_app.choices import NotificationTypeChoices

class OrderCreatedProvider(BasePushMessageProvider):
    notification_type = NotificationTypeChoices.ORDER_CREATED

    def get_messages(self) -> list[PushMessageSchema]:
        # Return a list of templates. One will be chosen at random for the PUSH.
        return [
            PushMessageSchema(
                title=_("Order #{order_id} Confirmed"),
                body=_("Your order for {amount} items has been received."),
                image=None
            ),
            PushMessageSchema(
                title=_("Yay! Order #{order_id} is in!"),
                body=_("We are processing your order."),
                image=None
            )
        ]

    def get_site_message(self) -> PushMessageSchema:
        # Return the SINGLE stable template for notification history in DB.
        return PushMessageSchema(
            title=_("Order #{order_id} Confirmed"),
            body=_("Your order for {amount} items has been received."),
            image=None
        )

    def transform_payload_for_push(self, payload: dict) -> dict:
        # Optional: Transform payload for push (e.g. remove heavy data)
        return {
            "order_id": payload.get("id"),
            "amount": payload.get("total_amount"),
        }

# Register the provider
register(OrderCreatedProvider)
```

### 2. Send Notifications

#### Option A: Save to DB + Send Push (Recommended)

Use `NotificationService`. This creates a record in the database (using `get_site_message`) and sends a push (using a random template from `get_messages`).

```python
from django_devices.services import NotificationService
from my_app.choices import NotificationTypeChoices

# Sync
NotificationService.create_notification(
    user_id=user.id,
    type_=NotificationTypeChoices.ORDER_CREATED,
    payload={
        "id": 123, 
        "total_amount": 500, 
        "items": [...] # Full payload stored in DB
    },
    language_code="en"
)

# Async
await NotificationService.acreate_notification(
    user_id=user.id,
    type_=NotificationTypeChoices.ORDER_CREATED,
    payload={"id": 123, ...},
    language_code="en"
)
```

#### Option B: Send Push Only (No DB Record)

Use `PushSender` directly if you don't need history.

```python
from django_devices.services import PushSender
from django_devices.schemas.notifications.base import NotificationPushData
from my_app.choices import NotificationTypeChoices
from django.utils import timezone

push_data = NotificationPushData(
    type=NotificationTypeChoices.WELCOME,
    payload={"username": "Alice"},
    created_at=timezone.now()
)

# Sync
PushSender.send_to_user(
    user_id=user.id,
    language_code="en",
    payload=push_data
)

# Async
await PushSender.send_to_user_async(
    user_id=user.id,
    language_code="en",
    payload=push_data
)
```

## Advanced

### Custom Notification Model

You can extend `AbstractNotification` to add custom fields.

```python
# my_app/models.py
from django.db import models
from django_devices.models import AbstractNotification

class MyNotification(AbstractNotification):
    priority = models.IntegerField(default=0)
    
    class Meta(AbstractNotification.Meta):
        abstract = False
```

Don't forget to update `DEVICES_SETTINGS["NOTIFICATION_MODEL"]`.

### System Checks

The library includes Django system checks that run on startup (`runserver`, `migrate`). They verify that:
1. All registered providers have a valid `notification_type`.
2. All providers implement `get_messages` and return at least one message.

This prevents runtime errors caused by missing configuration.
