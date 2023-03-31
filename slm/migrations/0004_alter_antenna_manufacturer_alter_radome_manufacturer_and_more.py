# Generated by Django 4.1.7 on 2023-03-28 05:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('slm', '0003_alter_datacenter_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='antenna',
            name='manufacturer',
            field=models.ForeignKey(blank=True, default=None, help_text='The manufacturing organization.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s', to='slm.manufacturer'),
        ),
        migrations.AlterField(
            model_name='radome',
            name='manufacturer',
            field=models.ForeignKey(blank=True, default=None, help_text='The manufacturing organization.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s', to='slm.manufacturer'),
        ),
        migrations.AlterField(
            model_name='receiver',
            name='manufacturer',
            field=models.ForeignKey(blank=True, default=None, help_text='The manufacturing organization.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s', to='slm.manufacturer'),
        ),
    ]