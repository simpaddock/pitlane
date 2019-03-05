# Generated by Django 2.1.2 on 2019-03-03 13:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0075_auto_20190113_0950'),
    ]

    operations = [
        migrations.CreateModel(
            name='SkinSubmissions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skinFile', models.FileField(blank=True, default=None, upload_to='uploads/registration/', verbose_name='Skin file')),
                ('copyrightAccept', models.BooleanField(default=False, verbose_name='Our submission is free of copyright violations.')),
                ('registration', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Season')),
            ],
        ),
        migrations.RemoveField(
            model_name='registrationstatus',
            name='registration',
        ),
        migrations.RemoveField(
            model_name='registration',
            name='copyrightAccept',
        ),
        migrations.RemoveField(
            model_name='registration',
            name='ignoreReason',
        ),
        migrations.RemoveField(
            model_name='registration',
            name='skinFile',
        ),
        migrations.RemoveField(
            model_name='registration',
            name='wasUploaded',
        ),
        migrations.AlterField(
            model_name='registration',
            name='vehicleClass',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.VehicleClass', verbose_name='Vehicle'),
        ),
        migrations.DeleteModel(
            name='RegistrationStatus',
        ),
    ]