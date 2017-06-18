from django.test import TestCase

from cabinet.models import Folder, File


class TagsTestCase(TestCase):
    def test_stuff(self):
        self.assertEqual(
            Folder.objects.count(),
            0,
        )
        self.assertEqual(
            File.objects.count(),
            0,
        )
