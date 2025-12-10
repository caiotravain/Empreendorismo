"""
Django management command to seed database with realistic data for a specific doctor.

Usage:
    python manage.py seed_doctor_data [--doctor-id DOCTOR_ID] [--create-doctor]

If --doctor-id is provided, uses that doctor. Otherwise, creates a new doctor.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from datetime import date, time, timedelta, datetime
from decimal import Decimal
import random

try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    print("Warning: Faker not installed. Install with: pip install Faker")
    print("Using basic data generation instead.")

from dashboard.models import (
    Doctor, Patient, Appointment, MedicalRecord, 
    Prescription, PrescriptionItem, Expense
)

# ============================================================================
# CONFIGURATION - Set your target Doctor ID here, or use command line args
# ============================================================================
TARGET_DOCTOR_ID = None  # Set to a specific Doctor ID, or None to use command line args

# ============================================================================
# Business hours configuration
# ============================================================================
BUSINESS_HOURS_START = 9  # 9 AM
BUSINESS_HOURS_END = 17    # 5 PM
APPOINTMENT_DURATIONS = [30, 45, 60]  # minutes


class Command(BaseCommand):
    help = 'Seed database with realistic data for a specific doctor'

    def add_arguments(self, parser):
        parser.add_argument(
            '--doctor-id',
            type=int,
            help='ID of the doctor to use (if not provided, will create a new doctor)',
        )
        parser.add_argument(
            '--create-doctor',
            action='store_true',
            help='Create a new doctor if doctor-id is not provided',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if FAKER_AVAILABLE:
            self.fake = Faker('pt_BR')  # Portuguese Brazil locale
        else:
            self.fake = None

    def handle(self, *args, **options):
        doctor_id = options.get('doctor_id') or TARGET_DOCTOR_ID
        create_doctor = options.get('create_doctor', False)

        try:
            with transaction.atomic():
                # Get or create doctor
                doctor = self.get_or_create_doctor(doctor_id, create_doctor)
                if not doctor:
                    self.stdout.write(self.style.ERROR('No doctor available. Exiting.'))
                    return

                self.stdout.write(self.style.SUCCESS(f'Using doctor: {doctor.full_name} (ID: {doctor.id})'))

                # Create patients
                self.stdout.write('\n📋 Creating 10 patients...')
                patients = self.create_patients(doctor, count=10)
                self.stdout.write(self.style.SUCCESS(f'✓ Created {len(patients)} patients'))

                # Create appointments for current month
                self.stdout.write('\n📅 Creating appointments for current month...')
                appointments = self.create_current_month_appointments(doctor, patients)
                self.stdout.write(self.style.SUCCESS(f'✓ Created {len(appointments)} appointments'))

                # Create past medical records
                self.stdout.write('\n📝 Creating past medical records (1-12 months ago)...')
                medical_records = self.create_past_medical_records(doctor, patients)
                self.stdout.write(self.style.SUCCESS(f'✓ Created {len(medical_records)} medical records'))

                # Create prescriptions linked to medical records/appointments
                self.stdout.write('\n💊 Creating prescriptions...')
                prescriptions = self.create_prescriptions(doctor, patients, medical_records, appointments)
                self.stdout.write(self.style.SUCCESS(f'✓ Created {len(prescriptions)} prescriptions'))

                # Create expenses
                self.stdout.write('\n💰 Creating expenses...')
                expenses = self.create_expenses(doctor)
                self.stdout.write(self.style.SUCCESS(f'✓ Created {len(expenses)} expenses'))

                # Summary
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('✅ Database seeding completed successfully!'))
                self.stdout.write('='*60)
                self.stdout.write(f'\nSummary:')
                self.stdout.write(f'  • Doctor: {doctor.full_name}')
                self.stdout.write(f'  • Patients: {len(patients)}')
                self.stdout.write(f'  • Appointments: {len(appointments)}')
                self.stdout.write(f'  • Medical Records: {len(medical_records)}')
                self.stdout.write(f'  • Prescriptions: {len(prescriptions)}')
                self.stdout.write(f'  • Expenses: {len(expenses)}')
                self.stdout.write('')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during seeding: {str(e)}'))
            import traceback
            traceback.print_exc()
            raise

    def get_or_create_doctor(self, doctor_id, create_doctor):
        """Get existing doctor or create a new one"""
        if doctor_id:
            try:
                #print all doctors
                self.stdout.write(self.style.SUCCESS(f'All doctors: {Doctor.objects.all().values()}'))
                doctor = Doctor.objects.get(id=doctor_id)
                self.stdout.write(f'Found existing doctor: {doctor.full_name}')
                return doctor
            except Doctor.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Doctor with ID {doctor_id} not found.'))
                if not create_doctor:
                    return None

        # Create a new doctor
        if not FAKER_AVAILABLE:
            username = f'dr.test{random.randint(1000, 9999)}'
            first_name = 'Test'
            last_name = 'Doctor'
            email = f'{username}@clinic.com'
        else:
            username = f'dr.{self.fake.user_name()}'
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            email = self.fake.email()

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'is_staff': True,
            }
        )
        if created:
            user.set_password('password123')
            user.save()

        doctor, created = Doctor.objects.get_or_create(
            user=user,
            defaults={
                'medical_license': f'CRM{random.randint(100000, 999999)}',
                'specialization': self.get_specialization(),
                'years_of_experience': random.randint(5, 30),
                'phone': self.get_phone_number(),
                'is_active': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created new doctor: {doctor.full_name}'))
            self.stdout.write(f'  Username: {username}')
            self.stdout.write(f'  Password: password123')

        return doctor

    def create_patients(self, doctor, count=10):
        """Create patients with realistic data"""
        patients = []
        genders = ['M', 'F', 'O']
        
        for i in range(count):
            if FAKER_AVAILABLE:
                first_name = self.fake.first_name()
                last_name = self.fake.last_name()
                email = self.fake.email()
                phone = self.get_phone_number()
                date_of_birth = self.fake.date_of_birth(minimum_age=18, maximum_age=80)
                gender = random.choice(genders)
                address = self.fake.address()
                city = self.fake.city()
                state = self.fake.state_abbr()
                zip_code = self.fake.postcode()
                emergency_name = self.fake.name()
                emergency_phone = self.get_phone_number()
                insurance = random.choice(['Unimed', 'Bradesco Saúde', 'SulAmérica', 'Amil', 'NotreDame', None])
            else:
                first_name = f'Patient{i+1}'
                last_name = f'Test{i+1}'
                email = f'patient{i+1}@test.com'
                phone = f'+5511{random.randint(900000000, 999999999)}'
                date_of_birth = date.today() - timedelta(days=random.randint(6570, 29200))  # 18-80 years
                gender = random.choice(genders)
                address = f'Rua Teste {i+1}, {random.randint(100, 999)}'
                city = 'São Paulo'
                state = 'SP'
                zip_code = f'{random.randint(10000, 99999)}-{random.randint(100, 999)}'
                emergency_name = f'Emergency Contact {i+1}'
                emergency_phone = f'+5511{random.randint(900000000, 999999999)}'
                insurance = random.choice(['Unimed', 'Bradesco Saúde', 'SulAmérica', 'Amil', None])

            patient = Patient.objects.create(
                doctor=doctor,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                emergency_contact_name=emergency_name,
                emergency_contact_phone=emergency_phone,
                medical_insurance=insurance,
                is_active=True,
            )
            patients.append(patient)

        return patients

    def create_current_month_appointments(self, doctor, patients):
        """Create appointments distributed throughout the current month"""
        appointments = []
        today = date.today()
        
        # Get first and last day of current month
        first_day = today.replace(day=1)
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        used_times = set()  # Track used time slots per day to avoid conflicts
        
        statuses = ['scheduled', 'confirmed', 'scheduled', 'confirmed', 'scheduled']  # More scheduled than confirmed
        appointment_types = ['consultation', 'follow_up', 'checkup', 'consultation', 'follow_up']
        payment_types = ['convenio', 'particular']
        
        # First, create more past appointments (before today) - 8-12 appointments
        num_past_appointments = random.randint(8, 12)
        self.stdout.write(f'  Creating {num_past_appointments} past appointments...')
        past_appointments_created = 0
        max_attempts = num_past_appointments * 10  # More attempts for more appointments
        
        # Track used slots for past appointments too (to prevent overlaps)
        past_used_slots = {}  # {(appointment_date, start_time): end_time}
        
        while past_appointments_created < num_past_appointments and max_attempts > 0:
            max_attempts -= 1
            
            # Pick a date in the past (1-30 days ago - wider range)
            days_ago = random.randint(1, 30)
            appointment_date = today - timedelta(days=days_ago)
            
            # Skip weekends (Saturday=5, Sunday=6)
            if appointment_date.weekday() >= 5:
                continue
            
            # Generate time slot (business hours)
            hour = random.randint(BUSINESS_HOURS_START, BUSINESS_HOURS_END - 1)
            minute = random.choice([0, 15, 30, 45])
            appointment_time = time(hour, minute)
            
            # Calculate appointment end time to check for overlaps
            duration = random.choice(APPOINTMENT_DURATIONS)
            start_datetime = datetime.combine(appointment_date, appointment_time)
            end_datetime = start_datetime + timedelta(minutes=duration)
            end_time = end_datetime.time()
            
            # Check for overlaps with existing past appointments
            overlaps = False
            for (existing_date, existing_start), existing_end in past_used_slots.items():
                if existing_date != appointment_date:
                    continue
                
                existing_start_dt = datetime.combine(appointment_date, existing_start)
                existing_end_dt = datetime.combine(appointment_date, existing_end)
                new_start_dt = datetime.combine(appointment_date, appointment_time)
                new_end_dt = datetime.combine(appointment_date, end_time)
                
                if (new_start_dt < existing_end_dt and new_end_dt > existing_start_dt):
                    overlaps = True
                    break
            
            if overlaps:
                continue
            
            # No overlap, track this slot
            past_used_slots[(appointment_date, appointment_time)] = end_time
            
            patient = random.choice(patients)
            duration = random.choice(APPOINTMENT_DURATIONS)
            appointment_type = random.choice(appointment_types)
            payment_type = random.choice(payment_types)
            
            # Generate value for all appointments
            value = Decimal(str(random.uniform(150.0, 500.0))).quantize(Decimal('0.01'))
            
            if FAKER_AVAILABLE:
                reason = self.fake.sentence(nb_words=6)
                notes = self.fake.sentence(nb_words=8) if random.random() > 0.5 else None
                location = random.choice(['Consultório 1', 'Consultório 2', 'Sala 101', 'Sala 102', 'Consultório Principal'])
            else:
                reason = f'Consulta de rotina - {appointment_type}'
                notes = 'Observações gerais' if random.random() > 0.5 else None
                location = 'Consultório'

            appointment = Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                duration_minutes=duration,
                appointment_type=appointment_type,
                payment_type=payment_type,
                status='completed',  # Past appointments are confirmed
                value=value,
                reason=reason,
                notes=notes,
                location=location,
            )
            appointments.append(appointment)
            past_appointments_created += 1
        
        # Now create more appointments for the near future (next 3-4 weeks)
        # Generate 7-11 appointments per week (slightly more appointments in near future)
        appointments_per_week = random.randint(7, 11)
        weeks_ahead = 4  # Focus on next 4 weeks (slightly extended)
        total_appointments = appointments_per_week * weeks_ahead
        
        # Track used time slots with duration to prevent overlaps
        # Format: {(date, start_time): end_time}
        used_slots = {}  # {(appointment_date, start_time): end_time}
        
        max_attempts_per_appointment = 50  # Prevent infinite loops
        
        for _ in range(total_appointments):
            attempts = 0
            appointment_created = False
            
            while attempts < max_attempts_per_appointment and not appointment_created:
                attempts += 1
                
                # Pick a date in the near future (1-28 days ahead, focusing on next 4 weeks)
                # Weight towards earlier dates (more appointments sooner)
                days_ahead = random.choices(
                    range(1, 29),  # 1-28 days ahead (4 weeks)
                    weights=[10, 10, 9, 9, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # More weight on earlier days
                )[0]
                
                appointment_date = today + timedelta(days=days_ahead)
                
                # Skip weekends (Saturday=5, Sunday=6)
                if appointment_date.weekday() >= 5:
                    continue
                
                # Skip if beyond end of month
                if appointment_date > last_day:
                    continue
                
                # Generate time slot (business hours)
                hour = random.randint(BUSINESS_HOURS_START, BUSINESS_HOURS_END - 1)
                minute = random.choice([0, 15, 30, 45])
                appointment_time = time(hour, minute)
                
                # Calculate appointment end time
                duration = random.choice(APPOINTMENT_DURATIONS)
                start_datetime = datetime.combine(appointment_date, appointment_time)
                end_datetime = start_datetime + timedelta(minutes=duration)
                end_time = end_datetime.time()
                
                # Check for overlaps with existing appointments
                # An appointment overlaps if:
                # 1. Same date
                # 2. Start time is within another appointment's duration, OR
                # 3. End time is within another appointment's duration, OR
                # 4. It completely contains another appointment
                overlaps = False
                for (existing_date, existing_start), existing_end in used_slots.items():
                    if existing_date != appointment_date:
                        continue
                    
                    # Convert times to datetime for comparison
                    existing_start_dt = datetime.combine(appointment_date, existing_start)
                    existing_end_dt = datetime.combine(appointment_date, existing_end)
                    new_start_dt = datetime.combine(appointment_date, appointment_time)
                    new_end_dt = datetime.combine(appointment_date, end_time)
                    
                    # Check if appointments overlap
                    if (new_start_dt < existing_end_dt and new_end_dt > existing_start_dt):
                        overlaps = True
                        break
                
                if overlaps:
                    continue
                
                # No overlap found, create the appointment
                used_slots[(appointment_date, appointment_time)] = end_time
                
                patient = random.choice(patients)
                status = random.choice(statuses)
                appointment_type = random.choice(appointment_types)
                payment_type = random.choice(payment_types)
                
                # Generate value for all appointments
                value = Decimal(str(random.uniform(150.0, 500.0))).quantize(Decimal('0.01'))
                
                if FAKER_AVAILABLE:
                    reason = self.fake.sentence(nb_words=6)
                    notes = self.fake.sentence(nb_words=8) if random.random() > 0.5 else None
                    location = random.choice(['Consultório 1', 'Consultório 2', 'Sala 101', 'Sala 102', 'Consultório Principal'])
                else:
                    reason = f'Consulta de rotina - {appointment_type}'
                    notes = 'Observações gerais' if random.random() > 0.5 else None
                    location = 'Consultório'

                appointment = Appointment.objects.create(
                    doctor=doctor,
                    patient=patient,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    duration_minutes=duration,
                    appointment_type=appointment_type,
                    payment_type=payment_type,
                    status=status,
                    value=value,
                    reason=reason,
                    notes=notes,
                    location=location,
                )
                appointments.append(appointment)
                appointment_created = True

        return appointments

    def create_past_medical_records(self, doctor, patients):
        """Create medical records dated 1-12 months ago"""
        medical_records = []
        now = timezone.now()
        
        # Create 2-4 records per patient
        for patient in patients:
            num_records = random.randint(2, 4)
            
            for _ in range(num_records):
                # Random date between 1 and 12 months ago
                months_ago = random.randint(1, 12)
                days_ago = random.randint(months_ago * 30 - 15, months_ago * 30 + 15)
                record_datetime = now - timedelta(days=days_ago)
                
                # Generate realistic medical record content
                if FAKER_AVAILABLE:
                    content = self.generate_medical_record_content(doctor)
                else:
                    content = self.generate_basic_medical_record_content(patient, doctor)
                
                medical_record = MedicalRecord.objects.create(
                    doctor=doctor,
                    patient=patient,
                    datetime=record_datetime,
                    content=content,
                )
                medical_records.append(medical_record)

        return medical_records

    def create_prescriptions(self, doctor, patients, medical_records, appointments):
        """Create prescriptions linked to medical records and appointments"""
        prescriptions = []
        
        # Medications database (common Brazilian medications)
        medications = [
            {'name': 'Losartana', 'dosage': '50mg', 'common_quantity': '30 comprimidos'},
            {'name': 'Metformina', 'dosage': '500mg', 'common_quantity': '60 comprimidos'},
            {'name': 'Atenolol', 'dosage': '25mg', 'common_quantity': '30 comprimidos'},
            {'name': 'Captopril', 'dosage': '25mg', 'common_quantity': '30 comprimidos'},
            {'name': 'Enalapril', 'dosage': '10mg', 'common_quantity': '30 comprimidos'},
            {'name': 'Omeprazol', 'dosage': '20mg', 'common_quantity': '30 cápsulas'},
            {'name': 'Dipirona', 'dosage': '500mg', 'common_quantity': '20 comprimidos'},
            {'name': 'Paracetamol', 'dosage': '750mg', 'common_quantity': '20 comprimidos'},
            {'name': 'Ibuprofeno', 'dosage': '400mg', 'common_quantity': '20 comprimidos'},
            {'name': 'Amoxicilina', 'dosage': '500mg', 'common_quantity': '21 cápsulas'},
        ]
        
        # Create prescriptions for some medical records and appointments
        # Link to medical records (past prescriptions)
        for medical_record in random.sample(medical_records, min(len(medical_records), len(patients) * 2)):
            prescription_date = medical_record.datetime.date()
            
            # Create prescription with 1-3 medications
            num_medications = random.randint(1, 3)
            selected_medications = random.sample(medications, min(num_medications, len(medications)))
            
            prescription = Prescription.objects.create(
                doctor=doctor,
                patient=medical_record.patient,
                prescription_date=prescription_date,
                status=random.choice(['active']),
                notes=f'Prescrição gerada durante consulta em {prescription_date.strftime("%d/%m/%Y")}',
            )
            
            # Add prescription items
            for idx, med in enumerate(selected_medications):
                dosage_instructions = [
                    '1 comprimido de 8/8 horas',
                    '1 comprimido de 12/12 horas',
                    '1 comprimido ao dia',
                    '1 comprimido de 6/6 horas',
                    '2 comprimidos ao dia',
                ]
                
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    medication_name=med['name'],
                    quantity=med['common_quantity'],
                    dosage=random.choice(dosage_instructions),
                    notes=f'Tomar com água' if random.random() > 0.7 else None,
                    order=idx,
                )
            
            prescriptions.append(prescription)
        
        # Link to some appointments (recent prescriptions)
        for appointment in random.sample(appointments, min(len(appointments) // 3, len(patients))):
            if appointment.status in ['completed', 'confirmed']:
                prescription = Prescription.objects.create(
                    doctor=doctor,
                    patient=appointment.patient,
                    prescription_date=appointment.appointment_date,
                    status='active',
                    notes=f'Prescrição gerada durante consulta agendada para {appointment.appointment_date.strftime("%d/%m/%Y")}',
                )
                
                # Add 1-2 medications
                num_medications = random.randint(1, 2)
                selected_medications = random.sample(medications, min(num_medications, len(medications)))
                
                for idx, med in enumerate(selected_medications):
                    dosage_instructions = [
                        '1 comprimido de 8/8 horas',
                        '1 comprimido de 12/12 horas',
                        '1 comprimido ao dia',
                    ]
                    
                    PrescriptionItem.objects.create(
                        prescription=prescription,
                        medication_name=med['name'],
                        quantity=med['common_quantity'],
                        dosage=random.choice(dosage_instructions),
                        order=idx,
                    )
                
                prescriptions.append(prescription)

        return prescriptions

    def generate_medical_record_content(self, doctor):
        """Generate realistic and detailed medical record content using Faker"""
        templates = [
            """CONSULTA DE ROTINA

