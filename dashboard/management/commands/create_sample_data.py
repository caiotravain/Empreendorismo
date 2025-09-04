from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, time, timedelta
from dashboard.models import Patient, Doctor, Appointment, MedicalRecord


class Command(BaseCommand):
    help = 'Create sample data for testing the medical dashboard'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create a doctor user
        doctor_user, created = User.objects.get_or_create(
            username='dr.santos',
            defaults={
                'first_name': 'João',
                'last_name': 'Santos',
                'email': 'dr.santos@clinic.com',
                'is_staff': True,
            }
        )
        if created:
            doctor_user.set_password('password123')
            doctor_user.save()
            self.stdout.write(f'Created doctor user: {doctor_user.username}')
        
        # Create doctor profile
        doctor, created = Doctor.objects.get_or_create(
            user=doctor_user,
            defaults={
                'medical_license': 'CRM123456',
                'specialization': 'Cardiology',
                'years_of_experience': 10,
                'hospital_affiliation': 'Hospital São Paulo',
                'phone': '+5511999999999',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'Created doctor profile: {doctor.full_name}')
        
        # Create patients
        patients_data = [
            {
                'first_name': 'Maria',
                'last_name': 'Silva',
                'email': 'maria.silva@email.com',
                'phone': '+5511888888888',
                'date_of_birth': date(1985, 3, 15),
                'gender': 'F',
                'address': 'Rua das Flores, 123',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01234-567',
                'emergency_contact_name': 'José Silva',
                'emergency_contact_phone': '+5511777777777',
                'medical_insurance': 'Unimed',
            },
            {
                'first_name': 'João',
                'last_name': 'Santos',
                'email': 'joao.santos@email.com',
                'phone': '+5511666666666',
                'date_of_birth': date(1978, 7, 22),
                'gender': 'M',
                'address': 'Av. Paulista, 456',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01310-100',
                'emergency_contact_name': 'Ana Santos',
                'emergency_contact_phone': '+5511555555555',
                'medical_insurance': 'Bradesco Saúde',
            },
            {
                'first_name': 'Ana',
                'last_name': 'Costa',
                'email': 'ana.costa@email.com',
                'phone': '+5511444444444',
                'date_of_birth': date(1992, 11, 8),
                'gender': 'F',
                'address': 'Rua Augusta, 789',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01305-000',
                'emergency_contact_name': 'Carlos Costa',
                'emergency_contact_phone': '+5511333333333',
                'medical_insurance': 'SulAmérica',
            },
            {
                'first_name': 'Pedro',
                'last_name': 'Oliveira',
                'email': 'pedro.oliveira@email.com',
                'phone': '+5511222222222',
                'date_of_birth': date(1965, 5, 30),
                'gender': 'M',
                'address': 'Rua Consolação, 321',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01302-000',
                'emergency_contact_name': 'Lucia Oliveira',
                'emergency_contact_phone': '+5511111111111',
                'medical_insurance': 'Amil',
            },
        ]
        
        patients = []
        for patient_data in patients_data:
            patient, created = Patient.objects.get_or_create(
                email=patient_data['email'],
                defaults=patient_data
            )
            if created:
                self.stdout.write(f'Created patient: {patient.full_name}')
            patients.append(patient)
        
        # Create appointments for today and this week
        today = date.today()
        appointments_data = [
            # Today's appointments
            {
                'patient': patients[0],  # Maria Silva
                'appointment_date': today,
                'appointment_time': time(9, 0),
                'duration_minutes': 30,
                'appointment_type': 'consultation',
                'status': 'completed',
                'reason': 'Regular checkup',
                'location': 'Room 101',
            },
            {
                'patient': patients[1],  # João Santos
                'appointment_date': today,
                'appointment_time': time(10, 30),
                'duration_minutes': 60,
                'appointment_type': 'follow_up',
                'status': 'completed',
                'reason': 'Follow-up after treatment',
                'location': 'Room 102',
            },
            {
                'patient': patients[2],  # Ana Costa
                'appointment_date': today,
                'appointment_time': time(14, 30),
                'duration_minutes': 30,
                'appointment_type': 'consultation',
                'status': 'scheduled',
                'reason': 'First consultation',
                'location': 'Room 101',
            },
            {
                'patient': patients[3],  # Pedro Oliveira
                'appointment_date': today,
                'appointment_time': time(16, 0),
                'duration_minutes': 30,
                'appointment_type': 'emergency',
                'status': 'scheduled',
                'reason': 'Emergency consultation',
                'location': 'Room 103',
            },
            # Tomorrow's appointments
            {
                'patient': patients[0],  # Maria Silva
                'appointment_date': today + timedelta(days=1),
                'appointment_time': time(8, 30),
                'duration_minutes': 30,
                'appointment_type': 'checkup',
                'status': 'confirmed',
                'reason': 'Annual checkup',
                'location': 'Room 101',
            },
            {
                'patient': patients[1],  # João Santos
                'appointment_date': today + timedelta(days=1),
                'appointment_time': time(11, 0),
                'duration_minutes': 45,
                'appointment_type': 'consultation',
                'status': 'scheduled',
                'reason': 'Consultation',
                'location': 'Room 102',
            },
            # Day after tomorrow
            {
                'patient': patients[2],  # Ana Costa
                'appointment_date': today + timedelta(days=2),
                'appointment_time': time(15, 0),
                'duration_minutes': 30,
                'appointment_type': 'follow_up',
                'status': 'scheduled',
                'reason': 'Follow-up appointment',
                'location': 'Room 101',
            },
        ]
        
        for appointment_data in appointments_data:
            appointment, created = Appointment.objects.get_or_create(
                doctor=doctor,
                patient=appointment_data['patient'],
                appointment_date=appointment_data['appointment_date'],
                appointment_time=appointment_data['appointment_time'],
                defaults=appointment_data
            )
            if created:
                self.stdout.write(f'Created appointment: {appointment}')
        
        # Create sample medical records
        medical_records_data = [
            {
                'patient': patients[0],  # Maria Silva
                'datetime': timezone.now() - timedelta(days=1),
                'content': 'Paciente apresentou-se para consulta de rotina. Pressão arterial: 140/90 mmHg. Peso: 65kg. Altura: 1.65m. IMC: 23.9. Paciente relata dores de cabeça ocasionais. Prescrito Losartana 50mg 1x/dia. Retorno em 30 dias.',
            },
            {
                'patient': patients[0],  # Maria Silva
                'datetime': timezone.now() - timedelta(days=30),
                'content': 'Primeira consulta. Paciente com histórico familiar de hipertensão. Exames laboratoriais solicitados: hemograma completo, glicemia, colesterol total, creatinina, uréia. Orientações sobre dieta e exercícios físicos.',
            },
            {
                'patient': patients[1],  # João Santos
                'datetime': timezone.now() - timedelta(days=2),
                'content': 'Consulta de retorno. Paciente diabético tipo 2. Glicemia de jejum: 120 mg/dL. HbA1c: 7.2%. Paciente relata aderência ao tratamento. Ajuste na dosagem da Metformina para 850mg 2x/dia. Orientações sobre monitoramento glicêmico.',
            },
            {
                'patient': patients[1],  # João Santos
                'datetime': timezone.now() - timedelta(days=60),
                'content': 'Diagnóstico de Diabetes Mellitus Tipo 2. Glicemia de jejum: 180 mg/dL. HbA1c: 9.1%. Iniciado tratamento com Metformina 500mg 2x/dia. Orientações sobre dieta diabética e exercícios. Retorno em 15 dias.',
            },
            {
                'patient': patients[2],  # Ana Costa
                'datetime': timezone.now() - timedelta(days=3),
                'content': 'Primeira consulta. Paciente jovem, 32 anos, relata fadiga e dores musculares. Exame físico normal. Exames laboratoriais solicitados: hemograma, TSH, T3, T4, vitamina D, B12. Orientações sobre sono e alimentação.',
            },
            {
                'patient': patients[3],  # Pedro Oliveira
                'datetime': timezone.now() - timedelta(days=5),
                'content': 'Consulta de emergência. Paciente com dor torácica. Eletrocardiograma normal. Pressão arterial: 160/95 mmHg. Exames cardiológicos solicitados: ecocardiograma, teste ergométrico. Prescrito captopril 25mg 2x/dia. Retorno em 7 dias.',
            },
            {
                'patient': patients[3],  # Pedro Oliveira
                'datetime': timezone.now() - timedelta(days=90),
                'content': 'Consulta de rotina. Paciente com histórico de hipertensão arterial. Pressão arterial controlada: 130/80 mmHg. Exames laboratoriais normais. Manutenção do tratamento com enalapril 10mg 1x/dia. Orientações sobre atividade física.',
            },
        ]
        
        for record_data in medical_records_data:
            record, created = MedicalRecord.objects.get_or_create(
                doctor=doctor,
                patient=record_data['patient'],
                datetime=record_data['datetime'],
                defaults={
                    'content': record_data['content'],
                }
            )
            if created:
                self.stdout.write(f'Created medical record: {record}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )
        self.stdout.write('You can now login with:')
        self.stdout.write('Username: dr.santos')
        self.stdout.write('Password: password123')
