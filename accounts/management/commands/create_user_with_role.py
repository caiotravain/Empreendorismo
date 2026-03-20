"""
Django management command to create users with specific roles.

Roles:
  doctor    - Creates a Doctor profile linked to a clinic. Use --clinic-name to specify
              the clinic (creates it if it does not exist). Use --clinic-admin to also
              grant clinic administrator privileges.
  secretary - Creates a Secretary profile linked to a clinic and assigned to a doctor.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from dashboard.models import Doctor, Secretary, Clinic
import getpass


class Command(BaseCommand):
    help = 'Create a user with a specific role (doctor or secretary)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the new user')
        parser.add_argument(
            '--role', type=str, choices=['doctor', 'secretary'],
            default='doctor', help='Role of the user (doctor or secretary)'
        )
        parser.add_argument('--email', type=str, help='Email address')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--medical-license', type=str, help='Medical license (for doctors)')
        parser.add_argument('--specialization', type=str, help='Specialization (for doctors)')
        parser.add_argument('--clinic-name', type=str, help='Clinic name to assign the user to (creates it if missing)')
        parser.add_argument('--clinic-admin', action='store_true', help='Grant clinic admin privileges (for doctors)')
        parser.add_argument('--doctor-username', type=str, help='Doctor username (for secretaries)')
        parser.add_argument('--phone', type=str, help='Phone number')
        parser.add_argument('--no-password', action='store_true', help='Skip password prompt')
        parser.add_argument('--set-password', type=str, help='Password (not recommended for security)')

    def _get_or_create_clinic(self, clinic_name):
        if not clinic_name:
            return None
        clinic, created = Clinic.objects.get_or_create(name=clinic_name)
        if created:
            self.stdout.write(self.style.WARNING(f'Created new clinic: "{clinic_name}"'))
        return clinic

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']
        email = options.get('email')
        first_name = options.get('first_name')
        last_name = options.get('last_name')
        phone = options.get('phone')

        if User.objects.filter(username=username).exists():
            raise CommandError(f'User "{username}" already exists.')

        if options.get('set_password'):
            password = options['set_password']
        elif options.get('no_password'):
            password = None
        else:
            password = getpass.getpass(f'Enter password for {username}: ')
            password2 = getpass.getpass('Enter password again: ')
            if password != password2:
                raise CommandError('Passwords do not match.')
            if not password:
                raise CommandError('Password cannot be empty.')

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email or '',
            first_name=first_name or '',
            last_name=last_name or ''
        )

        if role == 'doctor':
            medical_license = options.get('medical_license')
            specialization = options.get('specialization')

            if not medical_license:
                raise CommandError('--medical-license is required for doctors.')
            if not specialization:
                raise CommandError('--specialization is required for doctors.')

            clinic = self._get_or_create_clinic(options.get('clinic_name'))
            is_clinic_admin = options.get('clinic_admin', False)

            Doctor.objects.create(
                user=user,
                clinic=clinic,
                is_clinic_admin=is_clinic_admin,
                medical_license=medical_license,
                specialization=specialization,
                phone=phone or ''
            )

            admin_tag = ' [clinic admin]' if is_clinic_admin else ''
            clinic_tag = f' in clinic "{clinic.name}"' if clinic else ''
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created doctor "{username}" with license "{medical_license}"{clinic_tag}{admin_tag}.'
                )
            )

        elif role == 'secretary':
            doctor_username = options.get('doctor_username')

            if not doctor_username:
                raise CommandError('--doctor-username is required for secretaries.')

            try:
                doctor_user = User.objects.get(username=doctor_username)
                doctor = doctor_user.doctor_profile
            except User.DoesNotExist:
                raise CommandError(f'Doctor user "{doctor_username}" does not exist.')
            except AttributeError:
                raise CommandError(f'User "{doctor_username}" is not a doctor.')

            clinic = self._get_or_create_clinic(options.get('clinic_name')) or doctor.clinic

            secretary = Secretary.objects.create(
                user=user,
                clinic=clinic,
                phone=phone or ''
            )
            secretary.doctors.add(doctor)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created secretary "{username}" assigned to Dr. {doctor.user.get_full_name()}.'
                )
            )
