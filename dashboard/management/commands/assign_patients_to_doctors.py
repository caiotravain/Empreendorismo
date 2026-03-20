"""
Django management command to assign patients to a clinic.
Since patients are now shared within a clinic (not owned by a specific doctor),
this command assigns unassigned patients to a specified clinic.
"""
from django.core.management.base import BaseCommand
from dashboard.models import Patient, Clinic


class Command(BaseCommand):
    help = 'Assign unassigned patients to a clinic. Patients are shared within a clinic.'

    def add_arguments(self, parser):
        parser.add_argument('--clinic-name', type=str, help='Clinic name to assign patients to')
        parser.add_argument('--list-clinics', action='store_true', help='List all available clinics')

    def handle(self, *args, **options):
        if options.get('list_clinics'):
            clinics = Clinic.objects.filter(is_active=True)
            if clinics.exists():
                self.stdout.write('Available clinics:')
                for clinic in clinics:
                    self.stdout.write(f'  - {clinic.name} ({clinic.patients_count} patients, {clinic.doctors_count} doctors)')
            else:
                self.stdout.write(self.style.WARNING('No active clinics found.'))
            return

        unassigned_patients = Patient.objects.filter(clinic__isnull=True)

        if unassigned_patients.count() == 0:
            self.stdout.write(self.style.SUCCESS('No unassigned patients found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {unassigned_patients.count()} unassigned patients.'))

        if options.get('clinic_name'):
            try:
                clinic = Clinic.objects.get(name=options['clinic_name'])
            except Clinic.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Clinic "{options["clinic_name"]}" does not exist.'))
                self.stdout.write('Run with --list-clinics to see available clinics.')
                return

            count = unassigned_patients.update(clinic=clinic)
            self.stdout.write(self.style.SUCCESS(f'Successfully assigned {count} patients to clinic "{clinic.name}".'))
        else:
            self.stdout.write('Please specify --clinic-name or --list-clinics')
            self.stdout.write('\nTo assign all unassigned patients to a clinic, run:')
            self.stdout.write('  python manage.py assign_patients_to_doctors --clinic-name "<clinic name>"')
