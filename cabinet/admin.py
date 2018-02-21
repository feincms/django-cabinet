from django.contrib import admin
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from cabinet.base_admin import FileAdminBase
from cabinet.models import File


@admin.register(File)
class FileAdmin(FileAdminBase):
    list_display = (
        'admin_thumbnail',
        'admin_file_name',
        'admin_details',
    )
    list_display_links = (
        'admin_thumbnail',
        'admin_file_name',
    )

    def get_fieldsets(self, request, obj=None):
        return [
            (None, {
                'fields': [field for field in (
                    'folder',
                    'caption',
                    'copyright',
                    '_overwrite' if obj else '',
                ) if field],
            }),
            (_('Image'), {
                'fields': ('image_file', 'image_alt_text'),
                'classes': (
                    ('collapse',)
                    if (obj and not obj.image_file.name)
                    else ()
                ),
            }),
            (_('Download'), {
                'fields': ('download_file',),
                'classes': (
                    ('collapse',)
                    if (obj and not obj.download_file.name)
                    else ()
                ),
            }),
        ]

    def admin_thumbnail(self, instance):
        if instance.image_file.name:
            try:
                return format_html(
                    '<img src="{}" alt=""/>',
                    instance.image_file.crop['50x50'],
                )
            except Exception:
                return format_html('<span class="broken-image"></span>')
        elif instance.download_file.name:
            return format_html(
                '<span class="download download-{}">{}</span>',
                instance.download_type,
                instance.download_type.upper(),
            )
        return ''
    admin_thumbnail.short_description = ''

    def admin_file_name(self, instance):
        return format_html(
            '{} <small>({})</small>',
            instance.file_name,
            filesizeformat(instance.file_size),
        )
    admin_file_name.short_description = _('file name')

    def admin_details(self, instance):
        return format_html(
            '<small>{}<br>{}</small>',
            instance.caption,
            instance.copyright,
        )
    admin_details.short_description = _('details')
