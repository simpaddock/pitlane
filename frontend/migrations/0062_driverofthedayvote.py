# Generated by Django 2.1.2 on 2018-11-30 19:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0061_auto_20181125_0816'),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverOfTheDayVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ipAddress', models.GenericIPAddressField()),
                ('driver', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Driver')),
                ('race', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='frontend.Race')),
            ],
        ),
    ]