Paciente apresentou-se para consulta de rotina em bom estado geral. 

ANAMNESE:
{complaint} Início dos sintomas há aproximadamente {symptom_duration} dias. Intensidade {symptom_intensity}. 
Histórico familiar: {family_history}. Alergias conhecidas: {allergies}. Medicações em uso: {current_medications}.

EXAME FÍSICO:
Estado geral: {general_state}
Pressão arterial: {bp} mmHg
Frequência cardíaca: {heart_rate} bpm
Frequência respiratória: {resp_rate} ipm
Temperatura: {temperature}°C
Peso: {weight}kg
Altura: {height}m
IMC: {bmi:.1f} ({bmi_classification})
Ausculta cardíaca: {heart_auscultation}
Ausculta pulmonar: {lung_auscultation}
Abdome: {abdomen_exam}
Extremidades: {extremities_exam}

EXAMES COMPLEMENTARES:
{exams}

HIPÓTESE DIAGNÓSTICA:
{diagnosis}

CONDUTA:
Prescrito {medication}. Orientações sobre {advice}. 
Retorno em {days} dias ou retorno imediato em caso de {warning_signs}.

Dr. {doctor_name}
CRM: {crm}""",

            """CONSULTA DE RETORNO

{condition}

ANAMNESE:
Paciente retorna para acompanhamento. Relata {status}. 
Evolução desde última consulta: {evolution}. 
Adesão ao tratamento: {adherence}. Efeitos colaterais: {side_effects}.

