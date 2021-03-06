# Generated by Django 2.1.2 on 2018-12-01 19:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0063_race_driverofthedayvote'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='driverofthedayvote',
            name='race',
        ),
        migrations.RemoveField(
            model_name='race',
            name='driverOfTheDayVote',
        ),
        migrations.AddField(
            model_name='driverofthedayvote',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Season'),
        ),
        migrations.AddField(
            model_name='season',
            name='driverOfTheDayVote',
            field=models.BooleanField(default=False, verbose_name='Driver of the day vote'),
        ),
    ]
