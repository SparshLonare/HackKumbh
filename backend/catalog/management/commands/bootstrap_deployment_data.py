from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from catalog.models import (
    DiagnosticTest,
    Lab,
    LabTestPrice,
    Medicine,
    Pharmacy,
)


CLEAN_MEDICINES_CSV = settings.BASE_DIR / "data" / "clean" / "medicines_clean.csv"


class Command(BaseCommand):
    help = "Load the bundled catalog once when a newly deployed database is empty."

    def handle(self, *args, **options):
        if Medicine.objects.exists():
            self.stdout.write("Medicine catalog already exists; skipping initial medicine import.")
        else:
            if not CLEAN_MEDICINES_CSV.is_file():
                raise CommandError(
                    f"Cleaned medicine data is missing: {CLEAN_MEDICINES_CSV}. "
                    "The deployment build must run clean_data.py before startup."
                )
            call_command("import_medicines", verbosity=options["verbosity"])

        sample_catalog_exists = all(
            model.objects.exists()
            for model in (Pharmacy, Lab, DiagnosticTest, LabTestPrice)
        )
        if sample_catalog_exists:
            self.stdout.write("Sample pharmacy and lab catalog already exists; skipping import.")
        else:
            call_command("import_local_catalog", verbosity=options["verbosity"])
