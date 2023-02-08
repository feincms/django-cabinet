from django.contrib import admin
from django.template.defaultfilters import filesizeformat
from django.utils.formats import date_format
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import gettext_lazy as _

from cabinet.base_admin import FileAdminBase
from cabinet.ckeditor import CKEditorFilebrowserMixin
from cabinet.models import File


@admin.register(File)
class FileAdmin(CKEditorFilebrowserMixin, FileAdminBase):
    list_display = ["admin_thumbnail", "admin_file_name", "admin_details"]
    list_display_links = ["admin_thumbnail", "admin_file_name"]

    @admin.display(description="")
    def admin_thumbnail(self, instance):
        if instance.image_file.name:
            try:
                target = instance.image_file.process(["default", ("crop", (50, 50))])
                return format_html(
                    '<img src="{}" alt=""/>', instance.image_file.storage.url(target)
                )
            except Exception:
                return mark_safe('<span class="broken-image"></span>')
        elif instance.download_file.name:
            return format_html(
                '<span class="download download-{}">{}</span>',
                instance.download_type,
                instance.download_type.upper(),
            )
        return ""

    @admin.display(description=_("file name"))
    def admin_file_name(self, instance):
        return format_html(
            "{} <small>({})</small>",
            instance.file_name,
            filesizeformat(instance.file_size),
        )

    @admin.display(description=_("details"))
    def admin_details(self, instance):
        details = [
            instance.caption,
            instance.copyright,
            _("Created %(created_at)s, last modified %(updated_at)s")
            % {
                "created_at": date_format(instance.created_at, "SHORT_DATE_FORMAT"),
                "updated_at": date_format(instance.updated_at, "SHORT_DATE_FORMAT"),
            },
        ]
        return format_html(
            "<small>{}</small>",
            format_html_join(mark_safe("<br>"), "{}", ((d,) for d in details if d)),
        )
