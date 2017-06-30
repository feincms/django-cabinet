import io
import itertools
import os

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
        self.image_path = os.path.join(settings.BASE_DIR, 'image.png')

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
            <a href="/admin/cabinet/file/folder/add/?parent=" class="addlink">
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

        with io.open(self.image_path, 'rb') as image:
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
            '>image.png</a>',
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

        self.assertEqual(
            [getattr(f1, field).name for field in f1.FILE_FIELDS],
            [f1_name, ''],
        )
        self.assertEqual(f1.download_type, '')

        with io.open(self.image_path, 'rb') as image:
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

        self.assertNotEqual(
            f1_name,
            f2_name,
        )

        with io.open(self.image_path, 'rb') as image:
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

        self.assertEqual(
            f2_name,
            f3_name,
        )

        # print(response, response.content.decode('utf-8'))

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

        with io.open(self.image_path, 'rb') as image:
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
