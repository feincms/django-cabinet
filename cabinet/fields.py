from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.db import models
from django.utils.translation import ugettext_lazy as _

from cabinet.base_admin import folder_choices
from cabinet.models import Folder


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
        context["cabinet"] = {
            "upload_form": UploadForm(prefix="cu-{}".format(id(self)))
        }
        return context


class CabinetForeignKey(models.ForeignKey):
    def formfield(self, **kwargs):
        if isinstance(kwargs["widget"], ForeignKeyRawIdWidget):
            kwargs["widget"].__class__ = CabinetFileRawIdWidget
        return super().formfield(**kwargs)
