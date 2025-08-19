# Merge migration to resolve conflicts

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0007_add_rut_constraint'),
        ('alerts', '0008_add_rut_tipo_only'),
    ]

    operations = [
    ]