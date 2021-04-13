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
        # Currently, only supports callables (sufficient for admin_thumbnail
        # and admin_file_name)
        fn = getattr(self.cl.model_admin, self.name)
        result = fn(obj)
        return format_html(
            '<a href="{url}" data-ckeditor-function="{num}">{result}</a>',
            url=obj.file.url,
            num=self.cl.ck_context["CKEditorFuncNum"],
            result=result,
        )

    def __str__(self):
        return self.name
