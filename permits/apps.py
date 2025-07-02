from django.apps import AppConfig


class PermitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'permits'

    def ready(self):
        """
        Initialize app when Django starts.
        Only import signals here to avoid circular imports.
        """
        try:
            import permits.signals  # type: ignore # noqa: F401
        except ImportError:
            pass
