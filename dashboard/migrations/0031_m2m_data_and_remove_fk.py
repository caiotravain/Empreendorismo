# Data migration: copy FK to M2M, then remove old FK fields

from django.db import migrations, connection


def copy_doctor_admins(apps, schema_editor):
    """Copy Doctor.admin_id -> Doctor.admins M2M."""
    Doctor = apps.get_model('dashboard', 'Doctor')
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT id, admin_id FROM dashboard_doctor WHERE admin_id IS NOT NULL'
        )
        for doctor_id, admin_id in cursor.fetchall():
            try:
                doctor = Doctor.objects.get(pk=doctor_id)
                doctor.admins.add(admin_id)
            except Exception:
                pass


def copy_secretary_doctors(apps, schema_editor):
    """Copy Secretary.doctor_id -> Secretary.doctors M2M."""
    Secretary = apps.get_model('dashboard', 'Secretary')
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT id, doctor_id FROM dashboard_secretary WHERE doctor_id IS NOT NULL'
        )
        for secretary_id, doctor_id in cursor.fetchall():
            try:
                secretary = Secretary.objects.get(pk=secretary_id)
                secretary.doctors.add(doctor_id)
            except Exception:
                pass


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0030_doctor_admin_secretary_m2m'),
    ]

    operations = [
        migrations.RunPython(copy_doctor_admins, noop_reverse),
        migrations.RunPython(copy_secretary_doctors, noop_reverse),
        migrations.RemoveField(
            model_name='doctor',
            name='admin',
        ),
        migrations.RemoveField(
            model_name='secretary',
            name='doctor',
        ),
    ]
