from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class BackgroundTaskConfig(AppConfig):
    name = "kbackgroundtask"
    verbose_name = _('Background Task Management')
    # default_auto_field = "django.db.models.AutoField"
    def ready(self):
        from . import signals as signals_init  # noqa
