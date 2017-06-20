import os
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from versatileimagefield.fields import PPOIField, VersatileImageField


UPLOAD_TO = 'cabinet/%Y/%m'


class ImageMixin(models.Model):
    image_file = VersatileImageField(
        _('image'),
        upload_to=UPLOAD_TO,
        width_field='image_width',
        height_field='image_height',
        ppoi_field='image_ppoi',
        blank=True,
    )
    image_width = models.PositiveIntegerField(
        _('image width'),
        blank=True,
        null=True,
        editable=False,
    )
    image_height = models.PositiveIntegerField(
        _('image height'),
        blank=True,
        null=True,
        editable=False,
    )
    image_ppoi = PPOIField(_('primary point of interest'))
    image_alt_text = models.CharField(
        _('alternative text'),
        max_length=1000,
        blank=True,
    )

    class Meta:
        abstract = True


class DownloadMixin(models.Model):
    DOWNLOAD_TYPES = [
        # Should we be using imghdr.what instead of extension guessing?
        ('image', _('Image'), lambda f: re.compile(
            r'\.(bmp|jpe?g|jp2|jxr|gif|png|tiff?)$', re.IGNORECASE).search(f)),
        ('video', _('Video'), lambda f: re.compile(
            r'\.(mov|m[14]v|mp4|avi|mpe?g|qt|ogv|wmv|flv)$',
            re.IGNORECASE).search(f)),
        ('audio', _('Audio'), lambda f: re.compile(
            r'\.(au|mp3|m4a|wma|oga|ram|wav)$', re.IGNORECASE).search(f)),
        ('pdf', _('PDF document'), lambda f: f.lower().endswith('.pdf')),
        ('swf', _('Flash'), lambda f: f.lower().endswith('.swf')),
        ('txt', _('Text'), lambda f: f.lower().endswith('.txt')),
        ('rtf', _('Rich Text'), lambda f: f.lower().endswith('.rtf')),
        ('zip', _('Zip archive'), lambda f: f.lower().endswith('.zip')),
        ('doc', _('Microsoft Word'), lambda f: re.compile(
            r'\.docx?$', re.IGNORECASE).search(f)),
        ('xls', _('Microsoft Excel'), lambda f: re.compile(
            r'\.xlsx?$', re.IGNORECASE).search(f)),
        ('ppt', _('Microsoft PowerPoint'), lambda f: re.compile(
            r'\.pptx?$', re.IGNORECASE).search(f)),
        ('other', _('Binary'), lambda f: True),  # Must be last
    ]

    download_file = models.FileField(
        _('download'),
        upload_to=UPLOAD_TO,
        blank=True,
    )
    download_type = models.CharField(
        _('download type'),
        max_length=20,
        editable=False,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.download_type = next(iter(
            type
            for type, title, check in self.DOWNLOAD_TYPES
            if check(self.download_file.name)
        )) if self.download_file else ''
        super().save(*args, **kwargs)
    save.alters_data = True


class AbstractFileBase(models.Model):
    FILE_FIELDS = []

    folder = models.ForeignKey(
        'cabinet.Folder',
        on_delete=models.CASCADE,
        verbose_name=_('folder'),
        related_name='files',
    )

    file_name = models.CharField(
        _('file name'),
        max_length=1000,
    )
    file_size = models.PositiveIntegerField(
        _('file size'),
    )

    class Meta:
        abstract = True
        ordering = ['file_name']
        verbose_name = _('file')
        verbose_name_plural = _('files')

    def __str__(self):
        return self.file_name

    @property
    def file(self):
        files = (getattr(self, field) for field in self.FILE_FIELDS)
        return next(iter(f for f in files if f.name))

    def clean(self):
        files = (getattr(self, field) for field in self.FILE_FIELDS)
        if len([f for f in files if f.name]) != 1:
            raise ValidationError(_('Please fill in exactly one file field!'))

    def save(self, *args, **kwargs):
        f_obj = self.file
        self.file_name = os.path.basename(f_obj.name)
        self.file_size = f_obj.size
        super().save(*args, **kwargs)
    save.alters_data = True


class AbstractFile(
    AbstractFileBase,
    ImageMixin,
    DownloadMixin,
):
    FILE_FIELDS = [
        'image_file',
        'download_file',
    ]

    class Meta(AbstractFileBase.Meta):
        abstract = True