EXAME FÍSICO:
{exams}
Pressão arterial: {bp} mmHg
Peso: {weight}kg
Avaliação geral: {general_assessment}

AVALIAÇÃO LABORATORIAL:
{lab_results}

EVOLUÇÃO:
{treatment}

ORIENTAÇÕES:
Orientações sobre {advice}. Manutenção de {lifestyle_advice}. 
Importância de {important_note}.

RETORNO:
Retorno em {days} dias para reavaliação.

Dr. {doctor_name}
CRM: {crm}""",

            """PRIMEIRA CONSULTA

Paciente em primeira consulta. Queixa principal: {main_complaint}.

ANAMNESE COMPLETA:
Histórico familiar: {history}
Histórico pessoal: {personal_history}
Medicações prévias: {previous_medications}
Cirurgias prévias: {previous_surgeries}
Hábitos: {habits}
Alergias: {allergies}

EXAME FÍSICO:
{physical_exam}

EXAMES SOLICITADOS:
Exames laboratoriais: {tests}
Exames de imagem: {imaging_tests}
Outros exames: {other_tests}

HIPÓTESE DIAGNÓSTICA:
{diagnosis}

PLANO TERAPÊUTICO:
{instructions}
Orientações sobre dieta e exercícios físicos.
Importância do seguimento regular.

