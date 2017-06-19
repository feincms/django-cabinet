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
            '<div id="cabinet" style="display:none">',
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
            'delete': True,
        })
        self.assertRedirects(
            response,
            '/admin/cabinet/file/',
        )
        self.assertEqual(
            Folder.objects.count(),
            0,
        )

    def test_stuff(self):
        self.assertEqual(
            Folder.objects.count(),
            0,
        )
        self.assertEqual(
            File.objects.count(),
            0,
        )
