from urllib.parse import urlencode

import django
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import SEARCH_VAR
from django.core.exceptions import FieldDoesNotExist, PermissionDenied, ValidationError
from django.db import router, transaction
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path, re_path, reverse
from django.utils.functional import cached_property
from django.utils.html import escape, mark_safe
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from tree_queries.forms import TreeNodeChoiceField

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
            if folder_id := self.used_parameters.get("folder__id__exact"):
                if django.VERSION > (5,):
                    folder_id = folder_id[0]
                return queryset.filter(
                    # Avoid problems because of table aliasses (Django 1.11)
                    folder__in=list(
                        Folder.objects.descendants(
                            folder_id, include_self=True
                        ).values_list("id", flat=True)
                    )
                )
            return queryset

        if folder_id := self.used_parameters.get("folder__id__exact"):
            if django.VERSION > (5,):
                folder_id = folder_id[0]
            try:
                return queryset.filter(folder=folder_id)
            except ValidationError as e:
                raise IncorrectLookupParameters(e) from e
        else:
            return queryset.none()  # No files in root folder, never.


class FileTypeFilter(admin.SimpleListFilter):
    parameter_name = "file_type"
    title = _("file type")

    def lookups(self, request, model_admin):
        return [
            (row["file_field"], row["verbose_name"])
            for row in model_admin.model._file_mixin_fieldsets
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.exclude(**{self.value(): ""})
        return queryset


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ("parent", "name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["_delete_folder"] = forms.BooleanField(
                required=False,
                label=_("Delete this folder"),
                help_text=_("The folder will not be deleted if it contains files."),
            )


class SelectFolderForm(forms.Form):
    folder = TreeNodeChoiceField(
        queryset=Folder.objects.all(),
        label=capfirst(_("folder")),
        widget=forms.RadioSelect,
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        files = kwargs.pop("files")
        super().__init__(*args, **kwargs)

        self.fields["files"] = forms.ModelMultipleChoiceField(
            queryset=files,
            label=capfirst(_("files")),
            initial=[f.id for f in files],
            widget=forms.CheckboxSelectMultiple,
        )
        self.order_fields(["files", "folder"])


def cabinet_querystring(request, **kwargs):
    values = {
        key: value
        for key, value in request.GET.items()
        if key not in {"folder__id__exact", "p"}
    }
    values.update(kwargs)
    return urlencode(sorted(values.items()))


class FolderAdminMixin(admin.ModelAdmin):
    def get_urls(self):
        return [
            path(
                "folder/add/",
                self.admin_site.admin_view(self.folder_add),
                name="cabinet_folder_add",
            ),
            path(
                "folder/select/",
                self.admin_site.admin_view(self.folder_select),
                name="cabinet_folder_select",
            ),
            re_path(
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

        admin_form = helpers.AdminForm(
            form,
            [[None, {"fields": list(form.fields.keys())}]],
            {},
            (),
            model_admin=self,
        )

        # render_change_form sets request.current_app
        response = self.render_change_form(
            request,
            dict(
                self.admin_site.each_context(request),
                title=(_("Add %s") if add else _("Change %s"))
                % Folder._meta.verbose_name,
                adminform=admin_form,
                inline_admin_formsets=[],
                object_id=original.pk if original else None,
                original=original,
                is_popup=False,
                media=self.media + admin_form.media,
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

        # Populate deleted_objects, a data structure of all related objects
        # that will also be deleted.
        (
            deleted_objects,
            model_count,
            perms_needed,
            protected,
        ) = self.get_deleted_objects([obj], request)

        if perms_needed:
            self.message_user(
                request,
                _(
                    "You do not have the necessary permissions to delete the %(type)s '%(name)s'"
                )
                % {
                    "type": obj._meta.verbose_name,
                    "name": obj,
                },
                messages.ERROR,
            )

        elif protected:
            related = ", ".join(protected[:10])
            if len(protected) > 10:
                related += ", ..."

            self.message_user(
                request,
                mark_safe(
                    escape(
                        _(
                            "Cannot delete the %(type)s '%(name)s' because it is protected by related objects: %(related)s"
                        )
                    )
                    % {
                        "type": escape(obj._meta.verbose_name),
                        "name": escape(obj),
                        "related": ", ".join(protected),
                    }
                ),
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
        url = reverse(
            "admin:{}_{}_changelist".format(*info), current_app=self.admin_site.name
        )
        querydict = [
            (key, value)
            for key, value in request.GET.items()
            if key not in {"files", "folder__id__exact", "p", "parent"}
        ]
        if folder_id:
            querydict.append(("folder__id__exact", folder_id))
        return HttpResponseRedirect(
            "{}{}{}".format(url, "?" if querydict else "", urlencode(sorted(querydict)))
        )

    @admin.action(description=_("Move files to folder"))
    def move_to_folder(self, request, queryset):
        return HttpResponseRedirect(
            "{}?{}".format(
                reverse(
                    "admin:cabinet_folder_select", current_app=self.admin_site.name
                ),
                urlencode(sorted(("files", item.id) for item in queryset)),
            )
        )

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

        admin_form = helpers.AdminForm(
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
                adminform=admin_form,
                inline_admin_formsets=[],
                object_id=None,
                original=None,
                is_popup=False,
                media=self.media + admin_form.media,
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


class UploadForm(forms.Form):
    folder = forms.ModelChoiceField(queryset=Folder.objects.all())
    file = forms.FileField()


class FileAdminBase(FolderAdminMixin):
    actions = ["move_to_folder"]
    form = IgnoreChangedDataErrorsForm
    list_filter = [("folder", FolderListFilter), FileTypeFilter]
    search_fields = ("file_name",)

    # Useful when swapping the file model
    change_form_template = "admin/cabinet/file/change_form.html"
    change_list_template = "admin/cabinet/file/change_list.html"

    class Media:
        css = {"all": ("cabinet/cabinet.css",)}
        js = ["admin/js/jquery.init.js", "cabinet/cabinet.js"]

    def get_urls(self):
        return [
            path(
                "upload/",
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

    def changelist_view(self, request, extra_context=None):
        folder__id__exact = request.GET.get("folder__id__exact")
        if folder__id__exact == "last":
            kw = {}
            if request.COOKIES.get("cabinet_folder"):
                kw["folder__id__exact"] = request.COOKIES["cabinet_folder"]
            return HttpResponseRedirect(f"?{cabinet_querystring(request, **kw)}")

        cabinet_context = {
            # Keep query params except those in the set below when changing
            # folders
            "querystring": cabinet_querystring(request)
        }

        folder = None

        # Never filter by folder if searching
        if not request.GET.get(SEARCH_VAR):
            if folder__id__exact:
                try:
                    folder = Folder.objects.get(pk=folder__id__exact)
                except (Folder.DoesNotExist, ValueError):
                    return HttpResponseRedirect("?e=1")

            cabinet_context.update(
                {
                    "folder": folder,
                    "folder_children": self.folders_annotate_counts(
                        Folder.objects.filter(parent=folder)
                    ),
                }
            )

        extra_context_cabinet = {
            "cabinet": cabinet_context,
            "title": folder or _("Root folder"),
        }
        if extra_context:
            extra_context_cabinet.update(extra_context)
        response = super().changelist_view(
            request,
            extra_context=extra_context_cabinet,
        )
        response.set_cookie("cabinet_folder", folder.pk if folder else "")
        return response

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if request.GET.get("folder"):
            extra_context["cabinet"] = {
                "folder": Folder.objects.filter(pk=request.GET["folder"]).first()
            }

        return self.changeform_view(
            request, None, request.get_full_path(), extra_context
        )

    def _add_folder_if_redirect(self, response, folder_id):
        # Keep the folder preset when redirecting. This sometimes adds the
        # folder variable twice (once to preserved_filters and once separately
        # but this is at most ugly and not a real problem)
        if response.status_code == 302 and folder_id:
            response["Location"] += "{}folder__id__exact={}".format(
                "&" if "?" in response["Location"] else "?", folder_id
            )
        return response

    def response_add(self, request, obj, *args, **kwargs):
        return self._add_folder_if_redirect(
            super().response_add(request, obj, *args, **kwargs), obj.folder_id
        )

    def response_change(self, request, obj, *args, **kwargs):
        return self._add_folder_if_redirect(
            super().response_change(request, obj, *args, **kwargs), obj.folder_id
        )

    def upload(self, request):
        if request.method != "POST":
            return self.redirect_to_folder(request, None)
        form = UploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({"success": False}, status=400)

        f = self.model(folder=form.cleaned_data["folder"])
        f.file = form.cleaned_data["file"]
        f.save()

        return JsonResponse({"success": True, "pk": f.pk, "name": str(f)})

    top_fields = ["folder", "caption", "copyright"]
    advanced_fields = ["_overwrite"]

    def get_fieldsets(self, request, obj=None):
        def exists(field):
            try:
                self.model._meta.get_field(field)
            except FieldDoesNotExist:
                return False
            return True

        fieldsets = [
            (None, {"fields": [field for field in self.top_fields if exists(field)]})
        ]
        for row in self.model._file_mixin_fieldsets:
            if getattr(obj, row["file_field"], None):
                fieldsets[0][1]["fields"].extend(row["fields"])
            else:
                fieldsets.append(
                    (
                        row["verbose_name"],
                        {
                            "fields": row["fields"],
                            "classes": ["collapse"] if obj else [],
                        },
                    )
                )

        advanced = [field for field in self.advanced_fields if exists(field)]
        if advanced:
            fieldsets.append((_("Advanced"), {"fields": advanced}))
        return fieldsets
