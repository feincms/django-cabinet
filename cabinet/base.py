import inspect
import io
import os
import re

from django.core.exceptions import (
    FieldDoesNotExist,
    ImproperlyConfigured,
    ValidationError,
)
from django.db import models
from django.db.models import signals
from django.utils.translation import gettext_lazy as _
from imagefield.fields import ImageField, PPOIField
from PIL import Image
from tree_queries.fields import TreeNodeForeignKey


UPLOAD_TO = "cabinet/%Y/%m"


def upload_is_image(data):
    """
    Determine whether ``data`` is an image or not

    Usage::

        if upload_is_image(request.FILES['file']):
            ...
    """
    # From django/forms/fields.py
    if hasattr(data, "temporary_file_path"):
        file = data.temporary_file_path()
    else:
        file = io.BytesIO(data.read())

    try:
        image = Image.open(file)
        image.resize([20, 20], Image.LANCZOS)  # Verify image some more
        with io.BytesIO() as buf:
            image.save(buf, image.format)
        return True
    except Exception:  # OSError, errors while resizing
        return False


class ImageMixin(models.Model):
    image_file = ImageField(
        _("image"),
        upload_to=UPLOAD_TO,
        width_field="image_width",
        height_field="image_height",
        ppoi_field="image_ppoi",
        blank=True,
        max_length=1000,
    )
    image_width = models.PositiveIntegerField(
        _("image width"), blank=True, null=True, editable=False
    )
    image_height = models.PositiveIntegerField(
        _("image height"), blank=True, null=True, editable=False
    )
    image_ppoi = PPOIField(_("primary point of interest"))
    image_alt_text = models.CharField(
        _("alternative text"), max_length=1000, blank=True
    )

    class Meta:
        abstract = True
        verbose_name = _("image")
        verbose_name_plural = _("images")

    def accept_file(self, value):
        if upload_is_image(value):
            self.image_file = value
            return True


class DownloadMixin(models.Model):
    DOWNLOAD_TYPES = [  # pragma: no branch (last condition always matches)
        # Should we be using imghdr.what instead of extension guessing?
        (
            "image",
            _("Image"),
            lambda f: re.compile(
                r"\.(bmp|jpe?g|jp2|jxr|gif|png|tiff?)$", re.IGNORECASE
            ).search(f),
        ),
        (
            "video",
            _("Video"),
            lambda f: re.compile(
                r"\.(mov|m[14]v|mp4|avi|mpe?g|qt|ogv|wmv|flv)$", re.IGNORECASE
            ).search(f),
        ),
        (
            "audio",
            _("Audio"),
            lambda f: re.compile(
                r"\.(au|mp3|m4a|wma|oga|ram|wav)$", re.IGNORECASE
            ).search(f),
        ),
        ("pdf", _("PDF document"), lambda f: f.lower().endswith(".pdf")),
        ("swf", _("Flash"), lambda f: f.lower().endswith(".swf")),
        ("txt", _("Text"), lambda f: f.lower().endswith(".txt")),
        ("rtf", _("Rich Text"), lambda f: f.lower().endswith(".rtf")),
        ("zip", _("Zip archive"), lambda f: f.lower().endswith(".zip")),
        (
            "doc",
            _("Microsoft Word"),
            lambda f: re.compile(r"\.docx?$", re.IGNORECASE).search(f),
        ),
        (
            "xls",
            _("Microsoft Excel"),
            lambda f: re.compile(r"\.xlsx?$", re.IGNORECASE).search(f),
        ),
        (
            "ppt",
            _("Microsoft PowerPoint"),
            lambda f: re.compile(r"\.pptx?$", re.IGNORECASE).search(f),
        ),
        ("other", _("Binary"), lambda f: True),  # Must be last
    ]

    download_file = models.FileField(
        _("download"), upload_to=UPLOAD_TO, blank=True, max_length=1000
    )
    download_type = models.CharField(_("download type"), max_length=20, editable=False)

    class Meta:
        abstract = True
        verbose_name = _("download")
        verbose_name_plural = _("downloads")

    def save(self, *args, **kwargs):
        self.download_type = (  # pragma: no branch
            next(
                type
                for type, title, check in self.DOWNLOAD_TYPES
                if check(self.download_file.name)
            )
            if self.download_file
            else ""
        )
        super().save(*args, **kwargs)

    save.alters_data = True

    def accept_file(self, value):
        self.download_file = value
        return True


