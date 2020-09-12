from django import forms
from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import NoReverseMatch, reverse
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from tree_queries.forms import TreeNodeChoiceField

from cabinet.models import Folder


class UploadForm(forms.Form):
    folder = TreeNodeChoiceField(label=_("folder"), queryset=Folder.objects.all())
    file = forms.FileField(label=_("file"))


class CabinetFileRawIdWidget(ForeignKeyRawIdWidget):
    template_name = "admin/cabinet/cabinet_file_raw_id_widget.html"

    class Media:
        css = {"all": ["cabinet/inline-upload.css"]}
        js = ["admin/js/jquery.init.js", "cabinet/inline-upload.js"]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        instance = getattr(self, "instance", None)
        context["cabinet"] = {
            "upload_form": UploadForm(
                prefix="cu-{}".format(id(self)),
                initial={"folder": instance and instance.folder_id},
            ),
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
                "admin:%s_%s_change"
                % (obj._meta.app_label, obj._meta.object_name.lower()),
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
