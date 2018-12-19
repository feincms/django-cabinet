from django.contrib import admin

from .models import Stuff


@admin.register(Stuff)
class StuffAdmin(admin.ModelAdmin):
    raw_id_fields = ["file"]
