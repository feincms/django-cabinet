import io
import itertools
import json
import os
import shutil

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import ContentFile
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from cabinet.base import AbstractFile, DownloadMixin, determine_accept_file_functions
from cabinet.models import File, Folder, get_file_model
from testapp.models import Stuff


class CabinetTestCase(TestCase):
    def setUp(self):
        self.user = User(username="test", is_staff=True, is_superuser=True)
        self.user.set_password("test")
        self.user.save()
        self.image1_path = os.path.join(settings.BASE_DIR, "image.png")
        self.image2_path = os.path.join(settings.BASE_DIR, "image-neg.png")
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)

    def login(self):
        client = Client()
        client.login(username="test", password="test")
        return client

    def assertNoMediaFiles(self):  # noqa: N802
        File.objects.all().delete()
        files = list(
            itertools.chain.from_iterable(i[2] for i in os.walk(settings.MEDIA_ROOT))
        )
        self.assertEqual(files, [])

    def test_cabinet_folders(self):
        c = self.login()

        response = c.get("/admin/cabinet/file/")
        self.assertContains(
            response, '<script type="text/template" id="cabinet-result-list">', 1
        )
        self.assertContains(
            response, '<script type="text/template" id="cabinet-folder-list">', 1
        )
        self.assertContains(
            response,
            """
<a href="/admin/cabinet/file/folder/add/?&amp;parent=" class="addlink">
    Add folder
</a>
            """,
            html=True,
        )
        self.assertNotContains(response, "Add file")

        response = c.get("/admin/cabinet/file/folder/add/")
        self.assertContains(response, "Add folder")
        self.assertNotContains(response, "_delete_folder")

        response = c.post("/admin/cabinet/file/folder/add/", {"name": "Test 1"})
        folder = Folder.objects.get()
        self.assertRedirects(
            response, "/admin/cabinet/file/?folder__id__exact=%s" % folder.id
        )

        response = c.get("/admin/cabinet/file/folder/%s/" % folder.id)
        self.assertContains(response, "_delete_folder")

        file = File(folder=folder)
        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content)

        response = c.post(
            "/admin/cabinet/file/folder/%s/" % folder.id,
            {"name": folder.name, "_delete_folder": True},
        )
        self.assertRedirects(response, "/admin/cabinet/file/")
        self.assertEqual(Folder.objects.count(), 1)  # not deleted

        file.delete()

        # Create a subfolder, but deleting should succeed anyway
        Folder.objects.create(parent=folder, name="Anything")

        response = c.post(
            "/admin/cabinet/file/folder/%s/" % folder.id,
            {"name": folder.name, "_delete_folder": True},
        )

        self.assertRedirects(response, "/admin/cabinet/file/")
        self.assertEqual(Folder.objects.count(), 0)

        self.assertNoMediaFiles()

    def test_upload(self):
        folder = Folder.objects.create(name="Test")
        c = self.login()

        response = c.get("/admin/cabinet/file/upload/")
        self.assertRedirects(response, "/admin/cabinet/file/")

        response = c.post("/admin/cabinet/file/upload/", {})
        self.assertEqual(response.status_code, 400)

        with open(self.image1_path, "rb") as image:
            response = c.post(
                "/admin/cabinet/file/add/",
                {"folder": folder.id, "image_file": image, "image_ppoi": "0.5x0.5"},
            )

        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )

        response = c.get("/admin/cabinet/file/?folder__id__exact=%s" % folder.id)

        self.assertContains(response, ">image.png <small>(4.9 KB)</small><", 1)
        self.assertContains(response, """../</a>""")
        self.assertContains(response, '<p class="paginator"> 1 file </p>', html=True)

        response = c.get("/admin/cabinet/file/")
        self.assertContains(
            response, '<a href="?&amp;folder__id__exact=%s">Test</a>' % folder.id
        )
        self.assertContains(response, '<p class="paginator"> 0 files </p>', html=True)

        f1 = File.objects.get()
        f1_name = f1.file.name
        f1_bytes = f1.file.read()

        self.assertEqual(
            [getattr(f1, field).name for field in f1.FILE_FIELDS], [f1_name, ""]
        )
        self.assertEqual(f1.download_type, "")

        with open(self.image1_path, "rb") as image:
            response = c.post(
                reverse("admin:cabinet_file_change", args=(f1.id,)),
                {"folder": folder.id, "image_file": image, "image_ppoi": "0.5x0.5"},
            )

        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )

        f2 = File.objects.get()
        f2_name = f2.file.name
        f2_bytes = f2.file.read()

        self.assertNotEqual(f1_name, f2_name)
        self.assertEqual(f1_bytes, f2_bytes)

        with open(self.image2_path, "rb") as image:
            response = c.post(
                reverse("admin:cabinet_file_change", args=(f1.id,)),
                {
                    "folder": folder.id,
                    "image_file": image,
                    "image_ppoi": "0.5x0.5",
                    "_overwrite": True,
                },
            )

        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )

        f3 = File.objects.get()
        f3_name = f3.file.name
        f3_bytes = f3.file.read()

        self.assertEqual(f2_name, f3_name)
        self.assertNotEqual(f2_bytes, f3_bytes)

        # Top level search
        response = c.get("/admin/cabinet/file/?q=image")
        self.assertContains(response, '<p class="paginator"> 1 file </p>', html=True)

        # Folder with file inside
        response = c.get(f"/admin/cabinet/file/?folder__id__exact={folder.pk}&q=image")
        self.assertContains(response, '<p class="paginator"> 1 file </p>', html=True)

        # Other folder
        f2 = Folder.objects.create(name="Second")
        response = c.get(f"/admin/cabinet/file/?folder__id__exact={f2.pk}&q=image")
        self.assertContains(response, '<p class="paginator"> 0 files </p>', html=True)

        subfolder = Folder.objects.create(parent=folder, name="sub")
        f = File.objects.get()

        response = c.get(f"/admin/cabinet/file/folder/select/?files={f.pk}")
        self.assertContains(response, 'id="id_files_0"')
        self.assertContains(response, 'id="id_folder_0"')
        self.assertListEqual(
            list(response.context["adminform"].form.fields.keys()), ["files", "folder"]
        )

        response = c.post(
            "/admin/cabinet/file/folder/select/",
            {"files": f.pk, "folder": subfolder.pk},
        )
        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={subfolder.pk}"
        )

        # f.folder = subfolder
        # f.save()

        # File is in a subfolder now
        response = c.get(f"/admin/cabinet/file/?folder__id__exact={folder.pk}")
        self.assertContains(response, '<p class="paginator"> 0 files </p>', html=True)

        # But can be found by searching
        response = c.get(f"/admin/cabinet/file/?folder__id__exact={folder.pk}&q=image")
        self.assertContains(response, '<p class="paginator"> 1 file </p>', html=True)

        response = c.get(
            f"/admin/cabinet/file/?folder__id__exact={folder.pk}&file_type=image_file"
        )
        self.assertContains(response, '<p class="paginator"> 0 files </p>', html=True)

        self.assertNoMediaFiles()

    def test_stuff(self):
        self.assertEqual(Folder.objects.count(), 0)
        self.assertEqual(File.objects.count(), 0)

    def test_dnd_upload(self):
        c = self.login()
        f = Folder.objects.create(name="Test")
        with io.BytesIO(b"invalid") as file:
            file.name = "image.jpg"  # but is not
            response = c.post(
                "/admin/cabinet/file/upload/", {"folder": f.id, "file": file}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["success"], True)

        with open(self.image1_path, "rb") as image:
            response = c.post(
                "/admin/cabinet/file/upload/", {"folder": f.id, "file": image}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["success"], True)

        response = c.get("/admin/cabinet/file/?folder__id__exact=%s" % f.id)

        self.assertContains(response, '<p class="paginator"> 2 files </p>', html=True)
        self.assertContains(
            response,
            # One valid image and a file with an image-like extension
            '<span class="download download-image">',
            1,
        )
        self.assertContains(response, '<img src="/media/__processed__/', 1)

        self.assertNoMediaFiles()

    def test_raw_id_fields(self):
        c = self.login()
        response = c.get("/admin/cabinet/file/?_to_field=id&_popup=1")
        self.assertContains(
            response,
            """
<a href="/admin/cabinet/file/folder/add/?_popup=1&amp;_to_field=id&amp;parent="
    class="addlink">
  Add folder
</a>
            """,
            html=True,
        )

        response = c.post(
            "/admin/cabinet/file/folder/add/?_popup=1&_to_field=id", {"name": "Test"}
        )
        f = Folder.objects.get()
        files_url = (
            "/admin/cabinet/file/?_popup=1&_to_field=id&folder__id__exact=%s" % f.id
        )
        self.assertRedirects(response, files_url)

        response = c.get(files_url)
        self.assertContains(
            response,
            '<a href="?_popup=1&amp;_to_field=id"><span class="folder"></span></a>',
        )
        # We do not need to test adding files -- that's covered by Django.

    def test_get_file_model(self):
        self.assertEqual(settings.CABINET_FILE_MODEL, "cabinet.File")
        self.assertEqual(get_file_model(), File)

        with override_settings(CABINET_FILE_MODEL="bla"):
            self.assertRaises(ImproperlyConfigured, get_file_model)

        with override_settings(CABINET_FILE_MODEL="stuff.stuff"):
            self.assertRaises(ImproperlyConfigured, get_file_model)

    def test_ckeditor_filebrowser(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)
        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content)

        client = self.login()
        response = client.get(
            f"/admin/cabinet/file/?_popup=1&CKEditor=editor&CKEditorFuncNum=1&langCode=en&folder__id__exact={folder.pk}"
        )
        self.assertContains(response, "data-ckeditor-function", 2)  # Icon and name

    def test_editing(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)
        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content)

        c = self.login()
        response = c.post(
            reverse("admin:cabinet_file_change", args=(file.id,)),
            {
                "folder": folder.id,
                "caption": "Hello world",
                "image_ppoi": file.image_ppoi,
                "download_file": "",
                "image_file": "",
            },
        )
        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )

    def test_overwrite_without_new(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)
        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content)

        c = self.login()
        response = c.post(
            reverse("admin:cabinet_file_change", args=(file.id,)),
            {
                "folder": folder.id,
                "caption": "Hello world",
                "image_ppoi": file.image_ppoi,
                "download_file": "",
                "image_file": "",
                "_overwrite": "on",
            },
        )
        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )

        file.refresh_from_db()
        self.assertFalse(file._overwrite)

    def test_invalid_folder(self):
        c = self.login()
        response = c.get("/admin/cabinet/file/?folder__id__exact=anything")
        self.assertRedirects(response, "/admin/cabinet/file/?e=1")

    def test_cabinet_foreign_key(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)
        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content)

        c = self.login()
        response = c.get("/admin/testapp/stuff/add/")

        self.assertContains(
            response,
            'href="/admin/cabinet/file/?_to_field=id&amp;folder__id__exact=last"',
        )

        stuff = Stuff.objects.create(title="Test", file=file)
        response = c.get(reverse("admin:testapp_stuff_change", args=(stuff.id,)))

        self.assertContains(
            response,
            f'href="/admin/cabinet/file/?_to_field=id&amp;folder__id__exact={folder.id}"',
        )

        filefield = Stuff._meta.get_field("file")
        formfield = filefield.formfield()
        self.assertTrue(isinstance(formfield.widget, forms.Select))

        name, path, args, kwargs = filefield.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")

    def test_two_files(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)
        with open(self.image1_path, "rb") as image:
            file.image_file.save("hello.jpg", ContentFile(image.read()))

        file.full_clean()  # Everything well

        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content, save=False)
        with self.assertRaises(ValidationError):
            file.full_clean()

    def test_file_add_folder_preselect(self):
        folder = Folder.objects.create(name="Root")
        c = self.login()

        response = c.get("/admin/cabinet/file/add/")
        self.assertContains(response, '<option value="" selected>------')

        response = c.get(f"/admin/cabinet/file/add/?folder={folder.id}")
        self.assertContains(
            response, f'<option value="{folder.id}" selected>Root</option>'
        )

    def test_folder_duplicate(self):
        folder = Folder.objects.create(name="Root")
        folder.full_clean()  # Cleaning self works.
        with self.assertRaises(ValidationError):
            Folder(name="Root").full_clean()

    def test_invalid_files_no_admin_crash(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)

        with open(self.image1_path, "rb") as image:
            image1_bytes = image.read()

        file.image_file.save("image.png", ContentFile(image1_bytes))
        with open(file.image_file.path, "wb") as f:
            f.write(image1_bytes[:500])

        File(folder=folder, file_size=0).save_base()  # No file at all

        c = self.login()
        response = c.get(f"/admin/cabinet/file/?folder__id__exact={folder.id}")
        self.assertContains(response, '<span class="broken-image"></span>', 1)

    def test_large_upload(self):
        c = self.login()
        f = Folder.objects.create(name="Test")
        # Big enough for Django to create a temporary file
        with io.BytesIO(b"0123456789" * 1024 * 1024) as file:
            file.name = "blob.txt"
            response = c.post(
                "/admin/cabinet/file/upload/", {"folder": f.id, "file": file}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["success"], True)

    def test_folder_editing(self):
        parent = Folder.objects.create(name="Root")
        folder = Folder.objects.create(name="Test", parent=parent)

        c = self.login()
        response = c.post(
            f"/admin/cabinet/file/folder/{folder.id}/",
            {"name": folder.name, "parent": parent.id},
        )
        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={parent.id}"
        )

    def test_last_folder(self):
        folder = Folder.objects.create(name="Root")

        c = self.login()
        response = c.get("/admin/cabinet/file/?_popup=1&folder__id__exact=last")
        self.assertRedirects(response, "/admin/cabinet/file/?_popup=1")

        c.get(f"/admin/cabinet/file/?folder__id__exact={folder.id}")
        response = c.get("/admin/cabinet/file/?folder__id__exact=last")
        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )
        self.assertEqual(c.cookies["cabinet_folder"].value, str(folder.id))

        response = c.get("/admin/cabinet/file/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(c.cookies["cabinet_folder"].value, "")

    def test_change_type(self):
        folder = Folder.objects.create(name="Test")
        c = self.login()

        with open(self.image1_path, "rb") as image:
            response = c.post(
                "/admin/cabinet/file/add/",
                {"folder": folder.id, "image_file": image, "image_ppoi": "0.5x0.5"},
            )

        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )

        f1 = File.objects.get()
        self.assertEqual(f1.download_file, "")

        with open(self.image1_path, "rb") as image:
            response = c.post(
                reverse("admin:cabinet_file_change", args=(f1.id,)),
                {
                    "folder": folder.id,
                    "image_file-clear": True,
                    "image_ppoi": "0.5x0.5",
                    "download_file": image,
                },
            )

        self.assertRedirects(
            response, f"/admin/cabinet/file/?folder__id__exact={folder.id}"
        )

        f1 = File.objects.get()
        self.assertEqual(f1.image_file, "")

    def test_custom_file(self):
        class NonModelMixin:
            pass

        class CustomFile(AbstractFile, NonModelMixin, DownloadMixin):
            FILE_FIELDS = ["download_file"]

        # Shouldn't crash (did choke on the mixin before #9)
        determine_accept_file_functions(CustomFile)

        self.assertEqual(
            CustomFile._accept_file_functions,
            [DownloadMixin.accept_file],
        )

        self.assertEqual(
            CustomFile._file_mixin_fieldsets,
            [
                {
                    "verbose_name": "download",
                    "fields": ["download_file"],
                    "file_field": "download_file",
                }
            ],
        )
