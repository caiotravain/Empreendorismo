"""
Django management command to create users with specific roles
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from dashboard.models import Doctor, Secretary, Admin
import getpass


class Command(BaseCommand):
    help = 'Create a user with a specific role (admin, doctor, or secretary)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the new user')
        parser.add_argument('--role', type=str, choices=['admin', 'doctor', 'secretary'], 
                          default='doctor', help='Role of the user (admin, doctor, or secretary)')
        parser.add_argument('--email', type=str, help='Email address')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--medical-license', type=str, help='Medical license (for doctors)')
        parser.add_argument('--specialization', type=str, help='Specialization (for doctors)')
        parser.add_argument('--doctor-username', type=str, help='Doctor username (for secretaries)')
        parser.add_argument('--admin-username', type=str, help='Admin username (for doctors to assign them to an admin)')
        parser.add_argument('--phone', type=str, help='Phone number')
        parser.add_argument('--no-password', action='store_true', help='Skip password prompt')
        parser.add_argument('--set-password', type=str, help='Password (not recommended for security)')

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']
        email = options.get('email')
        first_name = options.get('first_name')
        last_name = options.get('last_name')
        phone = options.get('phone')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User "{username}" already exists.')

        # Create user
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

        if role == 'admin':
            admin = Admin.objects.create(
                user=user,
                phone=phone or ''
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created admin user "{username}".'
                )
            )

        elif role == 'doctor':
            medical_license = options.get('medical_license')
            specialization = options.get('specialization')
            
            if not medical_license:
                raise CommandError('--medical-license is required for doctors.')
            if not specialization:
                raise CommandError('--specialization is required for doctors.')
            
            # Get admin if specified
            admin = None
            admin_username = options.get('admin_username')
            if admin_username:
                try:
                    admin_user = User.objects.get(username=admin_username)
                    if hasattr(admin_user, 'admin_profile'):
                        admin = admin_user.admin_profile
                    else:
                        raise CommandError(f'User "{admin_username}" is not an admin.')
                except User.DoesNotExist:
                    raise CommandError(f'Admin user "{admin_username}" does not exist.')
            
            doctor = Doctor.objects.create(
                user=user,
                admin=admin,
                medical_license=medical_license,
                specialization=specialization,
                phone=phone or ''
            )
            admin_msg = f' assigned to admin {admin.full_name}' if admin else ''
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created doctor "{username}" with medical license "{medical_license}"{admin_msg}.'
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
            
            secretary = Secretary.objects.create(
                user=user,
                doctor=doctor,
                phone=phone or ''
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created secretary "{username}" assigned to Dr. {doctor.user.get_full_name()}.'
                )
            )

