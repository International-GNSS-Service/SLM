from django.db import migrations
from django.db.models import Q


def migrate_deleted(apps, schema_editor):
    for Section in [
        apps.get_model("slm", "SiteAntenna"),
        apps.get_model("slm", "SiteCollocation"),
        apps.get_model("slm", "SiteFrequencyStandard"),
        apps.get_model("slm", "SiteHumiditySensor"),
        apps.get_model("slm", "SiteLocalEpisodicEffects"),
        apps.get_model("slm", "SiteMultiPathSources"),
        apps.get_model("slm", "SiteOtherInstrumentation"),
        apps.get_model("slm", "SitePressureSensor"),
        apps.get_model("slm", "SiteRadioInterferences"),
        apps.get_model("slm", "SiteReceiver"),
        apps.get_model("slm", "SiteSignalObstructions"),
        apps.get_model("slm", "SiteSurveyedLocalTies"),
        apps.get_model("slm", "SiteTemperatureSensor"),
        apps.get_model("slm", "SiteWaterVaporRadiometer"),
    ]:
        for sect in Section.objects.filter(Q(is_deleted=True) & Q(published=False)):
            Section.objects.filter(
                Q(published=True) & Q(subsection=sect.subsection) & Q(site=sect.site)
            ).update(is_deleted=True)
        Section.objects.filter(Q(is_deleted=True) & Q(published=False)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("slm", "0017_alter_logentry_unique_together_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_deleted, migrations.RunPython.noop, elidable=True)
    ]
