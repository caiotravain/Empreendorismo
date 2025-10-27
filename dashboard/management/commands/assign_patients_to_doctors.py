"""
Django management command to assign patients to doctors
"""
from django.core.management.base import BaseCommand
from dashboard.models import Patient, Doctor


class Command(BaseCommand):
    help = 'Assign patients to doctors. Assigns unassigned patients to a specified doctor.'

    def add_arguments(self, parser):
        parser.add_argument('--doctor-username', type=str, help='Doctor username to assign patients to')
        parser.add_argument('--all-doctors', action='store_true', help='Assign patients to all doctors evenly')

    def handle(self, *args, **options):
        unassigned_patients = Patient.objects.filter(doctor__isnull=True)
        
        if unassigned_patients.count() == 0:
            self.stdout.write(
                self.style.SUCCESS('No unassigned patients found.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Found {unassigned_patients.count()} unassigned patients.'
            )
        )
        
        if options.get('doctor_username'):
            # Assign to specific doctor
            try:
                from django.contrib.auth.models import User
                from dashboard.models import Doctor
                
                doctor_user = User.objects.get(username=options['doctor_username'])
                try:
                    doctor = doctor_user.doctor_profile
                except AttributeError:
                    self.stdout.write(
                        self.style.ERROR(
                            f'User "{options["doctor_username"]}" is not a doctor.'
                        )
                    )
                    return
                
                count = unassigned_patients.update(doctor=doctor)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully assigned {count} patients to Dr. {doctor.full_name}.'
                    )
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'Doctor user "{options["doctor_username"]}" does not exist.'
                    )
                )
        
        elif options.get('all_doctors'):
            # Assign to all doctors evenly
            all_doctors = Doctor.objects.filter(is_active=True)
            
            if all_doctors.count() == 0:
                self.stdout.write(
                    self.style.ERROR('No active doctors found.')
                )
                return
            
            self.stdout.write(
                self.style.WARNING(
                    f'Assigning {unassigned_patients.count()} patients to {all_doctors.count()} doctors evenly...'
                )
            )
            
            patients = list(unassigned_patients)
            doctors = list(all_doctors)
            
            for i, patient in enumerate(patients):
                doctor = doctors[i % len(doctors)]
                patient.doctor = doctor
                patient.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully assigned patients to {all_doctors.count()} doctors.'
                )
            )
        
        else:
            # Interactive mode
            from django.contrib.auth.models import User
            from dashboard.models import Doctor
            
            self.stdout.write('Please specify --doctor-username or --all-doctors')
            self.stdout.write('\nAvailable doctors:')
            for doctor in Doctor.objects.filter(is_active=True):
                self.stdout.write(f'  - {doctor.full_name} (username: {doctor.user.username})')
            self.stdout.write('\nTo assign all patients to a specific doctor, run:')
            self.stdout.write('  python manage.py assign_patients_to_doctors --doctor-username <username>')
            self.stdout.write('\nTo assign patients evenly to all doctors, run:')
            self.stdout.write('  python manage.py assign_patients_to_doctors --all-doctors')

