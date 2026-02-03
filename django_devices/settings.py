from django.conf import settings
from django.test.signals import setting_changed

DEFAULTS = {
    "ONE_DEVICE_PER_USER": False,
    "DELETE_INACTIVE_DEVICES": False,
    "FCM_DEVICE_MODEL": "django_devices.CustomFCMDevice",
    "DEVICE_SETTINGS_MODEL": "django_devices.UserDeviceSettings",
    "NOTIFICATION_MODEL": "django_devices.Notification",
    "NOTIFICATION_TYPE_CHOICES": "django_devices.choices.DefaultNotificationTypeChoices",
    "DEFAULT_FIREBASE_APP": None,
    "DEVICE_ID_HEADER": "X-DEVICE-ID",
}
IMPORT_STRINGS = [
    "NOTIFICATION_TYPE_CHOICES",
]

USER_SETTINGS_NAME = "DEVICES_SETTINGS"


class DeviceSettings:
    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        self._user_settings = user_settings
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = {}

    @property
    def user_settings(self):
        if not self._user_settings:
            self._user_settings = getattr(settings, USER_SETTINGS_NAME, {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting: '{attr}'")

        try:

            val = self.user_settings[attr]
        except KeyError:
            val = self.defaults[attr]

        if attr in self.import_strings and isinstance(val, str):
            val = self.perform_import(val, attr)

        self._cached_attrs[attr] = val
        return val

    def perform_import(self, val, setting_name):
        from django.utils.module_loading import import_string

        try:
            return import_string(val)
        except ImportError as e:
            msg = f"Could not import '{val}' for setting '{setting_name}'. {e.__class__.__name__}: {e}."
            raise ImportError(msg)

    def reload(self):
        self._user_settings = None
        self._cached_attrs = {}


device_settings = DeviceSettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_api_settings(*args, **kwargs):
    setting = kwargs["setting"]
    if setting == USER_SETTINGS_NAME:
        device_settings.reload()


setting_changed.connect(reload_api_settings)
