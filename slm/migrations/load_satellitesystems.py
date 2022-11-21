from django.db import migrations


def load_satellitesystems(apps, schema_editor):

    SatelliteSystem = apps.get_model('slm', 'SatelliteSystem')
    for system in {
        'GPS',
        'GLO',
        'GAL',
        'BDS',
        'QZSS',
        'IRNSS',
        'SBAS',
        'WAAS'
    }:
        SatelliteSystem.objects.create(name=system)


class Migration(migrations.Migration):

    dependencies = [
        ('slm', '0001_initial')
    ]

    operations = [
        migrations.RunPython(load_satellitesystems)
    ]
