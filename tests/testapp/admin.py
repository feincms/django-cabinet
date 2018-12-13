from cabinet import admin, ckeditor


class FileAdmin(ckeditor.CKEditorFilebrowserMixin, admin.FileAdmin):
    pass


admin.admin.site.unregister(admin.File)
admin.admin.site.register(admin.File, FileAdmin)
