# Generated by Django 2.1 on 2018-08-25 06:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0002_auto_20180825_0846'),
    ]

    operations = [
        migrations.AddField(
            model_name='driverraceresultinfo',
            name='driverRaceResult',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.DriverRaceResult'),
        ),
    ]