RETORNO:
Retorno em {days} dias com resultados dos exames.

Dr. {doctor_name}
CRM: {crm}""",

            """CONSULTA DE EMERGÊNCIA

Paciente com {symptom}. Início há {symptom_duration_hours} horas.

ANAMNESE:
Queixa principal: {symptom}
Histórico relevante: {relevant_history}
Medicações em uso: {current_medications}
Alergias: {allergies}

EXAME FÍSICO URGENTE:
{examination}
Pressão arterial: {bp} mmHg
Frequência cardíaca: {heart_rate} bpm
Saturação de O2: {oxygen_sat}%
Estado de consciência: {consciousness}

EXAMES SOLICITADOS:
{tests_requested}

DIAGNÓSTICO PROVISÓRIO:
{provisional_diagnosis}

CONDUTA IMEDIATA:
{prescription}
Observação: {observation_instructions}

ORIENTAÇÕES:
Retorno imediato em caso de {warning_signs}.
Retorno em {days} dias para reavaliação.

Dr. {doctor_name}
CRM: {crm}"""
        ]
        
        template = random.choice(templates)
        
        bp_systolic = random.randint(110, 160)
        bp_diastolic = random.randint(70, 100)
        weight = random.randint(50, 100)
        height = random.uniform(1.50, 1.90)
        bmi = weight / (height ** 2)
        bmi_classification = "Normal" if 18.5 <= bmi < 25 else ("Sobrepeso" if 25 <= bmi < 30 else "Obesidade")
        
        complaints = [
            "Paciente relata dores de cabeça ocasionais, principalmente no período da manhã",
            "Paciente relata fadiga e cansaço excessivo ao realizar atividades do dia a dia",
            "Paciente relata dores musculares generalizadas, principalmente em membros inferiores",
            "Paciente relata tonturas ao levantar-se rapidamente",
            "Paciente sem queixas específicas, busca avaliação de rotina"
        ]
        
        conditions = [
            "Paciente diabético tipo 2 em acompanhamento",
            "Paciente hipertenso em tratamento",
            "Paciente com histórico de hipertensão arterial controlada",
            "Paciente com asma brônquica leve a moderada"
        ]
        
        medications = ["Losartana 50mg 1x/dia", "Metformina 500mg 2x/dia", "Captopril 25mg 2x/dia", "Enalapril 10mg 1x/dia"]
        
        tests = ["hemograma completo", "glicemia de jejum", "colesterol total e frações", "creatinina", "uréia", "TSH", "T3 livre", "T4 livre", "ácido úrico", "transaminases"]
        
        return template.format(
            bp=f"{bp_systolic}/{bp_diastolic}",
            weight=weight,
            height=height,
            bmi=bmi,
            bmi_classification=bmi_classification,
            complaint=random.choice(complaints),
            symptom_duration=random.randint(1, 30),  # days for routine, hours for emergency (handled in template)
            symptom_duration_hours=random.randint(1, 48),  # hours for emergency consultations
            symptom_intensity=random.choice(["leve", "moderada", "intensa"]),
            family_history=random.choice(["hipertensão familiar", "diabetes familiar", "doenças cardíacas", "sem histórico relevante"]),
            allergies=random.choice(["nenhuma conhecida", "penicilina", "dipirona", "sem alergias conhecidas"]),
            current_medications=random.choice(["nenhuma", "Losartana 50mg", "Metformina 500mg", "sem medicações regulares"]),
            general_state=random.choice(["bom", "regular", "ótimo"]),
            heart_rate=random.randint(60, 100),
            resp_rate=random.randint(14, 20),
            temperature=round(random.uniform(36.0, 37.2), 1),
            heart_auscultation=random.choice(["ritmo regular, bulhas normais", "ritmo regular, sopro sistólico leve", "ritmo regular, sem sopros"]),
            lung_auscultation=random.choice(["MV+ bilateral, sem ruídos adventícios", "MV+ bilateral, crepitações finas", "MV+ bilateral, normal"]),
            abdomen_exam=random.choice(["abdome plano, indolor à palpação", "abdome globoso, indolor", "abdome normal"]),
            extremities_exam=random.choice(["sem edemas", "edema discreto em membros inferiores", "extremidades normais"]),
            exams=random.choice([
                f"Glicemia de jejum: {random.randint(80, 150)} mg/dL. HbA1c: {random.uniform(5.5, 9.0):.1f}%.",
                f"Exame físico normal. Pressão arterial controlada: {bp_systolic}/{bp_diastolic} mmHg.",
                f"Exames laboratoriais dentro da normalidade. Pressão arterial: {bp_systolic}/{bp_diastolic} mmHg."
            ]),
            medication=random.choice(medications),
            days=random.randint(7, 30),
            condition=random.choice(conditions),
            status=random.choice(["aderência adequada ao tratamento", "melhora significativa dos sintomas", "sintomas controlados", "evolução favorável"]),
            evolution=random.choice(["favorável", "estável", "melhora progressiva"]),
            adherence=random.choice(["boa", "excelente", "regular"]),
            side_effects=random.choice(["nenhum relatado", "leve tontura ocasional", "sem efeitos colaterais"]),
            general_assessment=random.choice(["bom estado geral", "estado geral regular", "estado geral satisfatório"]),
            lab_results=random.choice([
                f"Glicemia: {random.randint(80, 120)} mg/dL. Colesterol total: {random.randint(150, 220)} mg/dL.",
                "Exames laboratoriais dentro dos parâmetros normais.",
                f"Creatinina: {random.uniform(0.7, 1.2):.2f} mg/dL. Função renal preservada."
            ]),
            treatment=random.choice([
                "Ajuste na dosagem da medicação conforme necessidade.",
                "Manutenção do tratamento atual com boa resposta.",
                "Novo tratamento iniciado com acompanhamento necessário."
            ]),
            advice=random.choice(["dieta balanceada", "exercícios físicos regulares", "monitoramento glicêmico", "atividade física moderada"]),
            lifestyle_advice=random.choice(["alimentação saudável", "exercícios regulares", "medicação conforme prescrição"]),
            important_note=random.choice(["seguimento regular", "monitoramento da pressão arterial", "controle glicêmico"]),
            history=random.choice(["hipertensão familiar", "diabetes familiar", "doenças cardíacas", "sem histórico relevante"]),
            personal_history=random.choice(["hipertensão arterial", "diabetes tipo 2", "asma", "sem antecedentes relevantes"]),
            previous_medications=random.choice(["nenhuma", "anti-hipertensivos", "antidiabéticos", "sem medicações prévias"]),
            previous_surgeries=random.choice(["nenhuma", "colecistectomia", "apendicectomia", "sem cirurgias prévias"]),
            habits=random.choice(["não tabagista, etilismo social", "tabagismo leve", "sem hábitos deletérios"]),
            tests=", ".join(random.sample(tests, random.randint(4, 6))),
            imaging_tests=random.choice(["radiografia de tórax", "ultrassonografia abdominal", "ecocardiograma", "nenhum solicitado"]),
            other_tests=random.choice(["eletrocardiograma", "teste ergométrico", "nenhum"]),
            diagnosis=random.choice([
                "Hipertensão arterial essencial",
                "Diabetes mellitus tipo 2",
                "Síndrome metabólica",
                "Hipertensão arterial estágio 1"
            ]),
            instructions=random.choice([
                "Orientações sobre dieta e exercícios físicos. Redução de sódio na alimentação.",
                "Orientações sobre sono e alimentação. Prática regular de atividade física.",
                "Orientações gerais sobre estilo de vida saudável."
            ]),
            symptom=random.choice(["dor torácica", "dor abdominal", "febre", "tosse persistente", "dispneia"]),
            relevant_history=random.choice(["hipertensão", "diabetes", "doenças cardíacas", "sem histórico relevante"]),
            oxygen_sat=random.randint(94, 99),
            consciousness=random.choice(["consciente, orientado", "consciente, lúcido", "consciente"]),
            provisional_diagnosis=random.choice([
                "Síndrome dolorosa torácica a esclarecer",
                "Dor abdominal inespecífica",
                "Síndrome gripal",
                "Crise hipertensiva"
            ]),
            observation_instructions=random.choice([
                "Manter repouso relativo",
                "Manter hidratação adequada",
                "Observar evolução dos sintomas"
            ]),
            warning_signs=random.choice([
                "piora dos sintomas",
                "dor intensa",
                "febre persistente",
                "dificuldade respiratória"
            ]),
            main_complaint=random.choice([
                "avaliação de rotina",
                "dor de cabeça frequente",
                "fadiga excessiva",
                "dor no peito"
            ]),
            examination=random.choice([
                "Eletrocardiograma normal. Ausculta cardíaca: ritmo regular, bulhas normais. Ausculta pulmonar: MV+ bilateral.",
                "Exame físico normal. Ausculta cardíaca e pulmonar sem alterações.",
                "Ausculta cardíaca normal. Ausculta pulmonar: MV+ bilateral, sem ruídos adventícios."
            ]),
            physical_exam=random.choice([
                f"Pressão arterial: {random.randint(110, 160)}/{random.randint(70, 100)} mmHg. Frequência cardíaca: {random.randint(60, 100)} bpm. Ausculta cardíaca: ritmo regular. Ausculta pulmonar: MV+ bilateral.",
                f"Exame físico geral: normal. Pressão arterial: {random.randint(110, 160)}/{random.randint(70, 100)} mmHg. Abdome: plano, indolor.",
                f"Estado geral: bom. Pressão arterial: {random.randint(110, 160)}/{random.randint(70, 100)} mmHg. Exame físico sem alterações."
            ]),
            tests_requested=random.choice([
                "Exames cardiológicos solicitados: ecocardiograma, teste ergométrico. Exames laboratoriais: hemograma, glicemia.",
                "Exames laboratoriais solicitados: hemograma completo, glicemia, creatinina, uréia. Eletrocardiograma.",
                "Exames de imagem: radiografia de tórax. Exames laboratoriais: hemograma, glicemia, colesterol."
            ]),
            prescription=random.choice([
                f"Prescrito {random.choice(medications)}.",
                "Medicação ajustada conforme necessidade.",
                f"Prescrito {random.choice(medications)}. Observação clínica necessária."
            ]),
            doctor_name=doctor.full_name,
            crm=doctor.medical_license
        )

    def generate_basic_medical_record_content(self, patient, doctor):
        """Generate basic but longer medical record content without Faker"""
        templates = [
            f"""CONSULTA DE ROTINA

