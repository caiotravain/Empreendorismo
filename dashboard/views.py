from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from datetime import date, timedelta
from .models import Appointment, Patient, Doctor, MedicalRecord

@login_required
def home(request):
    """Main medical dashboard view with agenda tab"""
    today = date.today()
    
    # Get current user's doctor profile
    try:
        current_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        current_doctor = None
    
    # Get today's appointments
    today_appointments = []
    if current_doctor:
        today_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today
        ).order_by('appointment_time')
    
    # Get this week's appointments for the calendar view
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    week_appointments = []
    if current_doctor:
        week_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date__range=[start_of_week, end_of_week]
        ).order_by('appointment_date', 'appointment_time')
    
    # Calculate stats
    if current_doctor:
        total_today = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today
        ).count()
        
        completed_today = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today,
            status='completed'
        ).count()
        
        pending_today = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today,
            status__in=['scheduled', 'confirmed']
        ).count()
        
        # Get next appointment
        next_appointment = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date__gte=today,
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date', 'appointment_time').first()
        
        next_appointment_time = next_appointment.appointment_time.strftime('%H:%M') if next_appointment else 'N/A'
    else:
        total_today = 0
        completed_today = 0
        pending_today = 0
        next_appointment_time = 'N/A'
    
    context = {
        'active_tab': 'agenda',
        'current_doctor': current_doctor,
        'today_appointments': today_appointments,
        'week_appointments': week_appointments,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'stats': {
            'consultas_hoje': total_today,
            'pacientes_atendidos': completed_today,
            'consultas_pendentes': pending_today,
            'proxima_consulta': next_appointment_time,
        }
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def prontuarios(request):
    """Medical records view"""
    # Get current user's doctor profile
    try:
        current_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        current_doctor = None
    
    # Get selected patient ID from request
    selected_patient_id = request.GET.get('patient_id')
    selected_patient = None
    
    # Get medical records for the current doctor and selected patient
    medical_records = []
    patients_with_records = []
    
    if current_doctor:
        if selected_patient_id:
            # Filter by selected patient
            try:
                selected_patient = Patient.objects.get(id=selected_patient_id)
                # Get total count for pagination info
                total_records = MedicalRecord.objects.filter(
                    doctor=current_doctor,
                    patient=selected_patient
                ).count()
                
                # Get offset from request (default 0)
                offset = int(request.GET.get('offset', 0))
                limit = int(request.GET.get('limit', 2))
                
                # Get records in reverse chronological order (newest first) for display
                medical_records = MedicalRecord.objects.filter(
                    doctor=current_doctor,
                    patient=selected_patient
                ).select_related('patient').order_by('-datetime')[offset:offset+limit]
                
                # Add pagination info to context
                has_more_records = (offset + limit) < total_records
                next_offset = offset + limit
                
            except Patient.DoesNotExist:
                selected_patient = None
                total_records = 0
                has_more_records = False
                next_offset = 0
        else:
            # Show all patients with records for this doctor
            patients = Patient.objects.filter(
                medical_records__doctor=current_doctor
            ).distinct().order_by('last_name', 'first_name')
            
            for patient in patients:
                # Get the latest medical record for this patient
                latest_record = MedicalRecord.objects.filter(
                    doctor=current_doctor,
                    patient=patient
                ).order_by('-datetime').first()
                
                if latest_record:
                    patients_with_records.append({
                        'patient': patient,
                        'latest_record': latest_record,
                        'total_records': MedicalRecord.objects.filter(
                            doctor=current_doctor,
                            patient=patient
                        ).count()
                    })
    
    context = {
        'active_tab': 'prontuarios',
        'current_doctor': current_doctor,
        'selected_patient': selected_patient,
        'medical_records': medical_records,
        'patients_with_records': patients_with_records,
        'total_records': total_records if 'total_records' in locals() else 0,
        'has_more_records': has_more_records if 'has_more_records' in locals() else False,
        'next_offset': next_offset if 'next_offset' in locals() else 0,
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def exames(request):
    """Medical exams history view"""
    context = {
        'active_tab': 'exames',
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def timeline(request):
    """Clinical timeline view"""
    context = {
        'active_tab': 'timeline',
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def prescricao(request):
    """Online prescriptions view"""
    context = {
        'active_tab': 'prescricao',
        'prescricoes': [
            {
                'paciente': 'Maria Silva',
                'medicamento': 'Losartana 50mg',
                'dosagem': '1 comprimido/dia',
                'data': '09/01/2025',
                'status': 'Ativa',
            },
            {
                'paciente': 'João Santos',
                'medicamento': 'Metformina 850mg',
                'dosagem': '2 comprimidos/dia',
                'data': '08/01/2025',
                'status': 'Ativa',
            },
        ]
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def indicadores(request):
    """Medical indicators view"""
    context = {
        'active_tab': 'indicadores',
        'indicadores': {
            'pacientes_ativos': 156,
            'consultas_mes': 89,
            'exames_solicitados': 23,
            'prescricoes_ativas': 67,
        }
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def settings(request):
    """Settings view"""
    context = {
        'active_tab': 'settings',
    }
    return render(request, 'dashboard/home.html', context)

@login_required
@require_POST
def add_medical_record(request):
    """Add a new medical record for a patient"""
    try:
        # Get current user's doctor profile
        current_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Doctor profile not found'})
    
    # Get patient ID and content from request
    patient_id = request.POST.get('patient_id')
    content = request.POST.get('content', '').strip()
    
    if not patient_id or not content:
        return JsonResponse({'success': False, 'error': 'Patient ID and content are required'})
    
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Patient not found'})
    
    # Create new medical record
    medical_record = MedicalRecord.objects.create(
        patient=patient,
        doctor=current_doctor,
        content=content,
        datetime=timezone.now()
    )
    
    return JsonResponse({
        'success': True,
        'record_id': medical_record.id,
        'datetime': medical_record.datetime.strftime('%d/%m/%Y %H:%M'),
        'content': medical_record.content
    })

# API Views for Appointment Modal

@login_required
@require_http_methods(["GET"])
def api_patients(request):
    """API endpoint to get all patients for the appointment modal"""
    try:
        patients = Patient.objects.all().order_by('last_name', 'first_name')
        patients_data = []
        
        for patient in patients:
            patients_data.append({
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'email': patient.email,
                'phone': patient.phone,
                'full_name': patient.full_name
            })
        
        return JsonResponse({
            'success': True,
            'patients': patients_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_http_methods(["GET"])
def api_doctors(request):
    """API endpoint to get all doctors for the appointment modal"""
    try:
        doctors = Doctor.objects.filter(is_active=True).order_by('user__last_name', 'user__first_name')
        doctors_data = []
        
        for doctor in doctors:
            doctors_data.append({
                'id': doctor.id,
                'full_name': doctor.full_name,
                'specialization': doctor.specialization,
                'medical_license': doctor.medical_license
            })
        
        return JsonResponse({
            'success': True,
            'doctors': doctors_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_POST
def api_appointments(request):
    """API endpoint to create a new appointment"""
    try:
        # Get form data
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        duration_minutes = request.POST.get('duration_minutes', 30)
        appointment_type = request.POST.get('appointment_type', 'consultation')
        status = request.POST.get('status', 'scheduled')
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        location = request.POST.get('location', '')
        
        # Validate required fields
        if not all([patient_id, doctor_id, appointment_date, appointment_time]):
            return JsonResponse({
                'success': False,
                'error': 'Paciente, médico, data e horário são obrigatórios'
            })
        
        # Get patient and doctor objects
        try:
            patient = Patient.objects.get(id=patient_id)
            doctor = Doctor.objects.get(id=doctor_id)
        except (Patient.DoesNotExist, Doctor.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'Paciente ou médico não encontrado'
            })
        
        # Check for appointment conflicts
        existing_appointment = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).exists()
        
        if existing_appointment:
            return JsonResponse({
                'success': False,
                'error': 'Já existe uma consulta agendada para este médico no horário selecionado'
            })
        
        # Create the appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            duration_minutes=int(duration_minutes),
            appointment_type=appointment_type,
            status=status,
            reason=reason,
            notes=notes,
            location=location
        )
        
        return JsonResponse({
            'success': True,
            'appointment_id': appointment.id,
            'message': f'Consulta agendada para {patient.full_name} com {doctor.full_name} em {appointment_date} às {appointment_time}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar consulta: {str(e)}'
        })

@login_required
@require_POST
def api_create_patient(request):
    """API endpoint to create a new patient"""
    try:
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        
        # Validate required fields
        if not all([first_name, last_name, date_of_birth, gender]):
            return JsonResponse({
                'success': False,
                'error': 'Nome, sobrenome, data de nascimento e sexo são obrigatórios'
            })
        
        # Check if patient already exists
        existing_patient = Patient.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            date_of_birth=date_of_birth
        ).exists()
        
        if existing_patient:
            return JsonResponse({
                'success': False,
                'error': 'Já existe um paciente com estes dados'
            })
        
        # Create the patient
        patient = Patient.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email if email else None,
            phone=phone if phone else None,
            date_of_birth=date_of_birth,
            gender=gender
        )
        
        return JsonResponse({
            'success': True,
            'patient_id': patient.id,
            'message': f'Paciente {patient.full_name} criado com sucesso'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar paciente: {str(e)}'
        })
