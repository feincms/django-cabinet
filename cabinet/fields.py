from django import forms
from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy as _

from cabinet.base_admin import folder_choices
from cabinet.models import Folder

try:
    from django.urls import NoReverseMatch, reverse
except ImportError:
    from django.core.urlresolvers import NoReverseMatch, reverse


class UploadForm(forms.Form):
    folder = forms.ModelChoiceField(label=_("folder"), queryset=Folder.objects.all())
    file = forms.FileField(label=_("file"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folder"].choices = list(folder_choices())


class CabinetFileRawIdWidget(ForeignKeyRawIdWidget):
    template_name = "admin/cabinet/cabinet_file_raw_id_widget.html"

    class Media:
        css = {"all": ["cabinet/inline-upload.css"]}
        js = ["cabinet/inline-upload.js"]

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
        if instance:
            context["related_url"] += "&folder__id__exact={}".format(instance.folder_id)
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
                "%s:%s_%s_change"
                % (
                    self.admin_site.name,
                    obj._meta.app_label,
                    obj._meta.object_name.lower(),
                ),
                args=(obj.pk,),
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
