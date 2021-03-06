# Generated by Django 2.1.2 on 2018-11-22 19:41

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0056_upload'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenericPrivacyAccept',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(default='', max_length=200)),
                ('givenName', models.CharField(default='', max_length=200)),
                ('familyName', models.CharField(default='', max_length=200)),
                ('privacyAccept', models.BooleanField(default=False, verbose_name='I consent the GDPR compilant processing of my submission data')),
                ('acceptDate', models.DateTimeField(default=datetime.datetime.now)),
                ('ipAddress', models.GenericIPAddressField()),
                ('userAgent', models.CharField(default='', max_length=255)),
            ],
        ),
        migrations.AlterField(
            model_name='registration',
            name='skinFile',
            field=models.FileField(blank=True, default=None, upload_to='uploads/registration/', verbose_name='Skin file'),
        ),
        migrations.AlterField(
            model_name='textblock',
            name='context',
            field=models.CharField(choices=[('about', 'About page'), ('rule', 'Reglement'), ('landing', 'Landing page'), ('signup', 'SignUp'), ('dstandings', 'Driver standings (Preseason)'), ('tstandings', 'Team standings (Preseason)')], default=('about', 'About page'), max_length=30),
        ),
        migrations.AlterField(
            model_name='upload',
            name='name',
            field=models.CharField(default='', max_length=200, null=True),
        ),
    ]
