from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangoDevicesConfig(AppConfig):
    """
    Configuration class for the django_devices application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_devices'
    verbose_name = _("Devices")

    def ready(self) -> None:
        """
        Initializes the application by auto-discovering push providers.
        """
        from django_devices.push import push_provider_registry
        
        push_provider_registry.autodiscover()
        import django_devices.checks  # noqa
