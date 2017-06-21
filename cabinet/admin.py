from collections import defaultdict
from io import BytesIO
from PIL import Image
from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import get_deleted_objects
from django.contrib.admin.views.main import SEARCH_VAR
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import router, transaction
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from cabinet.models import File, Folder


class FolderListFilter(admin.RelatedFieldListFilter):
    """
    Filters are hidden in the file changelist; this filter is only responsible
    for filtering files by folders.
    """
    def has_output(self):
        return True

    def queryset(self, request, queryset):
        if self.used_parameters:
            try:
                return queryset.filter(**self.used_parameters)
            except ValidationError as e:
                raise IncorrectLookupParameters(e)
        elif 'q' in request.GET:
            return queryset
        else:
            return queryset.filter(folder__isnull=True)


def folder_choices():
    """
    Generate folder choices, concatenating all folders with their ancestors'
    names.
    """
    children = defaultdict(list)
    for folder in Folder.objects.all():
        children[folder.parent_id].append(folder)

    yield (None, '-' * 10)

    if not children:
        return

    def iterate(parent_id, ancestors):
        for node in children[parent_id]:
            anc = ancestors + [node.name]
            yield node.id, ' / '.join(anc)
            yield from iterate(node.id, anc)

    yield from iterate(None, [])


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('parent', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].choices = list(folder_choices())
        if self.instance.pk:
            self.fields['_delete_folder'] = forms.BooleanField(
                required=False,
                label=_('Delete this folder'),
            )


class FolderAdminMixin(admin.ModelAdmin):
    def get_urls(self):
        from django.conf.urls import url

        return [
            url(
                r'^folder/add/$',
                self.admin_site.admin_view(self.folder_add),
                name='cabinet_folder_add',
            ),
            url(
                r'^folder/(.+)/$',
                self.admin_site.admin_view(self.folder_change),
                name='cabinet_folder_change',
            ),
        ] + super().get_urls()

    def folder_add(self, request):
        with transaction.atomic(using=router.db_for_write(self.model)):
            return self._folder_form(request, {
                'initial': {
                    'parent': request.GET.get('parent'),
                },
            })

    def folder_change(self, request, object_id):
        with transaction.atomic(using=router.db_for_write(self.model)):
            return self._folder_form(request, {
                'instance': get_object_or_404(Folder, pk=object_id),
            })

    def _folder_form(self, request, kw):
        original = kw.get('instance')
        add = not original

        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied
        else:
            if not self.has_change_permission(request, original):
                raise PermissionDenied

        if request.method == 'POST':
            form = FolderForm(request.POST, **kw)
            if form.is_valid():
                if original and form.cleaned_data.get('_delete_folder'):
                    return self._folder_form_delete(request, original)

                folder = form.save()
                if original:
                    self.message_user(
                        request,
                        _('The folder "%s" was changed successfully.') % (
                            folder,
                        ),
                        messages.SUCCESS)
                    return self.redirect_to_folder(folder.parent_id)

                else:
                    self.message_user(
                        request,
                        _('The folder "%s" was added successfully.') % (
                            folder,
                        ),
                        messages.SUCCESS)
                    return self.redirect_to_folder(folder.id)

        else:
            form = FolderForm(**kw)

        adminForm = helpers.AdminForm(
            form,
            [[None, {'fields': list(form.fields.keys())}]],
            {},
            (),
            model_admin=self)

        response = self.render_change_form(
            request,
            dict(
                self.admin_site.each_context(request),
                title=(
                    _('Add %s') if add else _('Change %s')
                ) % Folder._meta.verbose_name,
                adminform=adminForm,
                object_id=original.pk if original else None,
                original=original,
                is_popup=False,
                media=self.media + adminForm.media,
                errors=helpers.AdminErrorList(form, []),
                preserve_filters=self.get_preserved_filters(request),
            ),
            add=add,
            change=not add,
            form_url='.',
            obj=original,
        )
        response.template_name = [
            'admin/cabinet/folder/change_form.html',
            'admin/change_form.html',
        ]
        return response

    def _folder_form_delete(self, request, obj):
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        using = router.db_for_write(obj.__class__)

        # Populate deleted_objects, a data structure of all related objects
        # that will also be deleted.
        (deleted_objects, model_count, perms_needed, protected) = get_deleted_objects(  # noqa
            [obj], obj._meta, request.user, self.admin_site, using)

        if protected or perms_needed:
            self.message_user(
                request,
                _('Cannot delete %(name)s') % {'name': obj._meta.verbose_name},
                messages.ERROR,
            )

        elif len(deleted_objects) > 1:
            self.message_user(
                request,
                _('Cannot delete %(name)s because of related objects (%(related)s)') % {  # noqa
                    'name': obj._meta.verbose_name,
                    'related': ', '.join(
                        '%s %s' % (count, name)
                        for name, count in model_count.items()
                    ),
                },
                messages.ERROR,
            )

        else:
            obj.delete()
            self.message_user(
                request,
                _('The folder "%s" was deleted successfully.') % obj,
                messages.SUCCESS)

        return self.redirect_to_folder(obj.parent_id)

    def redirect_to_folder(self, folder_id):
        info = self.model._meta.app_label, self.model._meta.model_name
        url = reverse('admin:%s_%s_changelist' % info)
        if folder_id:
            url += '?folder__id__exact=%s' % folder_id
        return HttpResponseRedirect(url)


@admin.register(File)
class FileAdmin(FolderAdminMixin):
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

    def upload_is_image(self, data):
        """
        Determine whether ``data`` is an image or not

        Usage::

            if upload_is_image(request.FILES['file']):
                ...
        """
        # From django/forms/fields.py
        if hasattr(data, 'temporary_file_path'):
            file = data.temporary_file_path()
        else:
            if hasattr(data, 'read'):
                file = BytesIO(data.read())
            else:
                file = BytesIO(data['content'])

        try:
            image = Image.open(file)
            image.verify()
            return True
        except OSError:
            return False

    def upload(self, request):
        f = File(folder_id=request.POST['folder'])
        if self.upload_is_image(request.FILES['file']):
            f.image_file = request.FILES['file']
        else:
            f.download_file = request.FILES['file']
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
