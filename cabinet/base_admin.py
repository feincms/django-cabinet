from collections import defaultdict

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import get_deleted_objects
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import router, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from cabinet.models import Folder


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


class IgnoreChangedDataErrorsForm(forms.ModelForm):
    @cached_property
    def changed_data(self):
        # Admin's construct_change_message does not like it if files are
        # already gone. Whatever...
        try:
            return super().changed_data
        except OSError:
            return []
