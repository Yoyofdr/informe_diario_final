# Manual migration - Add only RUT and tipo fields

import alerts.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0005_informediariocache'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizacion',
            name='rut',
            field=models.CharField(blank=True, help_text='RUT en formato NNNNNNNN-DV (sin puntos, DV mayúscula)', max_length=11, null=True, unique=True, validators=[alerts.validators.validar_rut_estricto]),
        ),
        migrations.AddField(
            model_name='organizacion',
            name='tipo',
            field=models.CharField(choices=[('empresa', 'Empresa'), ('independiente', 'Independiente')], default='independiente', help_text='Tipo de organización: Empresa (con RUT) o Independiente', max_length=20),
        ),
        migrations.AlterField(
            model_name='organizacion',
            name='dominio',
            field=models.CharField(blank=True, help_text='Campo legacy - no se usa para agrupar', max_length=80, null=True),
        ),
    ]