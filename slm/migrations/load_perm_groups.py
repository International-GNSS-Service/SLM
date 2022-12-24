from django.db import migrations


def load_perm_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    group = Group.objects.create(name='Agency Manager')
    group.permissions.set(
        Permission.objects.filter(
            codename__in=['propose_sites', 'moderate_sites']
        )
    )
    group.save()


def unload_perm_groups(apps, schema_editor):
    apps.get_model(
        'auth', 'Group'
    ).objects.filter(
        name='Agency Manager'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('slm', '0001_initial')
    ]

    operations = [
        migrations.RunPython(load_perm_groups, unload_perm_groups)
    ]
