# Generated by Django 2.1.2 on 2018-11-25 07:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0060_newsarticle_isdraft'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driver',
            name='country',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Country'),
        ),
        migrations.AlterField(
            model_name='driverentry',
            name='driver',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Driver'),
        ),
        migrations.AlterField(
            model_name='driverentry',
            name='teamEntry',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.TeamEntry'),
        ),
        migrations.AlterField(
            model_name='driverraceresult',
            name='driverEntry',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.DriverEntry'),
        ),
        migrations.AlterField(
            model_name='incident',
            name='opponentCar',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='opponent', to='frontend.DriverEntry'),
        ),
        migrations.AlterField(
            model_name='incident',
            name='ownCar',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.DriverEntry'),
        ),
        migrations.AlterField(
            model_name='incident',
            name='race',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Race'),
        ),
        migrations.AlterField(
            model_name='newsarticle',
            name='isDraft',
            field=models.BooleanField(default=False, verbose_name='Is draft?'),
        ),
        migrations.AlterField(
            model_name='race',
            name='track',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Track'),
        ),
        migrations.AlterField(
            model_name='raceresult',
            name='race',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Race'),
        ),
        migrations.AlterField(
            model_name='registration',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Season'),
        ),
        migrations.AlterField(
            model_name='teamentry',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Season'),
        ),
        migrations.AlterField(
            model_name='teamentry',
            name='team',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Team'),
        ),
        migrations.AlterField(
            model_name='textblock',
            name='season',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='frontend.Season'),
        ),
        migrations.AlterField(
            model_name='track',
            name='country',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Country'),
        ),
    ]
