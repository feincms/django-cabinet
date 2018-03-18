import io
import itertools
import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase

from cabinet.models import File, Folder


class CabinetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='test',
            is_staff=True,
            is_superuser=True,
        )
        self.image1_path = os.path.join(settings.BASE_DIR, 'image.png')
        self.image2_path = os.path.join(settings.BASE_DIR, 'image-neg.png')
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)

    def login(self):
        client = Client()
        client.force_login(self.user)
        return client

    def assertNoMediaFiles(self):
        File.objects.all().delete()
        files = list(itertools.chain.from_iterable(
            i[2] for i in os.walk(settings.MEDIA_ROOT)
        ))
        self.assertEqual(files, [])

    def test_cabinet_folders(self):
        c = self.login()

        response = c.get('/admin/cabinet/file/')
        self.assertContains(
            response,
            '<script type="text/template" id="cabinet-result-list">',
            1,
        )
        self.assertContains(
            response,
            '<script type="text/template" id="cabinet-folder-list">',
            1,
        )
        self.assertContains(
            response,
            '''
<a href="/admin/cabinet/file/folder/add/?&amp;parent=" class="addlink">
    Add folder
</a>
            ''',
            html=True,
        )
        self.assertNotContains(
            response,
            'Add file',
        )

        response = c.post('/admin/cabinet/file/folder/add/', {
            'name': 'Test 1',
        })
        folder = Folder.objects.get()
        self.assertRedirects(
            response,
            '/admin/cabinet/file/?folder__id__exact=%s' % folder.id,
        )

        response = c.post('/admin/cabinet/file/folder/%s/' % folder.id, {
            'name': folder.name,
            '_delete_folder': True,
        })
        self.assertRedirects(
            response,
            '/admin/cabinet/file/',
        )
        self.assertEqual(
            Folder.objects.count(),
            0,
        )

        self.assertNoMediaFiles()

    def test_upload(self):
        folder = Folder.objects.create(name='Test')
        c = self.login()

        with io.open(self.image1_path, 'rb') as image:
            response = c.post('/admin/cabinet/file/add/', {
                'folder': folder.id,
                'image_file_0': image,
            })

        self.assertRedirects(
            response,
            '/admin/cabinet/file/',
        )

        response = c.get(
            '/admin/cabinet/file/?folder__id__exact=%s' % folder.id)

        self.assertContains(
            response,
            '>image.png <small>(4.9 KB)</small><',
            1,
        )
        self.assertContains(
            response,
            '''../</a>''',
        )
        self.assertContains(
            response,
            '<p class="paginator"> 1 file </p>',
            html=True,
        )

        response = c.get('/admin/cabinet/file/')
        self.assertContains(
            response,
            '<a href="?&amp;folder__id__exact=%s">Test</a>' % folder.id,
        )
        self.assertContains(
            response,
            '<p class="paginator"> 0 files </p>',
            html=True,
        )

        response = c.get('/admin/cabinet/file/?q=image')
        self.assertContains(
            response,
            '<p class="paginator"> 1 file </p>',
            html=True,
        )

        f1 = File.objects.get()
        f1_name = f1.file.name
        f1_bytes = f1.file.read()

        self.assertEqual(
            [getattr(f1, field).name for field in f1.FILE_FIELDS],
            [f1_name, ''],
        )
        self.assertEqual(f1.download_type, '')

        with io.open(self.image1_path, 'rb') as image:
            response = c.post('/admin/cabinet/file/%s/change/' % f1.id, {
                'folder': folder.id,
                'image_file_0': image,
            })

        self.assertRedirects(
            response,
            '/admin/cabinet/file/',
        )

        f2 = File.objects.get()
        f2_name = f2.file.name
        f2_bytes = f2.file.read()

        self.assertNotEqual(
            f1_name,
            f2_name,
        )
        self.assertEqual(
            f1_bytes,
            f2_bytes,
        )

        with io.open(self.image2_path, 'rb') as image:
            response = c.post('/admin/cabinet/file/%s/change/' % f1.id, {
                'folder': folder.id,
                'image_file_0': image,
                '_overwrite': True,
            })

        self.assertRedirects(
            response,
            '/admin/cabinet/file/',
        )

        f3 = File.objects.get()
        f3_name = f3.file.name
        f3_bytes = f3.file.read()

        self.assertEqual(
            f2_name,
            f3_name,
        )
        self.assertNotEqual(
            f2_bytes,
            f3_bytes,
        )
        print(f2_bytes)

        self.assertNoMediaFiles()

    def test_stuff(self):
        self.assertEqual(
            Folder.objects.count(),
            0,
        )
        self.assertEqual(
            File.objects.count(),
            0,
        )

    def test_dnd_upload(self):
        c = self.login()
        f = Folder.objects.create(name='Test')
        with io.BytesIO(b'invalid') as file:
            file.name = 'image.jpg'  # but is not
            response = c.post('/admin/cabinet/file/upload/', {
                'folder': f.id,
                'file': file,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            b'{"success": true}',
        )

        with io.open(self.image1_path, 'rb') as image:
            response = c.post('/admin/cabinet/file/upload/', {
                'folder': f.id,
                'file': image,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            b'{"success": true}',
        )

        response = c.get(
            '/admin/cabinet/file/?folder__id__exact=%s' % f.id)

        self.assertContains(
            response,
            '<p class="paginator"> 2 files </p>',
            html=True,
        )
        self.assertContains(
            response,
            # Only looking at the extension...
            '<span class="download download-image">',
            1,
        )
        self.assertContains(
            response,
            '<img src="__sized__/cabinet/',
            1,
        )

        self.assertNoMediaFiles()

    def test_raw_id_fields(self):
        c = self.login()
        response = c.get('/admin/cabinet/file/?_to_field=id&_popup=1')
        self.assertContains(
            response,
            '''
<a href="/admin/cabinet/file/folder/add/?_popup=1&amp;_to_field=id&amp;parent="
    class="addlink">
  Add folder
</a>
            ''',
            html=True,
        )

        response = c.post(
            '/admin/cabinet/file/folder/add/?_popup=1&_to_field=id',
            {'name': 'Test'},
        )
        f = Folder.objects.get()
        files_url = '/admin/cabinet/file/?_popup=1&_to_field=id&folder__id__exact=%s' % f.id  # noqa
        self.assertRedirects(
            response,
            files_url,
        )

        response = c.get(files_url)
        self.assertContains(
            response,
            '<a href="?_popup=1&amp;_to_field=id"><span class="folder"></span></a>',  # noqa
        )
        # We do not need to test adding files -- that's covered by Django.
