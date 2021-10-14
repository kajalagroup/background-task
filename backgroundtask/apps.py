from django.apps import AppConfig


class BackgroundTaskConfig(AppConfig):
    name = "backgroundtask"
    # default_auto_field = "django.db.models.AutoField"
    def ready(self):
        from . import signals as signals_init  # noqa
