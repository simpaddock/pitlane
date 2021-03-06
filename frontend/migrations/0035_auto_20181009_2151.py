# Generated by Django 2.1.2 on 2018-10-09 19:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0034_incident_result'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='', max_length=100)),
                ('text', models.TextField(default='', max_length=5000)),
            ],
        ),
        migrations.AlterField(
            model_name='incident',
            name='description',
            field=models.TextField(default='', max_length=1000, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='incident',
            name='opponentCar',
            field=models.CharField(default='', max_length=100, verbose_name='Opponent car'),
        ),
        migrations.AlterField(
            model_name='incident',
            name='ownCar',
            field=models.CharField(default='', max_length=100, verbose_name='Own car'),
        ),
        migrations.AlterField(
            model_name='incident',
            name='result',
            field=models.TextField(default='', max_length=100),
        ),
    ]
