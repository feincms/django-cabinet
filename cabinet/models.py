from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from cabinet.base import AbstractFile


if not hasattr(settings, 'CABINET_FILE_MODEL'):
    settings.CABINET_FILE_MODEL = 'cabinet.File'


def get_file_model():
    """
    Return the File model that is active in this project.
    """
    try:
        return apps.get_model(settings.CABINET_FILE_MODEL, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured(
            "CABINET_FILE_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "CABINET_FILE_MODEL refers to model '%s'"
            " that has not been installed" % settings.CABINET_FILE_MODEL
        )


class Folder(models.Model):
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True, null=True,
        verbose_name=_('parent'),
        related_name='children',
    )
    name = models.CharField(
        _('name'),
        max_length=100,
    )

    class Meta:
        ordering = ['name']
        unique_together = [('parent', 'name')]
        verbose_name = _('folder')
        verbose_name_plural = _('folders')

    def __str__(self):
        return self.name

    def ancestors(self):
        node = self
        while True:
            yield node
            if node.parent_id:
                node = node.parent
            else:
                break

    def clean(self):
        if self.id and self.parent_id and (
            self.id in [node.id for node in self.parent.ancestors()]
        ):
            raise ValidationError({
                'parent': _('Loop detected.'),
            })


class File(AbstractFile):
    class Meta(AbstractFile.Meta):
        swappable = 'CABINET_FILE_MODEL'
