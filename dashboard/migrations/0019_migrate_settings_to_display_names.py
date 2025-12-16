# Generated migration to convert settings from [value, label] format to display names only

from django.db import migrations


def migrate_settings_to_display_names(apps, schema_editor):
    """
    Convert type_choices and status_choices from [value, label] format to just display names.
    """
    AppointmentSettings = apps.get_model('dashboard', 'AppointmentSettings')
    
    try:
        settings = AppointmentSettings.objects.get(pk=1)
        
        # Convert type_choices
        if settings.type_choices:
            new_type_choices = []
            for choice in settings.type_choices:
                if isinstance(choice, list) and len(choice) >= 2:
                    # Old format: use the label (second element)
                    new_type_choices.append(choice[1])
                elif isinstance(choice, str):
                    # Already in new format
                    new_type_choices.append(choice)
            settings.type_choices = new_type_choices
        
        # Convert status_choices
        if settings.status_choices:
            new_status_choices = []
            for choice in settings.status_choices:
                if isinstance(choice, list) and len(choice) >= 2:
                    # Old format: use the label (second element)
                    new_status_choices.append(choice[1])
                elif isinstance(choice, str):
                    # Already in new format
                    new_status_choices.append(choice)
            settings.status_choices = new_status_choices
        
        settings.save()
        print(f'Migrated settings to display names format')
    except AppointmentSettings.DoesNotExist:
        # Settings don't exist yet, nothing to migrate
        pass


def reverse_migrate(apps, schema_editor):
    """
    Reverse migration - convert back to [value, label] format.
    This creates a slug from the display name as the value.
    """
    AppointmentSettings = apps.get_model('dashboard', 'AppointmentSettings')
    
    try:
        settings = AppointmentSettings.objects.get(pk=1)
        
        # Convert type_choices back
        if settings.type_choices:
            new_type_choices = []
            for choice in settings.type_choices:
                if isinstance(choice, str):
                    # New format: create [value, label] pair
                    # Generate slug from display name
                    value = choice.lower().replace(' ', '_').replace('-', '_')
                    new_type_choices.append([value, choice])
                elif isinstance(choice, list):
                    # Already in old format
                    new_type_choices.append(choice)
            settings.type_choices = new_type_choices
        
        # Convert status_choices back
        if settings.status_choices:
            new_status_choices = []
            for choice in settings.status_choices:
                if isinstance(choice, str):
                    # New format: create [value, label] pair
                    # Generate slug from display name
                    value = choice.lower().replace(' ', '_').replace('-', '_')
                    new_status_choices.append([value, choice])
                elif isinstance(choice, list):
                    # Already in old format
                    new_status_choices.append(choice)
            settings.status_choices = new_status_choices
        
        settings.save()
    except AppointmentSettings.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0018_fix_orphaned_medical_records'),
    ]

    operations = [
        migrations.RunPython(migrate_settings_to_display_names, reverse_migrate),
    ]
