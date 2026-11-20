from django.contrib import admin
from .models import (
    DiagnosticTest,
    Lab,
    LabTestPrice,
    Medicine,
    Pharmacy,
    PharmacyPrice,
)

admin.site.register(Medicine)
admin.site.register(Pharmacy)
admin.site.register(PharmacyPrice)
admin.site.register(Lab)
admin.site.register(DiagnosticTest)
admin.site.register(LabTestPrice)
