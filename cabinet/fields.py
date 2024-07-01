from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils.text import Truncator

# Import cabinet.models for the settings.CABINET_FILE_MODEL side-effect
import cabinet.models  # noqa: F401


class CabinetFileRawIdWidget(ForeignKeyRawIdWidget):
    template_name = "admin/cabinet/cabinet_file_raw_id_widget.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        instance = getattr(self, "instance", None)
        context["cabinet"] = {
            "instance": instance,
        }
        context["related_url"] += "&folder__id__exact={}".format(
            instance.folder_id if instance else "last"
        )
        return context

    def label_and_url_for_value(self, value):
        # Copied from django/contrib/admin/widgets.py with the addition of
        # saving the obj as self.instance
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.model._default_manager.using(self.db).get(**{key: value})
        except (ValueError, self.rel.model.DoesNotExist, ValidationError):
            obj = None
            return "", ""

        try:
            url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.object_name.lower()}_change",
                args=(obj.pk,),
                current_app=self.admin_site.name,
            )
        except NoReverseMatch:
            url = ""  # Admin not registered for target model.

        self.instance = obj
        return Truncator(obj).words(14, truncate="..."), url


class CabinetForeignKey(models.ForeignKey):
    def __init__(self, to=None, **kwargs):
        super().__init__(to or settings.CABINET_FILE_MODEL, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return (name, "django.db.models.ForeignKey", args, kwargs)

    def formfield(self, **kwargs):
        widget = kwargs.get("widget")
        if widget and isinstance(widget, ForeignKeyRawIdWidget):
            widget.__class__ = CabinetFileRawIdWidget
        return super().formfield(**kwargs)
