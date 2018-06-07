from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CabinetConfig(AppConfig):
    name = "cabinet"
    verbose_name = _("Cabinet media library")
