from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.admin.views.main import SEARCH_VAR
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from cabinet.base_admin import (
    FolderAdminMixin, FolderListFilter, IgnoreChangedDataErrorsForm,
    folder_choices,
)
from cabinet.models import File, Folder


@admin.register(File)
class FileAdmin(FolderAdminMixin):
    form = IgnoreChangedDataErrorsForm
    list_display = (
        'admin_thumbnail',
        'admin_file_name',
        'admin_details',
    )
    list_display_links = (
        'admin_thumbnail',
        'admin_file_name',
    )
    list_filter = (
        ('folder', FolderListFilter),
    )
    search_fields = (
        'file_name',
    )

    class Media:
        css = {'all': ('cabinet/cabinet.css',)}
        js = ('cabinet/cabinet.js',)

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

    def get_urls(self):
        from django.conf.urls import url

        return [
            url(
                r'^upload/$',
                self.admin_site.admin_view(self.upload),
                name='cabinet_upload',
            ),
        ] + super().get_urls()

    def folders_annotate_counts(self, folders):
        num_subfolders = dict(
            Folder.objects.order_by().filter(
                parent__in=folders,
            ).values('parent').annotate(
                Count('id'),
            ).values_list('parent', 'id__count'))

        num_files = dict(
            File.objects.order_by().filter(
                folder__in=folders,
            ).values('folder').annotate(
                Count('id'),
            ).values_list('folder', 'id__count'))

        for f in folders:
            f.num_subfolders = num_subfolders.get(f.id, 0)
            f.num_files = num_files.get(f.id, 0)

        return folders

    def changelist_view(self, request):
        cabinet_context = {
            'querystring': urlencode({
                key: value
                for key, value in request.GET.items()
                if key != 'folder__id__exact'
            }),
        }

        folder = None
        folder__id__exact = request.GET.get('folder__id__exact')

        if not request.GET.get(SEARCH_VAR):
            if folder__id__exact:
                try:
                    folder = Folder.objects.get(pk=folder__id__exact)
                except Folder.DoesNotExist:
                    return HttpResponseRedirect('?e=1')

            if folder is None:
                cabinet_context.update({
                    'folder': None,
                    'folder_children': self.folders_annotate_counts(
                        Folder.objects.filter(parent__isnull=True)),
                })
            else:
                cabinet_context.update({
                    'folder': folder,
                    'folder_children': self.folders_annotate_counts(
                        folder.children.all()),
                })

        return super().changelist_view(request, extra_context={
            'cabinet': cabinet_context,
            'title': folder or _('Root folder'),
        })

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'folder':
            field.choices = list(folder_choices())
        return field

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if request.GET.get('folder'):
            folder = get_object_or_404(Folder, pk=request.GET.get('folder'))
            extra_context['cabinet'] = {'folder': folder}
        else:
            folder = None

        response = self.changeform_view(
            request, None, request.get_full_path(), extra_context)

        if response.status_code == 302 and folder:
            response['Location'] += '&folder=%s' % folder.id
        return response

    def upload(self, request):
        f = File(folder_id=request.POST['folder'])
        f.file = request.FILES['file']
        f.save()

        return JsonResponse({
            'success': True,
        })

    def admin_thumbnail(self, instance):
        if instance.image_file.name:
            return format_html(
                '<img src="{}" alt=""/>',
                instance.image_file.crop['50x50'],
            )
        elif instance.download_file.name:
            return format_html(
                '<span class="download download-{}">{}</span>',
                instance.download_type,
                instance.download_type.upper(),
            )
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
