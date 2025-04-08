from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeographicArea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('north', models.FloatField(help_text='North latitude bound')),
                ('south', models.FloatField(help_text='South latitude bound')),
                ('east', models.FloatField(help_text='East longitude bound')),
                ('west', models.FloatField(help_text='West longitude bound')),
                ('coordinates', models.TextField(blank=True, help_text='GeoJSON-compatible polygon coordinates array', null=True)),
                ('preferred_resolution', models.PositiveSmallIntegerField(default=6, help_text='H3 resolution (0-15)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Geographic Area',
                'verbose_name_plural': 'Geographic Areas',
            },
        ),
    ] 