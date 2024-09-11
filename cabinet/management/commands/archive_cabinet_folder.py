import random
import string
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.management import BaseCommand

from cabinet.models import Folder


def _get_random_suffix():
    return random.choices(string.ascii_lowercase, k=4)


class Command(BaseCommand):
    help = "Create archive with contents of a cabinet folder, using the data structure of the db instead of the disk."

    def add_arguments(self, parser):
        parser.add_argument("--folder-id", type=int, required=True)
        parser.add_argument("--output", type=Path, required=True)

    def handle(self, **options):
        folder = Folder.objects.get(id=options["folder_id"])
        output = options["output"]

        arc_paths = set()
        with ZipFile(output, "w", ZIP_DEFLATED) as zip_file:
            for file, path in self._walk(folder, path=()):
                arc_path = Path(*path) / file.file_name

                if arc_path in arc_paths:
                    filename = Path(file.file_name)
                    arc_path = Path(*path) / "".join(
                        [
                            filename.stem,
                            "_",
                            *_get_random_suffix(),
                            *filename.suffixes,
                        ]
                    )

                zip_file.write(file.file.path, arc_path)
                arc_paths.add(arc_path)

    def _walk(self, folder, *, path):
        path = (*tuple(path), folder.name)
        for file_ in folder.files.all():
            yield (file_, path)

        for child in folder.children.all():
            yield from self._walk(child, path=path)
