from django.db import migrations


def load_satellitesystems(apps, schema_editor):
    SatelliteSystem = apps.get_model("slm", "SatelliteSystem")
    for system in [
        {"name": "GPS", "order": 0},
        {"name": "GLO", "order": 1},
        {"name": "GAL", "order": 2},
        {"name": "BDS", "order": 3},
        {"name": "QZSS", "order": 4},
        {"name": "IRNSS", "order": 5},
        {"name": "SBAS", "order": 6},
        {"name": "WAAS", "order": 7},
    ]:
        SatelliteSystem.objects.create(**system)


def unload_satellitesystems(apps, schema_editor):
    SatelliteSystem = apps.get_model("slm", "SatelliteSystem")
    SatelliteSystem.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("slm", "0001_initial")]

    operations = [migrations.RunPython(load_satellitesystems, unload_satellitesystems)]
