# Data migration: ensure "Não Compareceu" (no_show) is in appointment config

from django.db import migrations


NO_SHOW_LABEL = 'Não Compareceu'
NO_SHOW_COLOR = '#6c757d'
# Insert after 'Cancelada', before 'Reagendada' to match Appointment.STATUS_CHOICES order
STATUS_ORDER = [
    'Agendada',
    'Confirmada',
    'Em Andamento',
    'Concluída',
    'Cancelada',
    NO_SHOW_LABEL,
    'Reagendada',
]


def add_no_show_to_config(apps, schema_editor):
    AppointmentSettings = apps.get_model('dashboard', 'AppointmentSettings')
    try:
        settings = AppointmentSettings.objects.get(pk=1)
    except AppointmentSettings.DoesNotExist:
        return

    changed = False
    if settings.status_choices is None:
        settings.status_choices = list(STATUS_ORDER)
        changed = True
    elif NO_SHOW_LABEL not in settings.status_choices:
        settings.status_choices = list(settings.status_choices)
        # Insert after Cancelada if present, else append
        if 'Cancelada' in settings.status_choices:
            idx = settings.status_choices.index('Cancelada') + 1
            settings.status_choices.insert(idx, NO_SHOW_LABEL)
        else:
            settings.status_choices.append(NO_SHOW_LABEL)
        changed = True

    if settings.status_colors is None:
        settings.status_colors = {}
    if not isinstance(settings.status_colors, dict):
        settings.status_colors = {}
    if NO_SHOW_LABEL not in settings.status_colors:
        settings.status_colors = dict(settings.status_colors)
        settings.status_colors[NO_SHOW_LABEL] = NO_SHOW_COLOR
        changed = True

    if changed:
        settings.save()


def noop_reverse(apps, schema_editor):
    # Optional: could remove 'Não Compareceu' from config; leaving config as-is is safer
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0027_convenio_prices_per_operator'),
    ]

    operations = [
        migrations.RunPython(add_no_show_to_config, noop_reverse),
    ]
