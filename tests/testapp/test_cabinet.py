import io
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase

from cabinet.models import Folder, File


class CabinetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='test',
            is_staff=True,
            is_superuser=True,
        )

    def login(self):
        client = Client()
        client.force_login(self.user)
        return client

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

    def test_upload(self):
        folder = Folder.objects.create(name='Test')
        c = self.login()

        with io.open(os.path.join(settings.BASE_DIR, 'image.png'), 'rb') as f:
            response = c.post('/admin/cabinet/file/add/', {
                'folder': folder.id,
                'image_file_0': f,
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
            '<a href="?folder__id__exact=%s">Test</a>' % folder.id,
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

        # print(response.content.decode('utf-8'))

    def test_stuff(self):
        self.assertEqual(
            Folder.objects.count(),
            0,
        )
        self.assertEqual(
            File.objects.count(),
            0,
        )
