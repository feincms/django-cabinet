import json

import django
from django import forms
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.utils.html import format_html


class CKEditorFilebrowserMixin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        if request.GET.get("CKEditorFuncNum"):
            return CKFileBrowserChangeList
        return ChangeList

    @property
    def media(self):
        return super().media + forms.Media(
            js=["admin/js/jquery.init.js", "cabinet/ckeditor.js"]
        )


def _extract(value):
    return value[0] if value and django.VERSION > (5,) else value


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
            "CKEditorFuncNum": _extract(params.pop("CKEditorFuncNum")),
            "CKEditor": _extract(params.pop("CKEditor", None)),
            "langCode": _extract(params.pop("langCode", None)),
        }
        return params


class Link:
    def __init__(self, cl, name):
        self.cl = cl
        self.name = name
        self.__name__ = name

    def __call__(self, obj):
        # Currently, only supports callables (sufficient for admin_thumbnail
        # and admin_file_name)
        fn = getattr(self.cl.model_admin, self.name)
        result = fn(obj)

        # We can pass additional data as a third argument. When it is neither a
        # function nor a string it will be ignored by CKEditor 4's filebrowser
        # plugin:
        # https://github.com/ckeditor/ckeditor4/blob/c7e59ec199298b6b23f4aa7a7668f18572385bac/plugins/filebrowser/plugin.js#L413
        return format_html(
            '<a href="{url}" data-ckeditor-function="{num}" data-ckeditor-data="{data}">{result}</a>',
            url=obj.file.url,
            num=self.cl.ck_context["CKEditorFuncNum"],
            data=json.dumps(
                {
                    "alternative_text": getattr(obj, "image_alt_text", ""),
                    "caption": getattr(obj, "caption", ""),
                    "copyright": getattr(obj, "copyright", ""),
                }
            ),
            result=result,
        )

    def __str__(self):
        return self.name
