from django.db import models


class Medicine(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    manufacturer = models.CharField(max_length=255)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    pack_size_label = models.CharField(max_length=100)
    pack_units = models.PositiveIntegerField(null=True, blank=True)
    unit_type = models.CharField(max_length=50)
    form = models.CharField(max_length=100)
    form_variant = models.CharField(max_length=10, blank=True, default="")
    pack_volume = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    salt_1 = models.CharField(max_length=255)
    salt_2 = models.CharField(max_length=255, null=True, blank=True)
    salt_key = models.CharField(max_length=255, db_index=True)
    price_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    composition_incomplete = models.BooleanField(default=False)
    is_comparable = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Pharmacy(models.Model):
    class PharmacyType(models.TextChoices):
        JAN_AUSHADHI = 'jan_aushadhi', 'Jan Aushadhi'
        CHAIN = 'chain', 'Chain'
        LOCAL = 'local', 'Local'

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=PharmacyType.choices)
    area = models.CharField(max_length=255)
    address = models.TextField()
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    phone = models.CharField(max_length=30)
    hours = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class PharmacyPrice(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    in_stock = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('medicine', 'pharmacy')

    def __str__(self):
        return f'{self.medicine} at {self.pharmacy}'


class Lab(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    phone = models.CharField(max_length=30)
    hours = models.CharField(max_length=255)
    nabl_accredited = models.BooleanField(default=False)
    home_collection = models.BooleanField(default=False)
    collection_fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class DiagnosticTest(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    aliases = models.TextField(blank=True)
    fasting_required = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class LabTestPrice(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    test = models.ForeignKey(DiagnosticTest, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    report_time_hours = models.PositiveIntegerField()
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lab', 'test')

    def __str__(self):
        return f'{self.test} at {self.lab}'
