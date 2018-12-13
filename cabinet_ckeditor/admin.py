from django.contrib import admin
from django.contrib.admin.utils import (
    display_for_field,
    display_for_value,
    lookup_field,
)
from django.contrib.admin.views.main import ChangeList, EMPTY_CHANGELIST_VALUE
from django.db.models import ObjectDoesNotExist
from django.utils.html import format_html


# FIXME Remove inline JS again.
TEMPLATE = """\
<a href="{url}" onclick="\
opener.CKEDITOR.tools.callFunction({num}, this.getAttribute(\'href\'));\
window.close();return false">{result}</a>
"""


class CKEditorFilebrowserMixin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        if request.GET.get("CKEditorFuncNum"):
            return CKFileBrowserChangeList
        return ChangeList


class CKFileBrowserChangeList(ChangeList):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.list_display = [
            Link(self, field) if field in self.list_display_links else field
            for field in self.list_display
        ]
        self.list_display_links = None

    def get_filters_params(self, params=None):
        params = super().get_filters_params(params)
        self.ck_context = {
            "CKEditor": params.pop("CKEditor"),
            "CKEditorFuncNum": params.pop("CKEditorFuncNum"),
            "langCode": params.pop("langCode"),
        }
        return params


class Link(object):
    def __init__(self, cl, name):
        self.cl = cl
        self.name = name
        self.__name__ = name

    def __call__(self, obj):
        try:
            f, attr, value = lookup_field(self.name, obj, self.cl.model_admin)
        except ObjectDoesNotExist:
            result_repr = EMPTY_CHANGELIST_VALUE
        else:
            if f is None or f.auto_created:
                result_repr = display_for_value(value, False)
            else:
                result_repr = display_for_field(value, f)

        return format_html(
            TEMPLATE,
            url=obj.file.url,
            num=self.cl.ck_context["CKEditorFuncNum"],
            result=result_repr,
        )

    def __str__(self):
        return self.name
