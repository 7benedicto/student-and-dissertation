# Generated by Django 5.1.3 on 2025-05-25 03:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_dissertation', '0011_remove_filerepository_project_filerepository_group_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='filerepository',
            name='year',
            field=models.CharField(blank=True, max_length=4, null=True),
        ),
    ]
