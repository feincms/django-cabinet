from cabinet import admin
from cabinet_ckeditor.admin import CKEditorFilebrowserMixin


class FileAdmin(CKEditorFilebrowserMixin, admin.FileAdmin):
    pass


admin.admin.site.unregister(admin.File)
admin.admin.site.register(admin.File, FileAdmin)