Paciente {patient.full_name} apresentou-se para consulta de rotina em bom estado geral.

ANAMNESE:
Paciente relata {random.choice(['dores de cabeça ocasionais', 'fadiga', 'sem queixas específicas'])}. 
Histórico familiar: {random.choice(['hipertensão familiar', 'diabetes familiar', 'sem histórico relevante'])}.

EXAME FÍSICO:
Pressão arterial: {random.randint(110, 160)}/{random.randint(70, 100)} mmHg
Frequência cardíaca: {random.randint(60, 100)} bpm
Peso: {random.randint(50, 100)}kg
Altura: {random.uniform(1.50, 1.90):.2f}m
Ausculta cardíaca: ritmo regular, bulhas normais
Ausculta pulmonar: MV+ bilateral, sem ruídos adventícios
Abdome: plano, indolor à palpação

CONDUTA:
Exame físico normal. Orientações gerais fornecidas sobre {random.choice(['dieta', 'exercícios físicos', 'estilo de vida saudável'])}.
Retorno em {random.randint(15, 30)} dias.""",

            f"""CONSULTA DE RETORNO

Paciente {patient.full_name} retorna para acompanhamento.

ANAMNESE:
Paciente relata melhora dos sintomas. Evolução favorável desde última consulta.
Adesão ao tratamento: {random.choice(['boa', 'excelente'])}.