class OverwriteMixin(models.Model):
    _overwrite = models.BooleanField(
        _("Keep filename this time when uploading new file?"),
        default=False,
        help_text=_(
            "By default, a new and unique filename is generated for each file,"
            " which also helps with caching."
        ),
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        original = None
        if self.pk:
            original = self.__class__._base_manager.filter(pk=self.pk).first()

        if self._overwrite and original and not self.file._committed:
            original_file = original.file
            original_file_name = original_file.name
            original.delete_files()
            original_file.delete(save=False)

            new_file = self.file
            new_file.storage.save(
                original_file_name, new_file.file, max_length=new_file.field.max_length
            )
            new_file._committed = True
            setattr(self, new_file.field.name, original_file_name)

            # Better be safe than sorry:
            new_file.name = original_file_name
            self.file_name = os.path.basename(new_file.name)

            self._overwrite = False  # Only overwrite once.
            super().save(*args, **kwargs)

        else:
            self._overwrite = False  # Only overwrite once.
            super().save(*args, **kwargs)

            if original and (
                original.file.name != self.file.name
                or original.file.storage != self.file.storage
            ):
                original.delete_files()

    save.alters_data = True


class TimestampsMixin(models.Model):
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True


class AbstractFile(TimestampsMixin):
    FILE_FIELDS = []

    folder = TreeNodeForeignKey(
        "cabinet.Folder",
        on_delete=models.PROTECT,
        verbose_name=_("folder"),
        related_name="files",
    )

    file_name = models.CharField(_("file name"), max_length=1000)
    file_size = models.PositiveIntegerField(_("file size"))

    class Meta:
        abstract = True
        ordering = ["file_name"]
        verbose_name = _("file")
        verbose_name_plural = _("files")

    def __str__(self):
        return self.file_name

    def save(self, *args, **kwargs):
        f_obj = self.file
        self.file_name = os.path.basename(f_obj.name)
        self.file_size = f_obj.size
        super().save(*args, **kwargs)

    save.alters_data = True

    def delete_files(self):
        for field in self.FILE_FIELDS:
            f_obj = getattr(self, field)
            if not f_obj.name:
                continue

            # f_obj.storage.delete(f_obj.name)
            f_obj.delete(save=False)

    delete_files.alters_data = True

    def __files(self):
        for field in self.FILE_FIELDS:
            f = getattr(self, field)
            if f and f.name:
                yield f

    @property
    def file(self):
        return next(self.__files())

    @file.setter
    def file(self, value):
        for fn in self._accept_file_functions:
            if fn(self, value):
                break
        else:  # pragma: no cover (improper configuration!)
            raise TypeError("Invalid value %r" % value)

    def clean(self):
        if len(list(self.__files())) != 1:
            raise ValidationError(_("Please fill in exactly one file field!"))


def determine_accept_file_functions(sender, **kwargs):
    if issubclass(sender, AbstractFile) and not sender._meta.abstract:
        fields = set(sender.FILE_FIELDS)
        fns = {}
        fieldsets = []

        for cls in list(inspect.getmro(sender))[1:]:
            if not issubclass(cls, models.Model):
                continue
            for f in fields:
                try:
                    cls._meta.get_field(f)
                except FieldDoesNotExist:
                    pass
                else:
                    # File field exists on this class. There *must* be an
                    # accept_file method as well.
                    fns[f] = cls.accept_file
                    fields.discard(f)
                    fieldsets.append(
                        {
                            "verbose_name": cls._meta.verbose_name,
                            "fields": [
                                field.name
                                for field in cls._meta.local_fields
                                if field.editable
                            ],
                            "file_field": f,
                        }
                    )
                    break

        if fields:  # pragma: no cover
            raise ImproperlyConfigured(
                'No "accept_file" method found for {}'.format(", ".join(sorted(fields)))
            )

        sender._accept_file_functions = [fns[f] for f in sender.FILE_FIELDS]
        sender._file_mixin_fieldsets = fieldsets


signals.class_prepared.connect(determine_accept_file_functions)
