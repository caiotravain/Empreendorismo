from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, time, timedelta, datetime
from dashboard.models import (
    Clinic, Patient, Doctor, Appointment, MedicalRecord, 
    ConsultationRecord, Prescription, PrescriptionItem, WaitingListEntry
)

class Command(BaseCommand):
    help = 'Cria uma clínica completa com médicos, pacientes, agendamentos, prontuários, prescrições e lista de espera.'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando o povoamento de dados...')
        
        # 1. Criar Clínica
        clinic, created = Clinic.objects.get_or_create(
            name='Clínica Santa Maria',
            defaults={
                'phone': '+551133334444',
                'email': 'contato@santamaria.com',
                'address': 'Av. Paulista, 1000, São Paulo - SP',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'Clínica criada: {clinic.name}')

        # 2. Criar Médico
        doctor_user, created = User.objects.get_or_create(
            username='dr.oliveira',
            defaults={
                'first_name': 'Carlos',
                'last_name': 'Oliveira',
                'email': 'carlos.oliveira@santamaria.com',
                'is_staff': True,
            }
        )
        if created:
            doctor_user.set_password('senha123')
            doctor_user.save()
            self.stdout.write(f'Usuário médico criado: {doctor_user.username}')
        
        doctor, created = Doctor.objects.get_or_create(
            user=doctor_user,
            defaults={
                'clinic': clinic,
                'medical_license': 'CRM-SP 987654',
                'specialization': 'Clínica Médica',
                'years_of_experience': 15,
                'hospital_affiliation': 'Hospital Albert Einstein',
                'phone': '+5511988887777',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'Perfil médico criado: {doctor.full_name}')

        # 3. Criar Pacientes
        patients_data = [
            {
                'first_name': 'Ricardo', 'last_name': 'Pereira', 'email': 'ricardo@email.com',
                'phone': '+5511911112222', 'date_of_birth': date(1980, 5, 10), 'gender': 'M',
                'address': 'Rua Augusta, 500', 'city': 'São Paulo', 'state': 'SP', 'zip_code': '01305-000',
                'medical_insurance': 'Bradesco Saúde', 'cpf': '123.456.789-00'
            },
            {
                'first_name': 'Fernanda', 'last_name': 'Lima', 'email': 'fernanda@email.com',
                'phone': '+5511922223333', 'date_of_birth': date(1995, 8, 20), 'gender': 'F',
                'address': 'Al. Santos, 1200', 'city': 'São Paulo', 'state': 'SP', 'zip_code': '01419-001',
                'medical_insurance': 'Amil', 'cpf': '987.654.321-11'
            },
            {
                'first_name': 'Sérgio', 'last_name': 'Mendes', 'email': 'sergio@email.com',
                'phone': '+5511933334444', 'date_of_birth': date(1950, 12, 5), 'gender': 'M',
                'address': 'Rua Oscar Freire, 300', 'city': 'São Paulo', 'state': 'SP', 'zip_code': '01426-001',
                'medical_insurance': 'Unimed', 'cpf': '456.789.123-22'
            },
            {
                'first_name': 'Beatriz', 'last_name': 'Souza', 'email': 'beatriz@email.com',
                'phone': '+5511944445555', 'date_of_birth': date(1988, 3, 25), 'gender': 'F',
                'address': 'Av. Brigadeiro Faria Lima, 1500', 'city': 'São Paulo', 'state': 'SP', 'zip_code': '01452-001',
                'medical_insurance': 'Particular', 'cpf': '321.654.987-33'
            },
            {
                'first_name': 'Marcos', 'last_name': 'Rocha', 'email': 'marcos@email.com',
                'phone': '+5511955556666', 'date_of_birth': date(1972, 10, 15), 'gender': 'M',
                'address': 'Rua da Consolação, 2000', 'city': 'São Paulo', 'state': 'SP', 'zip_code': '01301-100',
                'medical_insurance': 'SulAmérica', 'cpf': '789.123.456-44'
            }
        ]
        
        patients = []
        for p_data in patients_data:
            patient, created = Patient.objects.get_or_create(
                email=p_data['email'],
                defaults={**p_data, 'clinic': clinic}
            )
            if created:
                self.stdout.write(f'Paciente criado: {patient.full_name}')
            patients.append(patient)

        # 4. Agendamentos e Prontuários
        today = date.today()
        
        # Histórico Passado (Concluído)
        past_date = today - timedelta(days=7)
        past_appointment, created = Appointment.objects.get_or_create(
            doctor=doctor, patient=patients[0],
            appointment_date=past_date, appointment_time=time(10, 0),
            defaults={
                'status': 'completed',
                'appointment_type': 'consultation',
                'reason': 'Check-up anual'
            }
        )
        
        ConsultationRecord.objects.get_or_create(
            appointment=past_appointment,
            defaults={
                'patient': patients[0],
                'doctor': doctor,
                'blood_pressure_systolic': 120,
                'blood_pressure_diastolic': 80,
                'heart_rate': 72,
                'temperature': 36.5,
                'weight': 75.0,
                'height': 175.0,
                'chief_complaint': 'Check-up de rotina.',
                'hda': 'Paciente assintomático, busca avaliação preventiva.',
                'physical_exam': 'Bom estado geral, eupneico, acianótico.',
                'diagnostic_hypothesis': 'Paciente hígido.',
                'conduct': 'Solicitado exames de sangue de rotina. Manter hábitos saudáveis.'
            }
        )
        
        MedicalRecord.objects.get_or_create(
            doctor=doctor, patient=patients[0],
            datetime=timezone.make_aware(datetime.combine(past_date, time(10, 30))),
            defaults={'content': 'Consulta concluída. Paciente em ótimas condições.'}
        )
        
        # Prescrição para o passado
        presc, created = Prescription.objects.get_or_create(
            patient=patients[0], doctor=doctor,
            prescription_date=past_date,
            defaults={'status': 'active', 'notes': 'Tomar após as refeições.'}
        )
        if created:
            PrescriptionItem.objects.create(
                prescription=presc, medication_name='Vitamina C 500mg',
                quantity='30 comprimidos', dosage='1 comprimido ao dia pela manhã.'
            )

        # Agendamentos para HOJE
        Appointment.objects.get_or_create(
            doctor=doctor, patient=patients[1],
            appointment_date=today, appointment_time=time(14, 0),
            defaults={'status': 'scheduled', 'appointment_type': 'follow_up', 'reason': 'Retorno de exames'}
        )
        
        Appointment.objects.get_or_create(
            doctor=doctor, patient=patients[2],
            appointment_date=today, appointment_time=time(15, 30),
            defaults={'status': 'scheduled', 'appointment_type': 'consultation', 'reason': 'Dores lombares'}
        )

        # Agendamentos Futuros
        future_date = today + timedelta(days=2)
        Appointment.objects.get_or_create(
            doctor=doctor, patient=patients[3],
            appointment_date=future_date, appointment_time=time(9, 0),
            defaults={'status': 'confirmed', 'appointment_type': 'consultation', 'reason': 'Avaliação cardiológica'}
        )

        # 5. Lista de Espera
        WaitingListEntry.objects.get_or_create(
            doctor=doctor, patient=patients[4],
            defaults={
                'patient_name': patients[4].full_name,
                'phone': patients[4].phone,
                'urgency_level': 'medium',
                'status': 'pending',
                'notes': 'Deseja antecipar consulta para dores articulares.'
            }
        )
        
        # Adicionar um registro de espera sem paciente vinculado (novo)
        WaitingListEntry.objects.get_or_create(
            doctor=doctor,
            patient_name='Carlos Almeida',
            defaults={
                'phone': '11977776666',
                'urgency_level': 'high',
                'status': 'pending',
                'notes': 'Paciente novo: Carlos Almeida - Dor aguda.'
            }
        )

        self.stdout.write(self.style.SUCCESS('Dados povoados com sucesso em Português!'))
        self.stdout.write(f'Acesse com: Usuário: {doctor_user.username} | Senha: senha123')