EXAME FÍSICO:
Pressão arterial: {random.randint(110, 140)}/{random.randint(70, 90)} mmHg (controlada)
Peso: {random.randint(50, 100)}kg
Estado geral: bom

CONDUTA:
Pressão arterial controlada. Manutenção do tratamento atual.
Orientações sobre {random.choice(['dieta balanceada', 'exercícios regulares', 'medicação conforme prescrição'])}.
Retorno em {random.randint(15, 30)} dias.""",

            f"""PRIMEIRA CONSULTA

Paciente {patient.full_name} em primeira consulta.

ANAMNESE:
Histórico familiar: {random.choice(['hipertensão familiar', 'diabetes familiar', 'doenças cardíacas'])}.
Medicações prévias: {random.choice(['nenhuma', 'anti-hipertensivos'])}.
Alergias: {random.choice(['nenhuma conhecida', 'sem alergias'])}.

EXAME FÍSICO:
Pressão arterial: {random.randint(110, 160)}/{random.randint(70, 100)} mmHg
Peso: {random.randint(50, 100)}kg
Exame físico geral: normal

EXAMES SOLICITADOS:
Exames laboratoriais: hemograma completo, glicemia, colesterol total, creatinina, uréia, TSH

CONDUTA:
Orientações sobre dieta e exercícios físicos. Importância do seguimento regular.
Retorno em {random.randint(15, 30)} dias com resultados dos exames."""
        ]
        return random.choice(templates)

    def get_specialization(self):
        """Get a random medical specialization"""
        specializations = [
            'Cardiologia', 'Clínica Geral', 'Endocrinologia', 'Ginecologia',
            'Ortopedia', 'Pediatria', 'Psiquiatria', 'Dermatologia',
            'Neurologia', 'Oftalmologia', 'Otorrinolaringologia', 'Urologia'
        ]
        if FAKER_AVAILABLE:
            return random.choice(specializations)
        return 'Clínica Geral'

    def get_phone_number(self):
        """Generate a Brazilian phone number"""
        if FAKER_AVAILABLE:
            return self.fake.phone_number()
        return f'+5511{random.randint(900000000, 999999999)}'

    def create_expenses(self, doctor):
        """Create expenses for the doctor distributed over the past 6 months and current month"""
        expenses = []
        today = date.today()
        
        # Expense categories with descriptions and amounts
        expense_templates = {
            'office_supplies': [
                {'desc': 'Papel A4 para impressora', 'amount_range': (50, 150)},
                {'desc': 'Canetas e material de escritório', 'amount_range': (30, 100)},
                {'desc': 'Pastas e organizadores', 'amount_range': (40, 120)},
                {'desc': 'Toner para impressora', 'amount_range': (200, 400)},
            ],
            'medical_supplies': [
                {'desc': 'Luvas descartáveis', 'amount_range': (80, 200)},
                {'desc': 'Máscaras cirúrgicas', 'amount_range': (50, 150)},
                {'desc': 'Algodão e gaze', 'amount_range': (30, 100)},
                {'desc': 'Seringas e agulhas', 'amount_range': (60, 180)},
                {'desc': 'Álcool e antissépticos', 'amount_range': (40, 120)},
            ],
            'equipment': [
                {'desc': 'Estetoscópio', 'amount_range': (300, 800)},
                {'desc': 'Esfigmomanômetro digital', 'amount_range': (200, 500)},
                {'desc': 'Termômetro digital', 'amount_range': (50, 150)},
                {'desc': 'Otoscópio', 'amount_range': (400, 1000)},
            ],
            'utilities': [
                {'desc': 'Conta de energia elétrica', 'amount_range': (200, 500)},
                {'desc': 'Conta de água', 'amount_range': (80, 200)},
                {'desc': 'Internet e telefone', 'amount_range': (150, 300)},
            ],
            'rent': [
                {'desc': 'Aluguel do consultório', 'amount_range': (2000, 5000)},
            ],
            'insurance': [
                {'desc': 'Seguro profissional', 'amount_range': (500, 1500)},
                {'desc': 'Seguro do consultório', 'amount_range': (300, 800)},
            ],
            'marketing': [
                {'desc': 'Anúncios online', 'amount_range': (200, 600)},
                {'desc': 'Material gráfico e panfletos', 'amount_range': (150, 400)},
                {'desc': 'Site e hospedagem', 'amount_range': (100, 300)},
            ],
            'professional_services': [
                {'desc': 'Serviço de contabilidade', 'amount_range': (300, 800)},
                {'desc': 'Advogado', 'amount_range': (500, 1500)},
                {'desc': 'Serviço de limpeza', 'amount_range': (200, 500)},
            ],
            'travel': [
                {'desc': 'Combustível', 'amount_range': (150, 400)},
                {'desc': 'Estacionamento', 'amount_range': (50, 200)},
                {'desc': 'Passagens aéreas para congresso', 'amount_range': (800, 2000)},
            ],
            'education': [
                {'desc': 'Curso de atualização médica', 'amount_range': (500, 2000)},
                {'desc': 'Inscrição em congresso', 'amount_range': (300, 1000)},
                {'desc': 'Livros e materiais de estudo', 'amount_range': (100, 400)},
            ],
            'other': [
                {'desc': 'Manutenção do ar condicionado', 'amount_range': (200, 500)},
                {'desc': 'Manutenção de equipamentos', 'amount_range': (300, 800)},
                {'desc': 'Despesas diversas', 'amount_range': (100, 300)},
            ],
        }
        
        # Generate 3 expenses per month for the past 6 months AND current month (7 months total)
        from calendar import monthrange
        
        for month_offset in range(7):  # 0 = current month, 1-6 = past months
            # Calculate the target month
            target_year = today.year
            target_month = today.month - month_offset
            
            # Handle year rollover
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            # First day of the month
            month_start = date(target_year, target_month, 1)
            
            # Last day of the month
            _, last_day = monthrange(target_year, target_month)
            month_end = date(target_year, target_month, last_day)
            
            # For current month, don't go beyond today
            if month_offset == 0:
                month_end = min(month_end, today)
            
            # Generate 3 expenses for this month
            for _ in range(3):
                # Pick random category
                category = random.choice(list(expense_templates.keys()))
                template = random.choice(expense_templates[category])
                
                # Generate expense date within the month
                days_between = (month_end - month_start).days
                if days_between <= 0:
                    # Skip if no valid days in month
                    continue
                
                random_days = random.randint(0, days_between)
                expense_date = month_start + timedelta(days=random_days)
                
                # Ensure we don't create expenses in the future
                if expense_date > today:
                    expense_date = today - timedelta(days=random.randint(0, min(7, (today - month_start).days)))
                
                # Generate amount
                amount = Decimal(str(random.uniform(*template['amount_range']))).quantize(Decimal('0.01'))
                
                # Generate vendor
                if FAKER_AVAILABLE:
                    vendor = self.fake.company()
                    notes = self.fake.sentence(nb_words=6) if random.random() > 0.6 else None
                else:
                    vendors_by_category = {
                        'office_supplies': ['Papelaria Central', 'Materiais de Escritório Ltda'],
                        'medical_supplies': ['MedSupply Brasil', 'Equipamentos Médicos SA'],
                        'equipment': ['MedTech Equipamentos', 'Hospitalar Brasil'],
                        'utilities': ['Companhia de Energia', 'Água e Saneamento'],
                        'rent': ['Imobiliária Central', 'Propriedades SA'],
                        'insurance': ['Seguros Médicos', 'Proteção Profissional'],
                        'marketing': ['Agência Digital', 'Marketing Solutions'],
                        'professional_services': ['Serviços Contábeis', 'Consultoria Jurídica'],
                        'travel': ['Posto de Combustível', 'Aeroporto'],
                        'education': ['Instituto Médico', 'Academia de Medicina'],
                        'other': ['Serviços Gerais', 'Manutenção Express'],
                    }
                    vendor = random.choice(vendors_by_category.get(category, ['Fornecedor']))
                    notes = 'Despesa regular' if random.random() > 0.6 else None
                
                # Generate receipt number
                receipt_number = f'NF-{random.randint(1000, 9999)}-{random.randint(100, 999)}' if random.random() > 0.3 else None
                
                expense = Expense.objects.create(
                    doctor=doctor,
                    amount=amount,
                    description=template['desc'],
                    category=category,
                    expense_date=expense_date,
                    notes=notes,
                    receipt_number=receipt_number,
                    vendor=vendor,
                )
                expenses.append(expense)
        
        return expenses


