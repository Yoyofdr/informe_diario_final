"""
Migración para agregar constraint de formato RUT en la base de datos
Solo se aplica en PostgreSQL, no en SQLite
"""
from django.db import migrations, connection


def add_rut_constraint(apps, schema_editor):
    """Agregar constraint solo si es PostgreSQL"""
    if connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE alerts_organizacion
                ADD CONSTRAINT rut_formato_estricto_chk
                CHECK (rut IS NULL OR rut ~ '^[1-9][0-9]{0,7}-[0-9K]$');
            """)


def remove_rut_constraint(apps, schema_editor):
    """Remover constraint solo si es PostgreSQL"""
    if connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE alerts_organizacion
                DROP CONSTRAINT IF EXISTS rut_formato_estricto_chk;
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0006_add_rut_and_tipo_to_organizacion'),
    ]

    operations = [
        migrations.RunPython(
            add_rut_constraint,
            remove_rut_constraint
        ),
    ]