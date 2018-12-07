from collections import defaultdict
from urllib.parse import urlencode

import django
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
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import capfirst
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
        if "q" in request.GET:
            folder = self.used_parameters.get("folder__id__exact")
            if folder:
                return queryset.filter(
                    # Avoid problems because of table aliasses (Django 1.11)
                    folder__in=list(
                        Folder.objects.descendants(
                            folder, include_self=True
                        ).values_list("id", flat=True)
                    )
                )
            return queryset

        if self.used_parameters:
            try:
                return queryset.filter(**self.used_parameters)
            except ValidationError as e:
                raise IncorrectLookupParameters(e)
        else:
            return queryset.none()  # No files in root folder, never.


def folder_choices(include_blank=True):
    """
    Generate folder choices, concatenating all folders with their ancestors'
    names.
    """
    children = defaultdict(list)
    for folder in Folder.objects.all():
        children[folder.parent_id].append(folder)

    if include_blank:
        yield (None, "-" * 10)

    if not children:
        return

    def iterate(parent_id, ancestors):
        for node in children[parent_id]:
            anc = ancestors + [node.name]
            yield node.id, " / ".join(anc)
            yield from iterate(node.id, anc)

    yield from iterate(None, [])


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ("parent", "name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].choices = folder_choices()
        if self.instance.pk:
            self.fields["_delete_folder"] = forms.BooleanField(
                required=False, label=_("Delete this folder")
            )


class SelectFolderForm(forms.Form):
    folder = forms.ModelChoiceField(
        queryset=Folder.objects.all(),
        label=capfirst(_("folder")),
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        files = kwargs.pop("files")
        super().__init__(*args, **kwargs)
        self.fields["folder"].choices = folder_choices(include_blank=False)

        self.fields["files"] = forms.ModelMultipleChoiceField(
            queryset=files,
            label=capfirst(_("files")),
            initial=[f.id for f in files],
            widget=forms.CheckboxSelectMultiple,
        )
        self.fields.move_to_end("files", last=False)


def cabinet_querystring(request):
    return urlencode(
        sorted(
            (key, value)
            for key, value in request.GET.items()
            if key not in {"folder__id__exact", "p"}
        )
    )


class FolderAdminMixin(admin.ModelAdmin):
    def get_urls(self):
        from django.conf.urls import url

        return [
            url(
                r"^folder/add/$",
                self.admin_site.admin_view(self.folder_add),
                name="cabinet_folder_add",
            ),
            url(
                r"^folder/select/$",
                self.admin_site.admin_view(self.folder_select),
                name="cabinet_folder_select",
            ),
            url(
                r"^folder/(.+)/$",
                self.admin_site.admin_view(self.folder_change),
                name="cabinet_folder_change",
            ),
        ] + super().get_urls()

    def folder_add(self, request):
        with transaction.atomic(using=router.db_for_write(self.model)):
            return self._folder_form(
                request, {"initial": {"parent": request.GET.get("parent")}}
            )

    def folder_change(self, request, object_id):
        with transaction.atomic(using=router.db_for_write(self.model)):
            return self._folder_form(
                request, {"instance": get_object_or_404(Folder, pk=object_id)}
            )

    def _folder_form(self, request, kw):
        original = kw.get("instance")
        add = not original

        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied
        else:
            if not self.has_change_permission(request, original):
                raise PermissionDenied

        if request.method == "POST":
            form = FolderForm(request.POST, **kw)
            if form.is_valid():
                if original and form.cleaned_data.get("_delete_folder"):
                    return self._folder_form_delete(request, original)

                folder = form.save()
                if original:
                    self.message_user(
                        request,
                        _('The folder "%s" was changed successfully.') % (folder,),
                        messages.SUCCESS,
                    )
                    return self.redirect_to_folder(request, folder.parent_id)

                else:
                    self.message_user(
                        request,
                        _('The folder "%s" was added successfully.') % (folder,),
                        messages.SUCCESS,
                    )
                    return self.redirect_to_folder(request, folder.id)

        else:
            form = FolderForm(**kw)

        adminForm = helpers.AdminForm(
            form,
            [[None, {"fields": list(form.fields.keys())}]],
            {},
            (),
            model_admin=self,
        )

        response = self.render_change_form(
            request,
            dict(
                self.admin_site.each_context(request),
                title=(_("Add %s") if add else _("Change %s"))
                % Folder._meta.verbose_name,
                adminform=adminForm,
                inline_admin_formsets=[],
                object_id=original.pk if original else None,
                original=original,
                is_popup=False,
                media=self.media + adminForm.media,
                errors=helpers.AdminErrorList(form, []),
                preserve_filters=self.get_preserved_filters(request),
                cabinet={"querystring": cabinet_querystring(request)},
            ),
            add=add,
            change=not add,
            form_url=request.get_full_path(),
            obj=original,
        )
        response.template_name = [
            "admin/cabinet/folder/change_form.html",
            "admin/change_form.html",
        ]
        return response

    def _folder_form_delete(self, request, obj):
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        using = router.db_for_write(obj.__class__)

        # Populate deleted_objects, a data structure of all related objects
        # that will also be deleted.
        if django.VERSION < (2, 1):
            (
                deleted_objects,
                model_count,
                perms_needed,
                protected,
            ) = get_deleted_objects(  # noqa
                [obj], obj._meta, request.user, self.admin_site, using
            )
        else:
            (
                deleted_objects,
                model_count,
                perms_needed,
                protected,
            ) = self.get_deleted_objects(
                [obj], request
            )  # noqa

        if protected or perms_needed:
            self.message_user(
                request,
                _("Cannot delete %(name)s") % {"name": obj._meta.verbose_name},
                messages.ERROR,
            )

        elif len(deleted_objects) > 1:
            self.message_user(
                request,
                _("Cannot delete %(name)s because of related objects (%(related)s)")
                % {  # noqa
                    "name": obj._meta.verbose_name,
                    "related": ", ".join(
                        "%s %s" % (count, name) for name, count in model_count.items()
                    ),
                },
                messages.ERROR,
            )

        else:
            obj.delete()
            self.message_user(
                request,
                _('The folder "%s" was deleted successfully.') % obj,
                messages.SUCCESS,
            )

        return self.redirect_to_folder(request, obj.parent_id)

    def redirect_to_folder(self, request, folder_id):
        info = self.model._meta.app_label, self.model._meta.model_name
        url = reverse("admin:%s_%s_changelist" % info)
        querydict = [
            (key, value)
            for key, value in request.GET.items()
            if key not in {"files", "folder__id__exact", "p", "parent"}
        ]
        if folder_id:
            querydict.append(("folder__id__exact", folder_id))
        return HttpResponseRedirect(
            "%s%s%s" % (url, "?" if querydict else "", urlencode(sorted(querydict)))
        )

    def move_to_folder(self, request, queryset):
        return HttpResponseRedirect(
            "%s?%s"
            % (
                reverse("admin:cabinet_folder_select"),
                urlencode(sorted(("files", item.id) for item in queryset)),
            )
        )

    move_to_folder.short_description = _("Move files to folder")

    def folder_select(self, request):
        files = self.model.objects.filter(
            pk__in=(request.POST.getlist("files") or request.GET.getlist("files"))
        )

        form = SelectFolderForm(
            request.POST if request.method == "POST" else None, files=files
        )

        if form.is_valid():
            folder = form.cleaned_data["folder"]
            form.cleaned_data["files"].update(folder=folder)
            self.message_user(request, _("The files have been successfully moved."))
            return self.redirect_to_folder(request, folder.id)

        adminForm = helpers.AdminForm(
            form,
            [[None, {"fields": list(form.fields.keys())}]],
            {},
            (),
            model_admin=self,
        )

        response = self.render_change_form(
            request,
            dict(
                self.admin_site.each_context(request),
                title=_("Move files to folder"),
                adminform=adminForm,
                inline_admin_formsets=[],
                object_id=None,
                original=None,
                is_popup=False,
                media=self.media + adminForm.media,
                errors=helpers.AdminErrorList(form, []),
                preserve_filters=self.get_preserved_filters(request),
                cabinet={"querystring": cabinet_querystring(request)},
            ),
            add=False,
            change=False,
            form_url=request.get_full_path(),
            obj=None,
        )
        response.template_name = [
            "admin/cabinet/folder/change_form.html",
            "admin/change_form.html",
        ]
        return response


class IgnoreChangedDataErrorsForm(forms.ModelForm):
    """
    Ignore ``OSError`` exceptions when listing changed fields.

    Admin's construct_change_message runs after OverwriteMixin.save()
    and crashes when files are already gone. Simply ignore this;
    it makes admin log messages look less nice than they should, but
    we do not care too much.
    """

    @cached_property
    def changed_data(self):
        try:
            return super().changed_data
        except OSError:
            return []


class FileAdminBase(FolderAdminMixin):
    actions = ["move_to_folder"]
    form = IgnoreChangedDataErrorsForm
    list_filter = (("folder", FolderListFilter),)
    search_fields = ("file_name",)

    class Media:
        css = {"all": ("cabinet/cabinet.css",)}
        js = ("cabinet/cabinet.js",)

    def get_urls(self):
        from django.conf.urls import url

        return [
            url(
                r"^upload/$",
                self.admin_site.admin_view(self.upload),
                name="cabinet_upload",
            )
        ] + super().get_urls()

    def folders_annotate_counts(self, folders):
        """
        Add direct subfolders and files counts to an iterable of folders

        Recursive traversal and summation isn't implemented as adjacency
        list-based tree traversal without common table expressions is
        expensive. We want to stay compatible even with stupid database
        engines!
        """
        num_subfolders = dict(
            Folder.objects.order_by()
            .filter(parent__in=folders)
            .values("parent")
            .annotate(Count("id"))
            .values_list("parent", "id__count")
        )

        num_files = dict(
            self.model._default_manager.order_by()
            .filter(folder__in=folders)
            .values("folder")
            .annotate(Count("id"))
            .values_list("folder", "id__count")
        )

        for f in folders:
            f.num_subfolders = num_subfolders.get(f.id, 0)
            f.num_files = num_files.get(f.id, 0)

        return folders

    def changelist_view(self, request):
        cabinet_context = {
            # Keep query params except those in the set below when changing
            # folders
            "querystring": cabinet_querystring(request)
        }

        folder = None

        # Never filter by folder if searching
        if not request.GET.get(SEARCH_VAR):
            folder__id__exact = request.GET.get("folder__id__exact")
            if folder__id__exact:
                try:
                    folder = Folder.objects.get(pk=folder__id__exact)
                except Folder.DoesNotExist:
                    return HttpResponseRedirect("?e=1")

            if folder is None:
                cabinet_context.update(
                    {
                        "folder": None,
                        "folder_children": self.folders_annotate_counts(
                            Folder.objects.filter(parent__isnull=True)
                        ),
                    }
                )
            else:
                cabinet_context.update(
                    {
                        "folder": folder,
                        "folder_children": self.folders_annotate_counts(
                            folder.children.all()
                        ),
                    }
                )

        return super().changelist_view(
            request,
            extra_context={
                "cabinet": cabinet_context,
                "title": folder or _("Root folder"),
            },
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "folder":
            field.choices = list(folder_choices())
        return field

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if request.GET.get("folder"):
            folder = get_object_or_404(Folder, pk=request.GET.get("folder"))
            extra_context["cabinet"] = {"folder": folder}
        else:
            folder = None

        response = self.changeform_view(
            request, None, request.get_full_path(), extra_context
        )

        # Keep the folder preset when redirecting. This sometimes adds the
        # folder variable twice (once to preserved_filters and once separately
        # but this is at most ugly and not a real problem)
        if response.status_code == 302 and folder:
            response["Location"] += "&folder=%s" % folder.id
        return response

    def upload(self, request):
        f = self.model(folder_id=request.POST["folder"])
        f.file = request.FILES["file"]
        f.save()

        return JsonResponse({"success": True})
