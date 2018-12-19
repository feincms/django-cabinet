import io
import itertools
import json
import os
import shutil
from unittest import skipIf

import django
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import ContentFile
from django.test import Client, TestCase
from django.test.utils import override_settings

from cabinet.models import File, Folder, get_file_model

from testapp.models import Stuff

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse


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

    def assertNoMediaFiles(self):
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
        self.assertEqual(response.status_code, 400)

        with io.open(self.image1_path, "rb") as image:
            response = c.post(
                "/admin/cabinet/file/add/",
                {"folder": folder.id, "image_file": image, "image_ppoi": "0.5x0.5"},
            )

        self.assertRedirects(
            response, "/admin/cabinet/file/?folder__id__exact={}".format(folder.id)
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

        with io.open(self.image1_path, "rb") as image:
            response = c.post(
                reverse("admin:cabinet_file_change", args=(f1.id,)),
                {"folder": folder.id, "image_file": image, "image_ppoi": "0.5x0.5"},
            )

        self.assertRedirects(
            response, "/admin/cabinet/file/?folder__id__exact={}".format(folder.id)
        )

        f2 = File.objects.get()
        f2_name = f2.file.name
        f2_bytes = f2.file.read()

        self.assertNotEqual(f1_name, f2_name)
        self.assertEqual(f1_bytes, f2_bytes)

        with io.open(self.image2_path, "rb") as image:
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
            response, "/admin/cabinet/file/?folder__id__exact={}".format(folder.id)
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
        response = c.get(
            "/admin/cabinet/file/?folder__id__exact={}&q=image".format(folder.pk)
        )
        self.assertContains(response, '<p class="paginator"> 1 file </p>', html=True)

        # Other folder
        f2 = Folder.objects.create(name="Second")
        response = c.get(
            "/admin/cabinet/file/?folder__id__exact={}&q=image".format(f2.pk)
        )
        self.assertContains(response, '<p class="paginator"> 0 files </p>', html=True)

        subfolder = Folder.objects.create(parent=folder, name="sub")
        f = File.objects.get()

        response = c.get("/admin/cabinet/file/folder/select/?files={}".format(f.pk))
        # TODO self.assertContains

        response = c.post(
            "/admin/cabinet/file/folder/select/",
            {"files": f.pk, "folder": subfolder.pk},
        )
        self.assertRedirects(
            response, "/admin/cabinet/file/?folder__id__exact={}".format(subfolder.pk)
        )

        # f.folder = subfolder
        # f.save()

        # File is in a subfolder now
        response = c.get("/admin/cabinet/file/?folder__id__exact={}".format(folder.pk))
        self.assertContains(response, '<p class="paginator"> 0 files </p>', html=True)

        # But can be found by searching
        response = c.get(
            "/admin/cabinet/file/?folder__id__exact={}&q=image".format(folder.pk)
        )
        self.assertContains(response, '<p class="paginator"> 1 file </p>', html=True)

        response = c.get(
            "/admin/cabinet/file/?folder__id__exact={}&file_type=image_file".format(
                folder.pk
            )
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

        with io.open(self.image1_path, "rb") as image:
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
        self.assertContains(response, '<img src="__processed__/', 1)

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
        )  # noqa
        self.assertRedirects(response, files_url)

        response = c.get(files_url)
        self.assertContains(
            response,
            '<a href="?_popup=1&amp;_to_field=id"><span class="folder"></span></a>',  # noqa
        )
        # We do not need to test adding files -- that's covered by Django.

    @skipIf(django.VERSION < (1, 11), "get_file_model() is not compatible.")
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
            "/admin/cabinet/file/?_popup=1&CKEditor=editor&CKEditorFuncNum=1"
            "&langCode=en&folder__id__exact={}".format(folder.pk)
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
            response, "/admin/cabinet/file/?folder__id__exact={}".format(folder.id)
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
            response, "/admin/cabinet/file/?folder__id__exact={}".format(folder.id)
        )

        file.refresh_from_db()
        self.assertFalse(file._overwrite)

    def test_invalid_folder(self):
        c = self.login()
        response = c.get("/admin/cabinet/file/?folder__id__exact=anything")
        self.assertRedirects(response, "/admin/cabinet/file/?e=1")

    @skipIf(django.VERSION < (1, 11), "No widget-based rendering in Django<1.11.")
    def test_cabinet_foreign_key(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)
        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content)

        c = self.login()
        response = c.get("/admin/testapp/stuff/add/")

        self.assertContains(response, 'class="cabinet-inline-upload"')
        self.assertContains(response, 'type="file"')
        self.assertContains(response, 'href="/admin/cabinet/file/?_to_field=id"')

        stuff = Stuff.objects.create(title="Test", file=file)
        response = c.get(reverse("admin:testapp_stuff_change", args=(stuff.id,)))

        self.assertContains(response, 'class="cabinet-inline-upload"')
        self.assertContains(response, 'type="file"')
        self.assertContains(
            response,
            'href="/admin/cabinet/file/?_to_field=id&amp;folder__id__exact={}"'.format(
                folder.id
            ),
        )

        filefield = Stuff._meta.get_field("file")
        formfield = filefield.formfield()
        self.assertTrue(isinstance(formfield.widget, forms.Select))

        name, path, args, kwargs = filefield.deconstruct()
        self.assertEqual(path, "django.db.models.ForeignKey")

    def test_two_files(self):
        folder = Folder.objects.create(name="Root")
        file = File(folder=folder)
        with io.open(self.image1_path, "rb") as image:
            file.image_file.save("hello.jpg", ContentFile(image.read()))

        file.full_clean()  # Everything well

        content = ContentFile("Hello")
        file.download_file.save("hello.txt", content, save=False)
        with self.assertRaises(ValidationError):
            file.full_clean()

    @skipIf(django.VERSION < (1, 11), 'selected="selected" is annoying')
    def test_file_add_folder_preselect(self):
        folder = Folder.objects.create(name="Root")
        c = self.login()

        response = c.get("/admin/cabinet/file/add/")
        self.assertContains(response, '<option value="" selected>----------</option>')

        response = c.get("/admin/cabinet/file/add/?folder={}".format(folder.id))
        self.assertContains(
            response, '<option value="{}" selected>Root</option>'.format(folder.id)
        )

    def test_folder_duplicate(self):
        folder = Folder.objects.create(name="Root")
        folder.full_clean()  # Cleaning self works.
        with self.assertRaises(ValidationError):
            Folder(name="Root").full_clean()
