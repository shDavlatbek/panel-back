# Generated by Django 5.1.6 on 2025-04-08 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0005_alter_station_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='station',
            name='height',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
