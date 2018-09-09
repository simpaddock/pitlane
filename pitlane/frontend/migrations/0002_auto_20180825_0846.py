# Generated by Django 2.1 on 2018-08-25 06:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverRaceResultInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('value', models.TextField()),
                ('infoType', models.TextField()),
            ],
        ),
        migrations.RemoveField(
            model_name='driverraceresult',
            name='infoType',
        ),
        migrations.RemoveField(
            model_name='driverraceresult',
            name='name',
        ),
        migrations.RemoveField(
            model_name='driverraceresult',
            name='value',
        ),
        migrations.AddField(
            model_name='driverraceresult',
            name='driverEntry',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.DriverEntry'),
        ),
        migrations.AddField(
            model_name='driverraceresult',
            name='raceResult',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.RaceResult'),
        ),
        migrations.AlterField(
            model_name='driver',
            name='country',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Country'),
        ),
        migrations.AlterField(
            model_name='driverentry',
            name='driver',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Driver'),
        ),
        migrations.AlterField(
            model_name='driverentry',
            name='teamEntry',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.TeamEntry'),
        ),
        migrations.AlterField(
            model_name='race',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Season'),
        ),
        migrations.AlterField(
            model_name='race',
            name='track',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Track'),
        ),
        migrations.AlterField(
            model_name='raceresult',
            name='race',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Race'),
        ),
        migrations.AlterField(
            model_name='raceresult',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Season'),
        ),
        migrations.AlterField(
            model_name='season',
            name='league',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.League'),
        ),
        migrations.AlterField(
            model_name='teamentry',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Season'),
        ),
        migrations.AlterField(
            model_name='teamentry',
            name='team',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Team'),
        ),
        migrations.AlterField(
            model_name='track',
            name='country',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.DO_NOTHING, to='frontend.Country'),
        ),
    ]
