# Generated by Django 2.1.2 on 2018-10-17 19:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0042_auto_20181014_1157'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driverraceresultinfo',
            name='driverRaceResult',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.DriverRaceResult'),
        ),
    ]
