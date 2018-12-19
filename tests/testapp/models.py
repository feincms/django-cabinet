from django.db import models

from cabinet.fields import CabinetForeignKey


class Stuff(models.Model):
    title = models.CharField(max_length=100)
    file = CabinetForeignKey(on_delete=models.CASCADE)
