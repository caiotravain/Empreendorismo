# Generated migration to fix orphaned medical records

from django.db import migrations


def fix_orphaned_medical_records(apps, schema_editor):
    """
    Fix orphaned MedicalRecord entries that reference non-existent patients.
    Set their patient_id to NULL since the field allows null=True.
    Uses raw SQL for efficiency.
    """
    db_alias = schema_editor.connection.alias
    
    # Use raw SQL to find and fix orphaned records in one query
    with schema_editor.connection.cursor() as cursor:
        # Count orphaned records first
        cursor.execute("""
            SELECT COUNT(*) 
            FROM dashboard_medicalrecord mr
            WHERE mr.patient_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM dashboard_patient p 
                WHERE p.id = mr.patient_id
            )
        """)
        count = cursor.fetchone()[0]
        
        if count > 0:
            # Fix orphaned records by setting patient_id to NULL
            cursor.execute("""
                UPDATE dashboard_medicalrecord
                SET patient_id = NULL
                WHERE patient_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM dashboard_patient p 
                    WHERE p.id = dashboard_medicalrecord.patient_id
                )
            """)
            print(f'Fixed {count} orphaned medical records by setting patient_id to NULL')


def reverse_fix(apps, schema_editor):
    """
    Reverse migration - cannot restore deleted patient references
    """
    # Nothing to reverse - we can't restore deleted patient references
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0017_appointmentsettings'),
    ]

    operations = [
        migrations.RunPython(fix_orphaned_medical_records, reverse_fix),
    ]
