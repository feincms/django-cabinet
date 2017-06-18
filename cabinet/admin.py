from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from cabinet import models


@admin.register(models.Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ('parent',)

    def changelist_view(self, request):
        parent__isnull = request.GET.get('parent__isnull')
        parent__id__exact = request.GET.get('parent__id__exact')
        if not any((parent__isnull, parent__id__exact)):
            return HttpResponseRedirect('?parent__isnull=True')

        if parent__id__exact:
            try:
                folder = models.Folder.objects.get(pk=parent__id__exact)
            except models.Folder.DoesNotExist:
                pass
            else:
                request._cabinet_folder = folder
        return super().changelist_view(request)


class FolderListFilter(admin.RelatedFieldListFilter):
    @property
    def include_empty_choice(self):
        return True


@admin.register(models.File)
class FileAdmin(admin.ModelAdmin):
    list_display = (
        'admin_thumbnail',
        'admin_file_name',
        'admin_details',
    )
    list_display_links = (
        'admin_file_name',
    )
    list_filter = (
        ('folder', FolderListFilter),
    )
    search_fields = (
        'file_name',
    )

    fieldsets = [
        (None, {
            'fields': ('folder',),
        }),
        (_('Image'), {
            'fields': ('image_file',),
        }),
        (_('Download'), {
            'fields': ('download_file',),
        }),
    ]

    def changelist_view(self, request):
        folder__isnull = request.GET.get('folder__isnull')
        folder__id__exact = request.GET.get('folder__id__exact')
        q = request.GET.get('q')
        if not any((folder__isnull, folder__id__exact, q)):
            return HttpResponseRedirect('?folder__isnull=True')

        cabinet_context = {}
        folder = None

        if not q:
            if folder__id__exact:
                try:
                    folder = models.Folder.objects.get(pk=folder__id__exact)
                except models.Folder.DoesNotExist:
                    return HttpResponseRedirect('?folder__isnull=True')

            if folder is None:
                cabinet_context.update({
                    'folder': None,
                    'folder_children': models.Folder.objects.filter(
                        parent__isnull=True,
                    ).annotate(
                        num_subfolders=Count('children'),
                        num_files=Count('files'),
                    ),
                })
            else:
                cabinet_context.update({
                    'folder': folder,
                    'folder_children': folder.children.annotate(
                        num_subfolders=Count('children'),
                        num_files=Count('files'),
                    ),
                })

        return super().changelist_view(request, extra_context={
            'cabinet': cabinet_context,
            'title': folder or _('Root folder'),
        })

    def admin_thumbnail(self, instance):
        if instance.image_file.name:
            return format_html(
                '<img src="{}" alt=""/>',
                instance.image_file.thumbnail['50x50'],
            )
        elif instance.download_file.name:
            return instance.download_type.upper()
        return ''
    admin_thumbnail.short_description = ''

    def admin_file_name(self, instance):
        return instance.file_name
    admin_file_name.short_description = _('file name')

    def admin_details(self, instance):
        return format_html(
            '<small>{}<br>{}</small>',
            filesizeformat(instance.file_size),
            instance.file.name,
        )
    admin_details.short_description = _('details')
