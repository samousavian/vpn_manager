# Generated by Django 4.2.2 on 2024-02-04 08:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modifier', '0003_updated_inbound_uuid'),
    ]

    operations = [
        migrations.RenameField(
            model_name='updated_inbound',
            old_name='buyer',
            new_name='seller',
        ),
    ]
