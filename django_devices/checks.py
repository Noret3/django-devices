from django.core.checks import Error, register, Tags
from django_devices.push import push_provider_registry
from django_devices.utils import get_notification_types


@register(Tags.compatibility)
def check_push_providers(app_configs, **kwargs):
    """
    Checks that all registered push providers have valid messages and types.
    """
    errors = []
    
    push_provider_registry.autodiscover()
    
    choices_class = get_notification_types()
    valid_types = set(choices_class.values)

    for type_, provider in push_provider_registry._registry.items():
        if type_ not in valid_types:
            errors.append(
                Error(
                    f"Push provider '{provider.__class__.__name__}' is registered for invalid type '{type_}'.",
                    hint=f"Available types are: {', '.join(map(str, valid_types))}. Check NOTIFICATION_TYPE_CHOICES.",
                    obj=provider,
                    id="django_devices.E003",
                )
            )

        try:
            messages = provider.get_messages()
            if not messages:
                errors.append(
                    Error(
                        f"Push provider '{provider.__class__.__name__}' for type '{type_}' "
                        f"returned an empty list of messages.",
                        hint="Implement get_messages() to return at least one PushMessageSchema.",
                        obj=provider,
                        id="django_devices.E001",
                    )
                )
        except Exception as e:
            errors.append(
                Error(
                    f"Push provider '{provider.__class__.__name__}' raised an exception during check: {e}",
                    obj=provider,
                    id="django_devices.E002",
                )
            )
            
    return errors
