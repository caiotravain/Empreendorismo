from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.db import models
from django.db.models import Q
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation
from .models import Appointment, Patient, Doctor, MedicalRecord, Prescription, PrescriptionItem, PrescriptionTemplate, Expense, Income, Medication, WaitingListEntry, AppointmentSettings
from .waiting_list_views import api_waiting_list, api_waiting_list_entry, api_update_waiting_list_entry, api_convert_waitlist_to_appointment
from accounts.utils import get_accessible_patients, get_user_role, has_access_to_patient, get_accessible_doctors, can_access_doctor

@login_required
def home(request):
    """Main medical dashboard view with agenda tab"""
    # Use localtime to get Brazil timezone (America/Sao_Paulo)
    today = timezone.localtime(timezone.now()).date()
    
    # Get current doctor (from selection for admins, or user's doctor)
    current_doctor = get_selected_doctor(request)
    
    # Get accessible doctors for filtering
    accessible_doctors = get_accessible_doctors(request.user)
    
    # Get today's appointments - filter by accessible doctors and exclude cancelled
    if current_doctor and current_doctor in accessible_doctors:
        today_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today
        ).exclude(status='cancelled').order_by('appointment_time')
    else:
        # For admins without doctor selection or when current_doctor is not accessible, show appointments from accessible doctors
        today_appointments = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            appointment_date=today
        ).exclude(status='cancelled').order_by('appointment_time')
    print("today_appointments", today_appointments)
    # Get this week's appointments for the calendar view (excluding cancelled)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    if current_doctor and current_doctor in accessible_doctors:
        week_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date__range=[start_of_week, end_of_week]
        ).exclude(status='cancelled').order_by('appointment_date', 'appointment_time')
    else:
        # For admins without doctor selection, show appointments from accessible doctors
        week_appointments = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            appointment_date__range=[start_of_week, end_of_week]
        ).exclude(status='cancelled').order_by('appointment_date', 'appointment_time')
    
    # Calculate stats - always filter by accessible doctors and exclude cancelled
    if current_doctor and current_doctor in accessible_doctors:
        total_today = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today
        ).exclude(status='cancelled').count()
        
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
        
        # Get next appointment (from today onwards, including future appointments today)
        # Use localtime to get Brazil timezone (America/Sao_Paulo)
        now = timezone.localtime(timezone.now())
        current_time = now.time()
        
        # First, try to find appointments today that haven't happened yet
        today_future_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today,
            appointment_time__gt=current_time,
            status__in=['scheduled', 'confirmed']
        ).exclude(
            status='cancelled'
        ).order_by('appointment_time').first()
        
        if today_future_appointments:
            # Next appointment is today
            next_appointment_time = f"Hoje às {today_future_appointments.appointment_time.strftime('%H:%M')}"
        else:
            # Look for appointments from tomorrow onwards
            tomorrow = today + timedelta(days=1)
            next_appointment = Appointment.objects.filter(
                doctor=current_doctor,
                appointment_date__gte=tomorrow,
                status__in=['scheduled', 'confirmed']
            ).exclude(
                status='cancelled'
            ).order_by('appointment_date', 'appointment_time').first()
            
            if next_appointment:
                if next_appointment.appointment_date == tomorrow:
                    next_appointment_time = f"Amanhã às {next_appointment.appointment_time.strftime('%H:%M')}"
                else:
                    next_appointment_time = f"{next_appointment.appointment_date.strftime('%d/%m')} às {next_appointment.appointment_time.strftime('%H:%M')}"
            else:
                next_appointment_time = 'N/A'
    else:
        # For admins without doctor selection, show aggregated stats for accessible doctors
        total_today = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            appointment_date=today
        ).exclude(status='cancelled').count()
        
        completed_today = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            appointment_date=today,
            status='completed'
        ).count()
        
        pending_today = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            appointment_date=today,
            status__in=['scheduled', 'confirmed']
        ).count()
        
        # Get next appointment from accessible doctors
        # Use localtime to get Brazil timezone (America/Sao_Paulo)
        now = timezone.localtime(timezone.now())
        current_time = now.time()
        
        today_future_appointments = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            appointment_date=today,
            appointment_time__gt=current_time,
            status__in=['scheduled', 'confirmed']
        ).exclude(
            status='cancelled'
        ).order_by('appointment_time').first()
        
        if today_future_appointments:
            next_appointment_time = f"Hoje às {today_future_appointments.appointment_time.strftime('%H:%M')}"
        else:
            tomorrow = today + timedelta(days=1)
            next_appointment = Appointment.objects.filter(
                doctor__in=accessible_doctors,
                appointment_date__gte=tomorrow,
                status__in=['scheduled', 'confirmed']
            ).exclude(
                status='cancelled'
            ).order_by('appointment_date', 'appointment_time').first()
            
            if next_appointment:
                if next_appointment.appointment_date == tomorrow:
                    next_appointment_time = f"Amanhã às {next_appointment.appointment_time.strftime('%H:%M')}"
                else:
                    next_appointment_time = f"{next_appointment.appointment_date.strftime('%d/%m')} às {next_appointment.appointment_time.strftime('%H:%M')}"
            else:
                next_appointment_time = 'N/A'
    
    # Get all patients for the patients tab (will be filtered by JavaScript)
    # Use utility function to filter by user role
    all_patients = get_accessible_patients(request.user).order_by('last_name', 'first_name')
    patients = all_patients.filter(is_active=True)  # Default view shows only active
    
    # Calculate patient statistics
    from django.utils import timezone as django_timezone
    
    # Get all patients (including inactive) for statistics
    total_patients = all_patients.count()
    active_patients = all_patients.filter(is_active=True).count()
    
    # Patients created this month (only active)
    now = django_timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = patients.filter(created_at__gte=start_of_month).count()
    
    # Pending appointments - always filter by accessible doctors
    if current_doctor and current_doctor in accessible_doctors:
        pending_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            status__in=['scheduled', 'confirmed']
        ).count()
    else:
        # For admins without doctor selection, show aggregated count for accessible doctors
        pending_appointments = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            status__in=['scheduled', 'confirmed']
        ).count()
    
    # Get active tab from URL parameter, default to 'agenda'
    active_tab = request.GET.get('tab', 'agenda')
    
    context = {
        'active_tab': active_tab,
        'current_doctor': current_doctor,
        'today_appointments': today_appointments,
        'week_appointments': week_appointments,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'patients': patients,
        'all_patients': all_patients,
        'patient_stats': {
            'total_patients': total_patients,
            'active_patients': active_patients,
            'new_this_month': new_this_month,
            'pending_appointments': pending_appointments,
        },
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
    # Get current doctor (from selection for admins, or user's doctor)
    current_doctor = get_selected_doctor(request)
    
    # Get selected patient ID from request
    selected_patient_id = request.GET.get('patient_id')
    selected_patient = None
    
    # Get medical records for the current doctor and selected patient
    medical_records = []
    patients_with_records = []
    
    # Get accessible doctors for filtering
    accessible_doctors = get_accessible_doctors(request.user)
    
    if current_doctor and current_doctor in accessible_doctors:
        if selected_patient_id:
            # Filter by selected patient
            try:
                selected_patient = Patient.objects.get(id=selected_patient_id)
                
                # Check if user has access to this patient
                if not has_access_to_patient(request.user, selected_patient):
                    selected_patient = None
                    total_records = 0
                    has_more_records = False
                    next_offset = 0
                else:
                    # Get total count for pagination info
                    total_records = MedicalRecord.objects.filter(
                        doctor__in=accessible_doctors,
                        patient=selected_patient
                    ).count()
                    
                    # Get offset from request (default 0)
                    offset = int(request.GET.get('offset', 0))
                    limit = int(request.GET.get('limit', 2))
                    
                    # Get records in reverse chronological order (newest first) for display
                    medical_records = MedicalRecord.objects.filter(
                        doctor__in=accessible_doctors,
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
            # Show all patients with records for accessible doctors
            accessible_patients = get_accessible_patients(request.user)
            patients = accessible_patients.filter(
                medical_records__doctor__in=accessible_doctors
            ).distinct().order_by('last_name', 'first_name')
            
            for patient in patients:
                # Get the latest medical record for this patient
                latest_record = MedicalRecord.objects.filter(
                    doctor__in=accessible_doctors,
                    patient=patient
                ).order_by('-datetime').first()
                
                if latest_record:
                    patients_with_records.append({
                        'patient': patient,
                        'latest_record': latest_record,
                        'total_records': MedicalRecord.objects.filter(
                            doctor__in=accessible_doctors,
                            patient=patient
                        ).count()
                    })
    
    # Calculate patient statistics for the context
    from django.utils import timezone as django_timezone
    all_patients = get_accessible_patients(request.user)
    total_patients = all_patients.count()
    active_patients = all_patients.filter(is_active=True).count()
    
    # Patients created this month
    now = django_timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = all_patients.filter(created_at__gte=start_of_month).count()
    
    # Pending appointments
    if current_doctor:
        pending_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            status__in=['scheduled', 'confirmed']
        ).count()
    else:
        pending_appointments = Appointment.objects.filter(
            status__in=['scheduled', 'confirmed']
        ).count()
    
    context = {
        'active_tab': 'prontuarios',
        'current_doctor': current_doctor,
        'selected_patient': selected_patient,
        'medical_records': medical_records,
        'patients_with_records': patients_with_records,
        'total_records': total_records if 'total_records' in locals() else 0,
        'has_more_records': has_more_records if 'has_more_records' in locals() else False,
        'next_offset': next_offset if 'next_offset' in locals() else 0,
        'patient_stats': {
            'total_patients': total_patients,
            'active_patients': active_patients,
            'new_this_month': new_this_month,
            'pending_appointments': pending_appointments,
        },
    }
    return render(request, 'dashboard/home.html', context)



@login_required
def prescricao(request):
    """Online prescriptions view"""
    # Get current user's doctor profile
    try:
        current_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        current_doctor = None
    
    context = {
        'active_tab': 'prescricao',
        'current_doctor': current_doctor,
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def indicadores(request):
    """Medical indicators view"""
    context = {
        'active_tab': 'indicadores',
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def relatorios(request):
    """Reports view"""
    # Get current doctor (from selection for admins, or user's doctor)
    current_doctor = get_selected_doctor(request)
    
    context = {
        'active_tab': 'relatorios',
        'current_doctor': current_doctor,
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def patients(request):
    """Patients management view"""
    # Get current doctor (from selection for admins, or user's doctor)
    current_doctor = get_selected_doctor(request)
    
    # Get accessible patients (filtered by user role)
    patients = get_accessible_patients(request.user).order_by('last_name', 'first_name')
    
    # Calculate statistics
    from datetime import date, timedelta
    from django.utils import timezone
    
    total_patients = patients.count()
    
    # Patients created this month
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = patients.filter(created_at__gte=start_of_month).count()
    
    # Pending appointments (if doctor exists)
    pending_appointments = 0
    if current_doctor:
        pending_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            status__in=['scheduled', 'confirmed']
        ).count()
    
    context = {
        'active_tab': 'patients',
        'current_doctor': current_doctor,
        'patients': patients,
        'stats': {
            'total_patients': total_patients,
            'active_patients': total_patients,  # All patients are considered active
            'new_this_month': new_this_month,
            'pending_appointments': pending_appointments,
        }
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def settings(request):
    """Settings view"""
    # Get current doctor (from selection for admins, or user's doctor)
    current_doctor = get_selected_doctor(request)
    
    # Get accessible patients for context
    all_patients = get_accessible_patients(request.user)
    total_patients = all_patients.count()
    active_patients = all_patients.filter(is_active=True).count()
    
    # Calculate patient statistics
    from django.utils import timezone as django_timezone
    now = django_timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = all_patients.filter(created_at__gte=start_of_month).count()
    
    # Pending appointments
    if current_doctor:
        pending_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            status__in=['scheduled', 'confirmed']
        ).count()
    else:
        pending_appointments = Appointment.objects.filter(
            status__in=['scheduled', 'confirmed']
        ).count()
    
    context = {
        'active_tab': 'settings',
        'current_doctor': current_doctor,
        'patient_stats': {
            'total_patients': total_patients,
            'active_patients': active_patients,
            'new_this_month': new_this_month,
            'pending_appointments': pending_appointments,
        },
    }
    return render(request, 'dashboard/home.html', context)

@login_required
@require_POST
def add_medical_record(request):
    """Add a new medical record for a patient"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({'success': False, 'error': 'Médico não encontrado ou sem permissão'})
        
        # Get patient ID and content from request
        patient_id = request.POST.get('patient_id')
        content = request.POST.get('content', '').strip()
        
        if not patient_id or not content:
            return JsonResponse({'success': False, 'error': 'Patient ID and content are required'})
        
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Patient not found'})
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({'success': False, 'error': 'Você não tem permissão para criar registro para este paciente'})
        
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
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar registro médico: {str(e)}'
        })

# API Views for Appointment Modal

@login_required
@require_http_methods(["GET"])
def api_patients(request):
    """API endpoint to get all patients for the appointment modal"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        
        # Get patients based on role and doctor selection
        if current_doctor:
            # If doctor is selected (or user is a doctor/secretary), show their patients
            patients = Patient.objects.filter(doctor=current_doctor, is_active=True).order_by('last_name', 'first_name')
        else:
            # For admins without doctor selection, show all accessible patients
            patients = get_accessible_patients(request.user).filter(is_active=True).order_by('last_name', 'first_name')
        
        patients_data = []
        
        for patient in patients:
            patients_data.append({
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'email': patient.email,
                'phone': patient.phone,
                'cpf': patient.cpf or '',
                'full_name': patient.full_name
            })
        
        response_data = {
            'success': True,
            'patients': patients_data,
            'count': len(patients_data),
            'debug': {
                'current_doctor': str(current_doctor) if current_doctor else 'None',
                'role': get_user_role(request.user),
                'total_patients_in_db': Patient.objects.filter(is_active=True).count(),
                'patients_with_doctors': Patient.objects.filter(doctor__isnull=False, is_active=True).count(),
                'patients_without_doctors': Patient.objects.filter(doctor__isnull=True, is_active=True).count()
            }
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@login_required
@require_http_methods(["GET"])
def api_patient_detail(request, patient_id):
    """API endpoint to get a specific patient's details"""
    try:
        patient = Patient.objects.get(id=patient_id)
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem acesso a este paciente'
            })
        
        patient_data = {
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'email': patient.email,
            'phone': patient.phone,
            'cpf': patient.cpf or '',
            'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
            'gender': patient.gender,
            'address': patient.address,
            'city': patient.city,
            'state': patient.state,
            'zip_code': patient.zip_code,
            'emergency_contact_name': patient.emergency_contact_name,
            'emergency_contact_phone': patient.emergency_contact_phone,
            'medical_insurance': patient.medical_insurance,
            'full_name': patient.full_name,
            'age': patient.age,
            'is_active': patient.is_active,
            'created_at': patient.created_at.strftime('%d/%m/%Y'),
        }
        
        return JsonResponse({
            'success': True,
            'patient': patient_data
        })
    except Patient.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Paciente não encontrado'
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
        # Get only accessible doctors
        doctors = get_accessible_doctors(request.user).filter(is_active=True).order_by('user__last_name', 'user__first_name')
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
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get form data
        patient_id = request.POST.get('patient')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        duration_minutes = request.POST.get('duration_minutes', 30)
        appointment_type = request.POST.get('appointment_type', 'consultation')
        payment_type = request.POST.get('payment_type')
        insurance_operator = request.POST.get('insurance_operator', '')
        status = request.POST.get('status', 'scheduled')
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        location = request.POST.get('location', '')
        value = request.POST.get('value', '')
        
        # Validate required fields
        if not all([patient_id, appointment_date, appointment_time, payment_type]):
            return JsonResponse({
                'success': False,
                'error': 'Paciente, data, horário e tipo de pagamento são obrigatórios'
            })
        
        # Get patient object
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Paciente não encontrado'
            })
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para criar consulta para este paciente'
            })
        
        # Check for appointment conflicts (excluding cancelled appointments)
        existing_appointment = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).exclude(status='cancelled').exists()
        
        if existing_appointment:
            return JsonResponse({
                'success': False,
                'error': 'Já existe uma consulta agendada para este médico no horário selecionado'
            })
        
        # Convert value to decimal if provided
        appointment_value = None
        if value and value.strip():
            try:
                appointment_value = Decimal(value)
            except (ValueError, InvalidOperation):
                return JsonResponse({
                    'success': False,
                    'error': 'Valor da consulta inválido'
                })
        
        # Create the appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=current_doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            duration_minutes=int(duration_minutes),
            appointment_type=appointment_type,
            payment_type=payment_type,
            insurance_operator=insurance_operator if insurance_operator else None,
            status=status,
            reason=reason,
            notes=notes,
            location=location,
            value=appointment_value
        )
        
        # Create income record if value is provided, appointment is confirmed/completed, and date is today or in the past
        if appointment_value and appointment_value > 0 and status in ['confirmed', 'completed']:
            from datetime import date
            today = date.today()
            if appointment_date <= today:
                from .models import Income
                Income.objects.create(
                    doctor=current_doctor,
                    appointment=appointment,
                    patient=patient,
                    amount=appointment_value,
                    description=f"Consulta - {patient.full_name}",
                    category=appointment_type,
                    income_date=appointment_date,
                    notes=f"Receita gerada pela consulta agendada para {appointment_date} às {appointment_time}"
                )
        
        return JsonResponse({
            'success': True,
            'appointment_id': appointment.id,
            'message': f'Consulta agendada para {patient.full_name} com {current_doctor.full_name} em {appointment_date} às {appointment_time}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar consulta: {str(e)}'
        })

@login_required
@require_http_methods(["GET"])
def api_week_appointments(request):
    """API endpoint to get appointments for a date range (week or month)"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        
        # Get date parameters - support both week_start (legacy) and start/end (new)
        week_start = request.GET.get('week_start')
        start_param = request.GET.get('start')
        end_param = request.GET.get('end')
        
        # Parse the dates
        try:
            if start_param and end_param:
                # New format: use start and end dates directly
                start_date = datetime.strptime(start_param, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_param, '%Y-%m-%d').date()
            elif week_start:
                # Legacy format: calculate end of week
                start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
                end_date = start_date + timedelta(days=6)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Parâmetros de data são obrigatórios (use start/end ou week_start)'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de data inválido'
            })
        
        # Get appointments for the week (excluding cancelled)
        # If current_doctor is set, filter by doctor; otherwise show all appointments for admins
        if current_doctor:
            appointments = Appointment.objects.filter(
                doctor=current_doctor,
                appointment_date__range=[start_date, end_date]
            ).exclude(status='cancelled').order_by('appointment_date', 'appointment_time')
        else:
            # For admins without doctor selection, show all appointments
            appointments = Appointment.objects.filter(
                appointment_date__range=[start_date, end_date]
            ).exclude(status='cancelled').order_by('appointment_date', 'appointment_time')
        
        # Format appointments for frontend
        appointments_data = []
        problematic_appointments = []  # Track appointments with missing patients
        
        for appointment in appointments.select_related('patient', 'doctor'):
            try:
                # Try to access patient - this will raise DoesNotExist if patient is missing
                patient_name = appointment.patient.full_name
                patient_id = appointment.patient.id
            except (Patient.DoesNotExist, AttributeError) as e:
                # Track problematic appointments - get patient_id from the FK field directly
                patient_fk_id = None
                try:
                    # Try to get the FK value directly from the model field
                    patient_fk_id = getattr(appointment, 'patient_id', None)
                except:
                    pass
                
                problematic_appointments.append({
                    'appointment_id': appointment.id,
                    'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                    'appointment_time': appointment.appointment_time.strftime('%H:%M'),
                    'patient_id': patient_fk_id,
                    'error': str(e)
                })
                # Skip this appointment
                continue
            
            # Check if this is the patient's first appointment with this doctor
            # Count previous appointments (excluding cancelled) before this appointment date/time
            previous_appointments_count = Appointment.objects.filter(
                patient=appointment.patient,
                doctor=appointment.doctor
            ).exclude(status='cancelled').filter(
                Q(appointment_date__lt=appointment.appointment_date) |
                Q(appointment_date=appointment.appointment_date, appointment_time__lt=appointment.appointment_time)
            ).count()
            is_first_appointment = previous_appointments_count == 0
            
            appointments_data.append({
                'id': appointment.id,
                'patient_name': patient_name,
                'patient_id': patient_id,
                'doctor_name': appointment.doctor.full_name,
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                'appointment_time': appointment.appointment_time.strftime('%H:%M'),
                'duration_minutes': appointment.duration_minutes,
                'appointment_type': appointment.get_appointment_type_display(),
                'payment_type': appointment.get_payment_type_display(),
                'value': float(appointment.value) if appointment.value else None,
                'status': appointment.status,
                'reason': appointment.reason,
                'notes': appointment.notes,
                'location': appointment.location,
                'is_first_appointment': is_first_appointment
            })
        
        response_data = {
            'success': True,
            'appointments': appointments_data,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'week_start': start_date.strftime('%Y-%m-%d'),  # Keep for backward compatibility
            'week_end': end_date.strftime('%Y-%m-%d')  # Keep for backward compatibility
        }
        
        # Include problematic appointments info if any
        if problematic_appointments:
            response_data['problematic_appointments'] = problematic_appointments
            response_data['warning'] = f'Found {len(problematic_appointments)} appointment(s) with missing patients'
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar consultas: {str(e)}'
        })


@login_required
@require_POST
def api_cancel_appointment(request):
    """API endpoint to cancel an appointment"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get accessible doctors for verification
        accessible_doctors = get_accessible_doctors(request.user)
        if current_doctor not in accessible_doctors:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para cancelar consultas deste médico'
            })
        
        # Get appointment ID and cancellation reason
        appointment_id = request.POST.get('appointment_id')
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        
        if not appointment_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da consulta é obrigatório'
            })
        
        # Get the appointment
        try:
            appointment = Appointment.objects.get(
                id=appointment_id,
                doctor__in=accessible_doctors
            )
        except Appointment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Consulta não encontrada ou sem permissão para acessá-la'
            })
        
        # Check if appointment can be cancelled
        if appointment.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'error': 'Esta consulta já foi cancelada'
            })
        
        if appointment.status == 'no_show':
            return JsonResponse({
                'success': False,
                'error': 'Esta consulta já foi marcada como falta'
            })
        
        if appointment.status == 'completed':
            return JsonResponse({
                'success': False,
                'error': 'Não é possível cancelar uma consulta já concluída'
            })
        
        # Check if reason contains "falta" to determine status
        is_no_show = cancellation_reason and 'falta' in cancellation_reason.lower()
        
        # Remove any associated income records before cancelling
        income_deleted_count = 0
        associated_incomes = Income.objects.filter(appointment=appointment)
        if associated_incomes.exists():
            income_deleted_count = associated_incomes.count()
            associated_incomes.delete()
        
        # Cancel the appointment (will set status to no_show or cancelled based on reason)
        appointment.cancel(cancellation_reason)
        
        # Set appropriate message based on status
        if is_no_show:
            message = f'Consulta de {appointment.patient.full_name} marcada como falta com sucesso'
        else:
            message = f'Consulta de {appointment.patient.full_name} cancelada com sucesso'
        
        if income_deleted_count > 0:
            message += f' e {income_deleted_count} receita(s) removida(s)'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'income_deleted_count': income_deleted_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao cancelar consulta: {str(e)}'
        })

@login_required
def api_count_appointments_to_cancel(request):
    """API endpoint to count appointments that will be cancelled in a date/time range"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get accessible doctors for filtering
        accessible_doctors = get_accessible_doctors(request.user)
        if current_doctor not in accessible_doctors:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para contar consultas deste médico'
            })
        
        # Get date range and time range from GET parameters
        from_date_str = request.GET.get('from_date')
        until_date_str = request.GET.get('until_date')
        from_time_str = request.GET.get('from_time')
        until_time_str = request.GET.get('until_time')
        exclude_completed = request.GET.get('exclude_completed', 'true').lower() == 'true'
        
        if not from_date_str or not until_date_str or not from_time_str or not until_time_str:
            return JsonResponse({
                'success': False,
                'error': 'Datas e horários são obrigatórios'
            })
        
        # Parse dates
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            until_date = datetime.strptime(until_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de data inválido. Use YYYY-MM-DD'
            })
        
        # Parse times
        try:
            from_time = datetime.strptime(from_time_str, '%H:%M').time()
            until_time = datetime.strptime(until_time_str, '%H:%M').time()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de horário inválido. Use HH:MM'
            })
        
        # Build query for appointments in date and time range (same logic as cancel)
        if from_date == until_date:
            # Same day: filter by time range
            appointments_query = Appointment.objects.filter(
                doctor__in=accessible_doctors,
                appointment_date=from_date,
                appointment_time__gte=from_time,
                appointment_time__lte=until_time
            )
        else:
            # Different days: use Q objects for complex filtering
            from django.db.models import Q
            
            appointments_query = Appointment.objects.filter(
                doctor__in=accessible_doctors
            ).filter(
                Q(
                    # Appointments on start date with time >= from_time
                    appointment_date=from_date,
                    appointment_time__gte=from_time
                ) | Q(
                    # Appointments on end date with time <= until_time
                    appointment_date=until_date,
                    appointment_time__lte=until_time
                ) | Q(
                    # Appointments between start and end dates (all times)
                    appointment_date__gt=from_date,
                    appointment_date__lt=until_date
                )
            )
        
        # Exclude completed appointments if requested
        if exclude_completed:
            appointments_query = appointments_query.exclude(status='completed')
        
        # Count appointments
        count = appointments_query.count()
        
        return JsonResponse({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao contar consultas: {str(e)}'
        })

@login_required
@require_POST
def api_bulk_cancel_appointments(request):
    """API endpoint to cancel multiple appointments in a date range"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get accessible doctors for filtering
        accessible_doctors = get_accessible_doctors(request.user)
        if current_doctor not in accessible_doctors:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para cancelar consultas deste médico'
            })
        
        # Get date range, time range and cancellation reason
        from_date_str = request.POST.get('from_date')
        until_date_str = request.POST.get('until_date')
        from_time_str = request.POST.get('from_time')
        until_time_str = request.POST.get('until_time')
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        exclude_completed = request.POST.get('exclude_completed', 'true').lower() == 'true'
        
        if not from_date_str or not until_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Datas inicial e final são obrigatórias'
            })
        
        if not from_time_str or not until_time_str:
            return JsonResponse({
                'success': False,
                'error': 'Horários inicial e final são obrigatórios'
            })
        
        if not cancellation_reason:
            return JsonResponse({
                'success': False,
                'error': 'Motivo do cancelamento é obrigatório'
            })
        
        # Parse dates
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            until_date = datetime.strptime(until_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de data inválido. Use YYYY-MM-DD'
            })
        
        # Parse times
        try:
            from_time = datetime.strptime(from_time_str, '%H:%M').time()
            until_time = datetime.strptime(until_time_str, '%H:%M').time()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de horário inválido. Use HH:MM'
            })
        
        # Get today's date and current time
        now = timezone.localtime(timezone.now())
        today = now.date()
        current_time = now.time()
        
        # Validate dates are not in the past
        # If it's today, allow if the time is in the future or current
        if from_date < today:
            return JsonResponse({
                'success': False,
                'error': 'A data inicial não pode ser no passado. Selecione a partir de hoje.'
            })
        
        if until_date < today:
            return JsonResponse({
                'success': False,
                'error': 'A data final não pode ser no passado. Selecione a partir de hoje.'
            })
        
        # If from_date is today, validate that from_time is not in the past
        if from_date == today and from_time < current_time:
            return JsonResponse({
                'success': False,
                'error': 'O horário inicial não pode ser no passado.'
            })
        
        if from_date > until_date:
            return JsonResponse({
                'success': False,
                'error': 'Data inicial não pode ser maior que data final'
            })
        
        # If same date, validate times
        if from_date == until_date and from_time > until_time:
            return JsonResponse({
                'success': False,
                'error': 'Horário final não pode ser anterior ao horário inicial no mesmo dia'
            })
        
        # If until_date is today, validate that until_time is not in the past
        if until_date == today and until_time < current_time:
            return JsonResponse({
                'success': False,
                'error': 'O horário final não pode ser no passado para o dia de hoje.'
            })
        
        # Build query for appointments in date and time range
        # For appointments on the start date, filter by time >= from_time
        # For appointments on the end date, filter by time <= until_time
        # For appointments in between, include all times
        
        if from_date == until_date:
            # Same day: filter by time range
            appointments_query = Appointment.objects.filter(
                doctor__in=accessible_doctors,
                appointment_date=from_date,
                appointment_time__gte=from_time,
                appointment_time__lte=until_time
            )
        else:
            # Different days: use Q objects for complex filtering
            from django.db.models import Q
            
            appointments_query = Appointment.objects.filter(
                doctor__in=accessible_doctors
            ).filter(
                Q(
                    # Appointments on start date with time >= from_time
                    appointment_date=from_date,
                    appointment_time__gte=from_time
                ) | Q(
                    # Appointments on end date with time <= until_time
                    appointment_date=until_date,
                    appointment_time__lte=until_time
                ) | Q(
                    # Appointments between start and end dates (all times)
                    appointment_date__gt=from_date,
                    appointment_date__lt=until_date
                )
            )
        
        # Exclude completed appointments if requested
        if exclude_completed:
            appointments_query = appointments_query.exclude(status='completed')
        
        # Get appointments to cancel
        appointments = appointments_query.all()
        
        if not appointments.exists():
            return JsonResponse({
                'success': False,
                'error': 'Nenhuma consulta encontrada no período selecionado para cancelar'
            })
        
        # Cancel all appointments
        cancelled_count = 0
        income_deleted_count = 0
        errors = []
        
        for appointment in appointments:
            try:
                # Remove any associated income records
                associated_incomes = Income.objects.filter(appointment=appointment)
                if associated_incomes.exists():
                    income_deleted_count += associated_incomes.count()
                    associated_incomes.delete()
                
                # Cancel the appointment
                appointment.cancel(cancellation_reason)
                cancelled_count += 1
            except Exception as e:
                errors.append(f'Erro ao cancelar consulta {appointment.id}: {str(e)}')
        
        # Build response message
        message = f'{cancelled_count} consulta(s) cancelada(s) com sucesso'
        if income_deleted_count > 0:
            message += f' e {income_deleted_count} receita(s) removida(s)'
        
        if errors:
            message += f'. {len(errors)} erro(s) ocorreram durante o processo.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cancelled_count': cancelled_count,
            'income_deleted_count': income_deleted_count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao cancelar consultas: {str(e)}'
        })

@login_required
@require_POST
def api_confirm_attendance(request):
    """API endpoint to confirm patient attendance"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get accessible doctors for verification
        accessible_doctors = get_accessible_doctors(request.user)
        if current_doctor not in accessible_doctors:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para confirmar presença de consultas deste médico'
            })
        
        # Get appointment ID
        appointment_id = request.POST.get('appointment_id')
        
        if not appointment_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da consulta é obrigatório'
            })
        
        # Get the appointment
        try:
            appointment = Appointment.objects.get(
                id=appointment_id,
                doctor__in=accessible_doctors
            )
        except Appointment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Consulta não encontrada ou sem permissão para acessá-la'
            })
        
        # Check if appointment can be confirmed
        if appointment.status == 'completed':
            return JsonResponse({
                'success': False,
                'error': 'Esta consulta já foi concluída'
            })
        
        if appointment.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'error': 'Não é possível confirmar presença de uma consulta cancelada'
            })
        
        # Check if appointment is in the future (shouldn't create income for future appointments)
        from datetime import date
        today = date.today()
        if appointment.appointment_date > today:
            return JsonResponse({
                'success': False,
                'error': 'Não é possível confirmar presença de uma consulta futura'
            })
        
        # Update appointment status to confirmed
        appointment.status = 'confirmed'
        appointment.save()
        
        # Note: Income is only created when appointment is completed, not when confirmed
        # This ensures financial reports only count completed appointments
        
        message = f'Presença de {appointment.patient.full_name} confirmada com sucesso'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'income_created': False
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao confirmar presença: {str(e)}'
        })


@login_required
@require_POST
def api_complete_appointment(request):
    """API endpoint to complete an appointment"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get accessible doctors for verification
        accessible_doctors = get_accessible_doctors(request.user)
        if current_doctor not in accessible_doctors:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para concluir consultas deste médico'
            })
        
        # Get appointment ID
        appointment_id = request.POST.get('appointment_id')
        
        if not appointment_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da consulta é obrigatório'
            })
        
        # Get the appointment
        try:
            appointment = Appointment.objects.get(
                id=appointment_id,
                doctor__in=accessible_doctors
            )
        except Appointment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Consulta não encontrada ou sem permissão para acessá-la'
            })
        
        # Check if appointment can be completed
        if appointment.status == 'completed':
            return JsonResponse({
                'success': False,
                'error': 'Esta consulta já foi concluída'
            })
        
        if appointment.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'error': 'Não é possível concluir uma consulta cancelada'
            })
        
        # Check if appointment is more than 4 hours in the future
        now = timezone.localtime(timezone.now())
        appointment_datetime = datetime.combine(appointment.appointment_date, appointment.appointment_time)
        # Make appointment_datetime timezone-aware for comparison
        appointment_datetime = timezone.make_aware(appointment_datetime)
        time_diff = appointment_datetime - now
        
        if time_diff.total_seconds() > 4 * 3600:  # 4 hours = 4 * 3600 seconds
            return JsonResponse({
                'success': False,
                'error': 'Não é possível concluir uma consulta com mais de 4 horas de antecedência'
            })
        
        # Update appointment status to completed
        appointment.status = 'completed'
        appointment.save()
        
        # Create income record if appointment has a value and doesn't already have one
        income_created = False
        if appointment.value and appointment.value > 0:
            # Check if income already exists for this appointment
            existing_income = Income.objects.filter(appointment=appointment).first()
            if not existing_income:
                Income.objects.create(
                    doctor=current_doctor,
                    appointment=appointment,
                    patient=appointment.patient,
                    amount=appointment.value,
                    description=f"Consulta - {appointment.patient.full_name}",
                    category=appointment.appointment_type,
                    income_date=appointment.appointment_date,
                    notes=f"Receita gerada pela consulta concluída em {appointment.appointment_date} às {appointment.appointment_time}"
                )
                income_created = True
        
        message = f'Consulta de {appointment.patient.full_name} concluída com sucesso'
        if income_created:
            message += f' e receita de R$ {appointment.value} registrada'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'income_created': income_created
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao concluir consulta: {str(e)}'
        })


@login_required
@require_POST
def api_sync_appointment_income(request):
    """API endpoint to sync income records for all completed appointments"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get accessible doctors for filtering
        accessible_doctors = get_accessible_doctors(request.user)
        if current_doctor not in accessible_doctors:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para sincronizar receitas deste médico'
            })
        
        # Get all completed appointments with values that don't have income records
        # Only include appointments that are confirmed/completed, have values, are not cancelled,
        # and are today or in the past
        from datetime import date
        today = date.today()
        
        completed_appointments = Appointment.objects.filter(
            doctor__in=accessible_doctors,
            status='completed',  # Only completed appointments generate income
            value__gt=0,
            appointment_date__lte=today  # Only today or past appointments
        ).exclude(
            status='cancelled'  # Explicitly exclude cancelled appointments
        ).exclude(
            incomes__isnull=False  # Exclude appointments that already have income records
        )
        
        income_created_count = 0
        total_value = 0
        
        for appointment in completed_appointments:
            # Create income record for this appointment
            Income.objects.create(
                doctor=current_doctor,
                appointment=appointment,
                patient=appointment.patient,
                amount=appointment.value,
                description=f"Consulta - {appointment.patient.full_name}",
                category=appointment.appointment_type,
                income_date=appointment.appointment_date,
                notes=f"Receita gerada pela consulta em {appointment.appointment_date} às {appointment.appointment_time}"
            )
            income_created_count += 1
            total_value += float(appointment.value)
        
        return JsonResponse({
            'success': True,
            'message': f'{income_created_count} receitas criadas automaticamente. Total: R$ {total_value:.2f}',
            'income_created_count': income_created_count,
            'total_value': total_value
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao sincronizar receitas: {str(e)}'
        })


@login_required
@require_POST
def api_update_appointment(request):
    """API endpoint to update appointment time, duration, or status"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get accessible doctors for verification
        accessible_doctors = get_accessible_doctors(request.user)
        if current_doctor not in accessible_doctors:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para atualizar consultas deste médico'
            })
        
        # Get appointment ID and update data
        appointment_id = request.POST.get('appointment_id')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        duration_minutes = request.POST.get('duration_minutes')
        status = request.POST.get('status')
        
        if not appointment_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da consulta é obrigatório'
            })
        
        # Get the appointment
        try:
            appointment = Appointment.objects.get(
                id=appointment_id,
                doctor__in=accessible_doctors
            )
        except Appointment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Consulta não encontrada ou sem permissão para acessá-la'
            })
        
        # Update appointment fields if provided
        if appointment_date:
            appointment.appointment_date = appointment_date
        if appointment_time:
            appointment.appointment_time = appointment_time
        if duration_minutes:
            appointment.duration_minutes = int(duration_minutes)
        if status:
            # Validate status
            valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
            if status in valid_statuses:
                appointment.status = status
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Status inválido: {status}'
                })
        
        appointment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Consulta atualizada com sucesso',
            'appointment': {
                'id': appointment.id,
                'status': appointment.status,
                'status_display': appointment.get_status_display()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao atualizar consulta: {str(e)}'
        })

@login_required
@require_http_methods(["GET"])
def api_next_appointment(request):
    """API endpoint to get the next appointment details"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
        # Get next appointment using the same logic as in home view
        # Use localtime to get Brazil timezone (America/Sao_Paulo)
        now = timezone.localtime(timezone.now())
        today = now.date()
        current_time = now.time()
        
        # First, try to find appointments today that haven't happened yet
        today_future_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date=today,
            appointment_time__gt=current_time,
            status__in=['scheduled', 'confirmed']
        ).exclude(
            status='cancelled'
        ).order_by('appointment_time').first()
        
        if today_future_appointments:
            next_appointment = today_future_appointments
        else:
            # Look for appointments from tomorrow onwards
            tomorrow = today + timedelta(days=1)
            next_appointment = Appointment.objects.filter(
                doctor=current_doctor,
                appointment_date__gte=tomorrow,
                status__in=['scheduled', 'confirmed']
            ).exclude(
                status='cancelled'
            ).order_by('appointment_date', 'appointment_time').first()
        
        if next_appointment:
            return JsonResponse({
                'success': True,
                'appointment': {
                    'id': next_appointment.id,
                    'patient_name': next_appointment.patient.full_name,
                    'appointment_date': next_appointment.appointment_date.strftime('%d/%m/%Y'),
                    'appointment_time': next_appointment.appointment_time.strftime('%H:%M'),
                    'appointment_type': next_appointment.get_appointment_type_display(),
                    'status': next_appointment.status,
                    'location': next_appointment.location or 'Consultório',
                    'reason': next_appointment.reason or 'Consulta médica',
                    'notes': next_appointment.notes or 'Nenhuma observação'
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Nenhuma consulta próxima encontrada'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao buscar próxima consulta: {str(e)}'
        })

@login_required
@require_http_methods(["GET"])
def api_agenda_stats(request):
    """API endpoint to get current agenda stats"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        
        # Use localtime to get Brazil timezone (America/Sao_Paulo)
        now = timezone.localtime(timezone.now())
        today = now.date()
        current_time = now.time()

        # Get accessible doctors for filtering
        accessible_doctors = get_accessible_doctors(request.user)
        
        # Calculate stats - always filter by accessible doctors
        if current_doctor and current_doctor in accessible_doctors:
            total_today = Appointment.objects.filter(
                doctor=current_doctor,
                appointment_date=today
            ).exclude(status='cancelled').count()
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
            
            # Get next appointment (from today onwards, including future appointments today)
            # First, try to find appointments today that haven't happened yet
            today_future_appointments = Appointment.objects.filter(
                doctor=current_doctor,
                appointment_date=today,
                appointment_time__gt=current_time,
                status__in=['scheduled', 'confirmed']
            ).exclude(
                status='cancelled'
            ).order_by('appointment_time').first()
            
            if today_future_appointments:
                # Next appointment is today
                next_appointment_time = f"Hoje às {today_future_appointments.appointment_time.strftime('%H:%M')}"
            else:
                # Look for appointments from tomorrow onwards
                tomorrow = today + timedelta(days=1)
                next_appointment = Appointment.objects.filter(
                    doctor=current_doctor,
                    appointment_date__gte=tomorrow,
                    status__in=['scheduled', 'confirmed']
                ).exclude(
                    status='cancelled'
                ).order_by('appointment_date', 'appointment_time').first()
                
                if next_appointment:
                    if next_appointment.appointment_date == tomorrow:
                        next_appointment_time = f"Amanhã às {next_appointment.appointment_time.strftime('%H:%M')}"
                    else:
                        next_appointment_time = f"{next_appointment.appointment_date.strftime('%d/%m')} às {next_appointment.appointment_time.strftime('%H:%M')}"
                else:
                    next_appointment_time = 'N/A'
        else:
            # For admins without doctor selection, show aggregated stats for accessible doctors
            total_today = Appointment.objects.filter(
                doctor__in=accessible_doctors,
                appointment_date=today
            ).exclude(status='cancelled').count()
            completed_today = Appointment.objects.filter(
                doctor__in=accessible_doctors,
                appointment_date=today,
                status='completed'
            ).count()
            
            pending_today = Appointment.objects.filter(
                doctor__in=accessible_doctors,
                appointment_date=today,
                status__in=['scheduled', 'confirmed']
            ).count()
            
            # Get next appointment from accessible doctors
            today_future_appointments = Appointment.objects.filter(
                doctor__in=accessible_doctors,
                appointment_date=today,
                appointment_time__gt=current_time,
                status__in=['scheduled', 'confirmed']
            ).exclude(
                status='cancelled'
            ).order_by('appointment_time').first()
            
            if today_future_appointments:
                next_appointment_time = f"Hoje às {today_future_appointments.appointment_time.strftime('%H:%M')}"
            else:
                tomorrow = today + timedelta(days=1)
                next_appointment = Appointment.objects.filter(
                    doctor__in=accessible_doctors,
                    appointment_date__gte=tomorrow,
                    status__in=['scheduled', 'confirmed']
                ).exclude(
                    status='cancelled'
                ).order_by('appointment_date', 'appointment_time').first()
                
                if next_appointment:
                    if next_appointment.appointment_date == tomorrow:
                        next_appointment_time = f"Amanhã às {next_appointment.appointment_time.strftime('%H:%M')}"
                    else:
                        next_appointment_time = f"{next_appointment.appointment_date.strftime('%d/%m')} às {next_appointment.appointment_time.strftime('%H:%M')}"
                else:
                    next_appointment_time = 'N/A'
        
        return JsonResponse({
            'success': True,
            'stats': {
                'consultas_hoje': total_today,
                'pacientes_atendidos': completed_today,
                'consultas_pendentes': pending_today,
                'proxima_consulta': next_appointment_time,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao buscar estatísticas: {str(e)}'
        })

# Prescription Views

def can_access_prescription(user, prescription):
    """
    Check if a user can access a specific prescription
    - Admins can access prescriptions of doctors they manage
    - Doctors can access only their own prescriptions
    - Secretaries can access prescriptions of their assigned doctor
    """
    if not user or not user.is_authenticated or not prescription:
        return False
    
    return can_access_doctor(user, prescription.doctor)

@login_required
@require_http_methods(["GET"])
def api_prescriptions(request):
    """API endpoint to get prescriptions for a patient"""
    try:
        # Get patient ID from request
        patient_id = request.GET.get('patient_id')
        if not patient_id:
            return JsonResponse({
                'success': False,
                'error': 'ID do paciente é obrigatório'
            })
        
        # Get patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Paciente não encontrado'
            })
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para acessar este paciente'
            })
        
        # Get accessible doctors for the current user
        accessible_doctors = get_accessible_doctors(request.user)
        
        # Get prescriptions for this patient from accessible doctors
        prescriptions = Prescription.objects.filter(
            patient=patient,
            doctor__in=accessible_doctors
        ).order_by('-prescription_date')
        
        prescriptions_data = []
        for prescription in prescriptions:
            items_data = []
            for item in prescription.items.all():
                items_data.append({
                    'medication_name': item.medication_name,
                    'quantity': item.quantity,
                    'dosage': item.dosage,
                    'notes': item.notes or ''
                })
            
            prescriptions_data.append({
                'id': prescription.id,
                'prescription_date': prescription.prescription_date.strftime('%d/%m/%Y'),
                'status': prescription.get_status_display(),
                'status_value': prescription.status,
                'notes': prescription.notes or '',
                'items': items_data,
                'sent_by_email': prescription.sent_by_email,
                'sent_by_whatsapp': prescription.sent_by_whatsapp,
                'printed': prescription.printed
            })
        
        return JsonResponse({
            'success': True,
            'prescriptions': prescriptions_data,
            'patient_name': patient.full_name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar prescrições: {str(e)}'
        })

@login_required
@require_POST
def api_create_prescription(request):
    """API endpoint to create a new prescription"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado ou sem permissão'
            })
        
        # Get form data
        patient_id = request.POST.get('patient_id')
        prescription_date = request.POST.get('prescription_date')
        template_id = request.POST.get('template_id')
        notes = request.POST.get('notes', '').strip()
        
        # Get medication data
        medication_names = request.POST.getlist('medication_name[]')
        quantities = request.POST.getlist('quantity[]')
        dosages = request.POST.getlist('dosage[]')
        
        # Validate required fields
        if not all([patient_id, prescription_date]):
            return JsonResponse({
                'success': False,
                'error': 'Paciente e data são obrigatórios'
            })
        
        if not medication_names or not any(medication_names):
            return JsonResponse({
                'success': False,
                'error': 'Pelo menos um medicamento deve ser adicionado'
            })
        
        # Get patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Paciente não encontrado'
            })
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para criar prescrição para este paciente'
            })
        
        # Get template if provided
        template = None
        if template_id:
            try:
                template = PrescriptionTemplate.objects.get(id=template_id, doctor=current_doctor)
            except PrescriptionTemplate.DoesNotExist:
                pass
        
        # Create prescription
        prescription = Prescription.objects.create(
            patient=patient,
            doctor=current_doctor,
            prescription_date=prescription_date,
            template=template,
            notes=notes if notes else None
        )
        
        # Create prescription items
        for i, medication_name in enumerate(medication_names):
            if medication_name.strip():  # Only create items with medication names
                quantity = quantities[i] if i < len(quantities) else ''
                dosage = dosages[i] if i < len(dosages) else ''
                
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    medication_name=medication_name.strip(),
                    quantity=quantity.strip(),
                    dosage=dosage.strip(),
                    order=i
                )
        
        return JsonResponse({
            'success': True,
            'prescription_id': prescription.id,
            'message': f'Prescrição criada com sucesso para {patient.full_name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar prescrição: {str(e)}'
        })

@login_required
@require_POST
def api_send_prescription_email(request):
    """API endpoint to send prescription by email"""
    try:
        prescription_id = request.POST.get('prescription_id')
        
        if not prescription_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da prescrição é obrigatório'
            })
        
        # Get prescription
        try:
            prescription = Prescription.objects.get(id=prescription_id)
        except Prescription.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Prescrição não encontrada'
            })
        
        # Check access permission
        if not can_access_prescription(request.user, prescription):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para acessar esta prescrição'
            })
        
        # Don't mark as sent - allow multiple sends
        # prescription.sent_by_email = True
        # prescription.save()
        
        # TODO: Implement actual email sending logic here
        # For now, just return success
        
        return JsonResponse({
            'success': True,
            'message': f'Prescrição enviada por email para {prescription.patient.full_name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao enviar prescrição por email: {str(e)}'
        })

@login_required
@require_POST
def api_send_prescription_whatsapp(request):
    """API endpoint to send prescription by WhatsApp"""
    try:
        prescription_id = request.POST.get('prescription_id')
        
        if not prescription_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da prescrição é obrigatório'
            })
        
        # Get prescription
        try:
            prescription = Prescription.objects.get(id=prescription_id)
        except Prescription.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Prescrição não encontrada'
            })
        
        # Check access permission
        if not can_access_prescription(request.user, prescription):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para acessar esta prescrição'
            })
        
        # Don't mark as sent - allow multiple sends
        # prescription.sent_by_whatsapp = True
        # prescription.save()
        
        # TODO: Implement actual WhatsApp sending logic here
        # For now, just return success
        
        return JsonResponse({
            'success': True,
            'message': f'Prescrição enviada por WhatsApp para {prescription.patient.full_name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao enviar prescrição por WhatsApp: {str(e)}'
        })

@login_required
@require_POST
def api_send_whatsapp(request):
    """API endpoint to send WhatsApp message (free integration using WhatsApp Web link)"""
    try:
        # Get phone number and message from request
        phone_number = request.POST.get('phone_number', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not phone_number:
            return JsonResponse({
                'success': False,
                'error': 'Número de telefone é obrigatório'
            })
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Mensagem é obrigatória'
            })
        
        # Format phone number (remove any non-digit characters except +)
        import re
        import urllib.parse
        
        # Remove all non-digit characters except +
        cleaned_phone = re.sub(r'[^\d+]', '', phone_number)
        
        # If phone doesn't start with +, assume it's Brazilian format and add country code
        if not cleaned_phone.startswith('+'):
            # Remove leading 0 if present
            if cleaned_phone.startswith('0'):
                cleaned_phone = cleaned_phone[1:]
            # Add Brazil country code if not present
            if not cleaned_phone.startswith('55'):
                cleaned_phone = '55' + cleaned_phone
            cleaned_phone = '+' + cleaned_phone
        
        # Remove the + for WhatsApp link format
        whatsapp_phone = cleaned_phone.replace('+', '')
        
        # URL encode the message
        encoded_message = urllib.parse.quote(message)
        
        # Create WhatsApp Web link
        whatsapp_url = f"https://wa.me/{whatsapp_phone}?text={encoded_message}"
        
        # Return the link - frontend can open it in a new window
        return JsonResponse({
            'success': True,
            'message': 'Link do WhatsApp gerado com sucesso',
            'whatsapp_url': whatsapp_url,
            'phone_formatted': cleaned_phone,
            'note': 'Abra este link para enviar a mensagem via WhatsApp Web'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao gerar link WhatsApp: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_print_prescription(request):
    """API endpoint to get prescription data for printing"""
    try:
        prescription_id = request.GET.get('prescription_id')
        
        if not prescription_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da prescrição é obrigatório'
            })
        
        # Get prescription
        try:
            prescription = Prescription.objects.get(id=prescription_id)
        except Prescription.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Prescrição não encontrada'
            })
        
        # Check access permission
        if not can_access_prescription(request.user, prescription):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para acessar esta prescrição'
            })
        
        # Don't mark as printed - allow multiple prints
        # prescription.printed = True
        # prescription.save()
        
        # Prepare prescription data for printing
        items_data = []
        for item in prescription.items.all():
            items_data.append({
                'medication_name': item.medication_name,
                'quantity': item.quantity,
                'dosage': item.dosage,
                'notes': item.notes or ''
            })
        
        prescription_data = {
            'id': prescription.id,
            'patient_name': prescription.patient.full_name,
            'doctor_name': prescription.doctor.full_name,
            'prescription_date': prescription.prescription_date.strftime('%d/%m/%Y'),
            'notes': prescription.notes or '',
            'items': items_data
        }
        
        return JsonResponse({
            'success': True,
            'prescription': prescription_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar prescrição para impressão: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_generate_prescription_pdf(request):
    """API endpoint to generate a professional PDF prescription"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
        from io import BytesIO
        
        prescription_id = request.GET.get('prescription_id')
        
        if not prescription_id:
            return JsonResponse({
                'success': False,
                'error': 'ID da prescrição é obrigatório'
            })
        
        # Get prescription
        try:
            prescription = Prescription.objects.select_related('patient', 'doctor', 'doctor__user').prefetch_related('items').get(id=prescription_id)
        except Prescription.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Prescrição não encontrada'
            })
        
        # Check access permission
        if not can_access_prescription(request.user, prescription):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para acessar esta prescrição'
            })
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Container for the PDF elements
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'PrescriptionTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        header_style = ParagraphStyle(
            'PrescriptionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        
        info_style = ParagraphStyle(
            'PrescriptionInfo',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=8,
            leading=14
        )
        
        medication_name_style = ParagraphStyle(
            'MedicationName',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=5,
            fontName='Helvetica-Bold',
            leading=16
        )
        
        medication_detail_style = ParagraphStyle(
            'MedicationDetail',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#555555'),
            spaceAfter=4,
            leftIndent=20,
            leading=14
        )
        
        notes_style = ParagraphStyle(
            'PrescriptionNotes',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            leading=14
        )
        
        # Header with decorative line
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("PRESCRIÇÃO MÉDICA", title_style))
        
        # Decorative line
        line_data = [['']]
        line_table = Table(line_data, colWidths=[6*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#1a5490')),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 0.25*inch))
        
        # Date and Prescription Number - Minimalist at top
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_RIGHT
        )
        date_text = f"{prescription.prescription_date.strftime('%d/%m/%Y')} • Prescrição Nº {prescription.id}"
        story.append(Paragraph(date_text, date_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Patient and Doctor Information - Minimalist boxes
        # Patient Information
        patient_info = f"<b>PACIENTE</b><br/>{prescription.patient.full_name}"
        if prescription.patient.cpf:
            patient_info += f"<br/><font size='9' color='#999999'>CPF: {prescription.patient.cpf}</font>"
        if prescription.patient.date_of_birth:
            age = prescription.patient.age
            if age is not None:
                patient_info += f"<br/><font size='9' color='#999999'>Idade: {age} anos</font>"
        
        patient_row = Table([[Paragraph(patient_info, info_style)]], colWidths=[6*inch])
        patient_row.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(patient_row)
        story.append(Spacer(1, 0.12*inch))
        
        # Doctor Information
        doctor_info = f"<b>MÉDICO</b><br/>{prescription.doctor.full_name}"
        if prescription.doctor.medical_license:
            doctor_info += f"<br/><font size='9' color='#999999'>CRM: {prescription.doctor.medical_license}</font>"
        if prescription.doctor.specialization:
            doctor_info += f"<br/><font size='9' color='#999999'>{prescription.doctor.specialization}</font>"
        
        doctor_row = Table([[Paragraph(doctor_info, info_style)]], colWidths=[6*inch])
        doctor_row.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(doctor_row)
        story.append(Spacer(1, 0.4*inch))
        
        # Medications section
        story.append(Paragraph("MEDICAMENTOS PRESCRITOS", header_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Medication items
        for idx, item in enumerate(prescription.items.all(), 1):
            medication_block = []
            
            # Medication name with number
            med_name = f"{idx}. {item.medication_name}"
            medication_block.append(Paragraph(med_name, medication_name_style))
            
            # Quantity
            if item.quantity:
                medication_block.append(Paragraph(f"<b>Quantidade:</b> {item.quantity}", medication_detail_style))
            
            # Dosage
            if item.dosage:
                medication_block.append(Paragraph(f"<b>Posologia:</b> {item.dosage}", medication_detail_style))
            
            # Notes
            if item.notes:
                medication_block.append(Paragraph(f"<b>Observações:</b> {item.notes}", medication_detail_style))
            
            # Add spacing between medications
            if idx < prescription.items.count():
                medication_block.append(Spacer(1, 0.15*inch))
            
            # Keep medication together
            story.append(KeepTogether(medication_block))
        
        # Additional notes section
        if prescription.notes:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("OBSERVAÇÕES GERAIS", header_style))
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph(prescription.notes, notes_style))
        
        # Footer with signature area
        story.append(Spacer(1, 0.5*inch))
        
        # Signature line
        signature_data = [['']]
        signature_table = Table(signature_data, colWidths=[6*inch])
        signature_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#333333')),
            ('TOPPADDING', (0, 0), (-1, -1), 30),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(signature_table)
        
        signature_text = Paragraph(
            f"<i>{prescription.doctor.full_name}<br/>CRM: {prescription.doctor.medical_license or 'N/A'}</i>",
            ParagraphStyle(
                'Signature',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#666666'),
                alignment=TA_CENTER,
                spaceAfter=0
            )
        )
        story.append(signature_text)
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create HTTP response
        response = HttpResponse(pdf_data, content_type='application/pdf')
        filename = f"prescricao_{prescription.patient.full_name.replace(' ', '_')}_{prescription.prescription_date.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except ImportError:
        return JsonResponse({
            'success': False,
            'error': 'Biblioteca reportlab não instalada. Execute: pip install reportlab'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao gerar PDF: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_search_medications(request):
    """API endpoint to search medications (case and accent insensitive)"""
    import unicodedata
    
    try:
        query = request.GET.get('q', '').strip()
        
        if not query:
            return JsonResponse({
                'success': True,
                'medications': [],
                'count': 0
            })
        
        # Get all medications
        all_medications = Medication.objects.all().order_by('name')
        
        # Normalize the search query (remove accents, convert to lowercase)
        query_normalized = unicodedata.normalize('NFKD', query.lower())
        query_normalized = ''.join(c for c in query_normalized if not unicodedata.combining(c))
        
        # Filter medications (case and accent insensitive)
        matching_medications = []
        for medication in all_medications:
            # Normalize medication name
            name_normalized = unicodedata.normalize('NFKD', medication.name.lower())
            name_normalized = ''.join(c for c in name_normalized if not unicodedata.combining(c))
            
            # Check if query matches
            if query_normalized in name_normalized:
                matching_medications.append({
                    'id': medication.id,
                    'name': medication.name,
                    'description': medication.description or ''
                })
        
        # Limit results to 50 for performance
        matching_medications = matching_medications[:50]
        
        return JsonResponse({
            'success': True,
            'medications': matching_medications,
            'count': len(matching_medications)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao buscar medicamentos: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_get_appointment_settings(request):
    """API endpoint to get appointment settings"""
    try:
        settings = AppointmentSettings.get_settings()
        return JsonResponse({
            'success': True,
            'settings': {
                'duration_options': settings.duration_options,
                'type_choices': settings.type_choices,
                'status_choices': settings.status_choices,
                'status_colors': settings.status_colors if settings.status_colors else {},
                'location_options': settings.location_options,
                'insurance_operators': settings.insurance_operators if settings.insurance_operators else [],
                'cancellation_reasons': settings.cancellation_reasons if settings.cancellation_reasons else [],
                'convenio_prices': settings.convenio_prices if settings.convenio_prices is not None else {},
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar configurações: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def api_save_appointment_settings(request):
    """API endpoint to save appointment settings"""
    try:
        import json
        data = json.loads(request.body)
        
        settings = AppointmentSettings.get_settings()
        
        # Validate and update duration options
        if 'duration_options' in data:
            duration_options = [int(d) for d in data['duration_options'] if isinstance(d, (int, str)) and str(d).isdigit()]
            if duration_options:
                settings.duration_options = sorted(set(duration_options))  # Remove duplicates and sort
        
        # Validate and update type choices (now just display names)
        if 'type_choices' in data:
            type_choices = []
            for choice in data['type_choices']:
                # Handle both old format [value, label] and new format (just string)
                if isinstance(choice, list) and len(choice) >= 2:
                    # Old format: use the label
                    type_choices.append(str(choice[1]).strip())
                elif isinstance(choice, str):
                    # New format: just the display name
                    type_choices.append(choice.strip())
            # Remove empty strings and duplicates
            type_choices = [c for c in type_choices if c]
            if type_choices:
                settings.type_choices = list(dict.fromkeys(type_choices))  # Remove duplicates while preserving order
        
        # Validate and update status choices (now just display names)
        if 'status_choices' in data:
            status_choices = []
            for choice in data['status_choices']:
                # Handle both old format [value, label] and new format (just string)
                if isinstance(choice, list) and len(choice) >= 2:
                    # Old format: use the label
                    status_choices.append(str(choice[1]).strip())
                elif isinstance(choice, str):
                    # New format: just the display name
                    status_choices.append(choice.strip())
            # Remove empty strings and duplicates
            status_choices = [c for c in status_choices if c]
            if status_choices:
                settings.status_choices = list(dict.fromkeys(status_choices))  # Remove duplicates while preserving order
        
        # Validate and update status colors
        if 'status_colors' in data:
            if isinstance(data['status_colors'], dict):
                # Clean up colors: remove entries for statuses that no longer exist
                valid_statuses = set(settings.status_choices)
                cleaned_colors = {
                    status: color for status, color in data['status_colors'].items()
                    if status in valid_statuses and isinstance(color, str) and color.startswith('#')
                }
                settings.status_colors = cleaned_colors
        
        # Validate and update location options
        if 'location_options' in data:
            location_options = [str(loc).strip() for loc in data['location_options'] if str(loc).strip()]
            settings.location_options = location_options
        
        # Validate and update insurance operators
        if 'insurance_operators' in data:
            insurance_operators = []
            for operator in data['insurance_operators']:
                if isinstance(operator, str) and operator.strip():
                    insurance_operators.append(operator.strip())
            # Remove duplicates while preserving order
            if insurance_operators:
                settings.insurance_operators = list(dict.fromkeys(insurance_operators))
        
        # Validate and update cancellation reasons
        if 'cancellation_reasons' in data:
            cancellation_reasons = []
            for reason in data['cancellation_reasons']:
                if isinstance(reason, str) and reason.strip():
                    cancellation_reasons.append(reason.strip())
            # Remove duplicates while preserving order
            if cancellation_reasons:
                settings.cancellation_reasons = list(dict.fromkeys(cancellation_reasons))
        
        # Validate and update convenio prices (dict: operator name -> price string)
        if 'convenio_prices' in data and isinstance(data['convenio_prices'], dict):
            cleaned = {}
            for op, val in data['convenio_prices'].items():
                if isinstance(op, str) and op.strip():
                    try:
                        cleaned[op.strip()] = str(float(val)) if val is not None and str(val).strip() != '' else '0'
                    except (TypeError, ValueError):
                        cleaned[op.strip()] = '0'
            settings.convenio_prices = cleaned
        
        settings.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Configurações salvas com sucesso!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao salvar configurações: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_indicators(request):
    """API endpoint to get real indicators/metrics data"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
        # Get period filter
        period = request.GET.get('period', 'month')
        
        # Calculate date range based on period
        from datetime import date, timedelta
        from django.utils import timezone
        
        today = timezone.now().date()
        start_date = None
        end_date = today
        
        if period == '30':
            start_date = today - timedelta(days=30)
        elif period == 'month':
            start_date = date(today.year, today.month, 1)
        elif period == 'quarter':
            quarter = (today.month - 1) // 3
            start_date = date(today.year, quarter * 3 + 1, 1)
        elif period == 'year':
            start_date = date(today.year, 1, 1)
        else:
            start_date = date(today.year, today.month, 1)
        
        # Get appointments in the period
        appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date__gte=start_date,
            appointment_date__lte=end_date
        )
        
        # Calculate metrics
        total_appointments = appointments.count()
        
        # Attendance metrics
        completed_count = appointments.filter(status='completed').count()
        no_show_count = appointments.filter(status='no_show').count()
        cancelled_count = appointments.filter(status='cancelled').count()
        attended_count = completed_count  # Completed = attended
        
        # Calculate percentages based on total appointments (so they add up to 100%)
        show_rate = round((attended_count / total_appointments * 100) if total_appointments > 0 else 0, 1)
        no_show_rate = round((no_show_count / total_appointments * 100) if total_appointments > 0 else 0, 1)
        cancelled_rate = round((cancelled_count / total_appointments * 100) if total_appointments > 0 else 0, 1)
        
        # Total patients
        total_patients = Patient.objects.filter(doctor=current_doctor, is_active=True).count()
        
        # Patient mix (payment type distribution)
        particular_count = appointments.filter(payment_type='particular').count()
        convenio_count = appointments.filter(payment_type='convenio').count()
        total_payment_appointments = particular_count + convenio_count
        
        private_pct = round((particular_count / total_payment_appointments * 100) if total_payment_appointments > 0 else 0, 1)
        insurance_pct = round((convenio_count / total_payment_appointments * 100) if total_payment_appointments > 0 else 0, 1)
        
        # Retention rate (patients with more than one appointment in the period)
        from django.db.models import Count
        patients_with_multiple = appointments.values('patient').annotate(
            appointment_count=Count('id')
        ).filter(appointment_count__gt=1).count()
        
        total_unique_patients = appointments.values('patient').distinct().count()
        retention_rate = round((patients_with_multiple / total_unique_patients * 100) if total_unique_patients > 0 else 0, 1)
        
        # Insurance providers breakdown
        providers_data = []
        
        # Get all insurance operators from appointments
        from django.db.models import Sum, Count, Avg
        from decimal import Decimal
        
        # Group by insurance operator
        insurance_appointments = appointments.filter(
            payment_type='convenio',
            insurance_operator__isnull=False
        ).exclude(insurance_operator='')
        
        operator_stats = insurance_appointments.values('insurance_operator').annotate(
            total_appointments=Count('id'),
            total_revenue=Sum('value'),
            avg_ticket=Avg('value')
        ).order_by('-total_revenue')
        
        for stat in operator_stats:
            providers_data.append({
                'name': stat['insurance_operator'],
                'total_appointments': stat['total_appointments'],
                'revenue': float(stat['total_revenue'] or 0),
                'avg_ticket': float(stat['avg_ticket'] or 0)
            })
        
        # Add "Particular" as a provider
        particular_appointments = appointments.filter(payment_type='particular')
        particular_revenue = particular_appointments.aggregate(Sum('value'))['value__sum'] or Decimal('0')
        particular_count_val = particular_appointments.count()
        particular_avg = float(particular_revenue / particular_count_val) if particular_count_val > 0 else 0
        
        if particular_count_val > 0:
            providers_data.insert(0, {
                'name': 'Particular',
                'total_appointments': particular_count_val,
                'revenue': float(particular_revenue),
                'avg_ticket': particular_avg
            })
        
        return JsonResponse({
            'success': True,
            'metrics': {
                'show_rate': show_rate,
                'no_show_rate': no_show_rate,
                'cancelled_rate': cancelled_rate,
                'total_patients': total_patients,
                'private_pct': private_pct,
                'insurance_pct': insurance_pct,
                'retention_rate': retention_rate,
                'providers': providers_data,
                'attended_count': attended_count,
                'no_show_count': no_show_count,
                'cancelled_count': cancelled_count,
                'particular_count': particular_count,
                'convenio_count': convenio_count,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao calcular indicadores: {str(e)}'
        })


@login_required
def finance(request):
    """Finance view with expense tracking and filtering"""
    # Get current user's doctor profile
    try:
        current_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        current_doctor = None
    
    # Get filter parameters
    selected_year = request.GET.get('year', timezone.now().year)
    selected_month = request.GET.get('month', timezone.now().month)
    
    # Convert to integers
    try:
        selected_year = int(selected_year)
        selected_month = int(selected_month)
    except (ValueError, TypeError):
        selected_year = timezone.now().year
        selected_month = timezone.now().month
    
    # Get expenses and income for the selected period
    expenses = []
    incomes = []
    total_expenses = 0
    total_income = 0
    expenses_by_category = {}
    incomes_by_category = {}
    
    if current_doctor:
        expenses = Expense.objects.filter(
            doctor=current_doctor,
            expense_date__year=selected_year,
            expense_date__month=selected_month
        ).order_by('-expense_date')
        
        incomes = Income.objects.filter(
            doctor=current_doctor,
            income_date__year=selected_year,
            income_date__month=selected_month
        ).order_by('-income_date')
        
        # Calculate totals
        total_expenses = sum(expense.amount for expense in expenses)
        total_income = sum(income.amount for income in incomes)
        
        # Group by category
        for expense in expenses:
            category = expense.get_category_display()
            if category not in expenses_by_category:
                expenses_by_category[category] = 0
            expenses_by_category[category] += float(expense.amount)
            
        for income in incomes:
            category = income.get_category_display()
            if category not in incomes_by_category:
                incomes_by_category[category] = 0
            incomes_by_category[category] += float(income.amount)
    
    # Get available years and months for filtering
    available_years = []
    available_months = []
    
    if current_doctor:
        # Get years with expenses
        expense_years = Expense.objects.filter(doctor=current_doctor).values_list('expense_date__year', flat=True).distinct()
        available_years = sorted(expense_years, reverse=True)
        
        # Get months for the selected year
        if selected_year:
            expense_months = Expense.objects.filter(
                doctor=current_doctor,
                expense_date__year=selected_year
            ).values_list('expense_date__month', flat=True).distinct()
            available_months = sorted(expense_months, reverse=True)
    
    # Add current year if not in the list
    current_year = timezone.now().year
    if current_year not in available_years:
        available_years.insert(0, current_year)
    
    # Add current month if not in the list
    current_month = timezone.now().month
    if selected_year == current_year and current_month not in available_months:
        available_months.insert(0, current_month)
    
    context = {
        'active_tab': 'finance',
        'expenses': expenses,
        'incomes': incomes,
        'total_expenses': total_expenses,
        'total_income': total_income,
        'expenses_by_category': expenses_by_category,
        'incomes_by_category': incomes_by_category,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'available_years': available_years,
        'available_months': available_months,
        'current_doctor': current_doctor,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
@require_http_methods(["GET"])
def api_incomes(request):
    """API endpoint to get incomes with filtering"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
        # Get filter parameters
        selected_year = request.GET.get('year')
        selected_month = request.GET.get('month')
        
        # Build filter query
        filter_query = {'doctor': current_doctor}
        
        if selected_year:
            filter_query['income_date__year'] = int(selected_year)
        if selected_month:
            filter_query['income_date__month'] = int(selected_month)
        
        # Get incomes
        incomes = Income.objects.filter(**filter_query).order_by('-income_date')
        
        # Serialize incomes
        incomes_data = []
        for income in incomes:
            incomes_data.append({
                'id': income.id,
                'description': income.description,
                'amount': float(income.amount),
                'category': income.category,
                'category_display': income.get_category_display(),
                'income_date': income.income_date.strftime('%d/%m/%Y'),
                'payment_method': income.payment_method,
                'payment_method_display': income.get_payment_method_display() if income.payment_method else None,
                'notes': income.notes,
                'created_at': income.created_at.strftime('%d/%m/%Y %H:%M')
            })
        
        return JsonResponse({
            'success': True,
            'incomes': incomes_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar receitas: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_expenses(request):
    """API endpoint to get expenses with filtering"""
    try:
        # Get current user's doctor profile
        current_doctor = Doctor.objects.get(user=request.user)
        
        # Get filter parameters
        year = request.GET.get('year')
        month = request.GET.get('month')
        category = request.GET.get('category')
        
        # Build filter
        filters = {'doctor': current_doctor}
        
        if year:
            filters['expense_date__year'] = int(year)
        if month:
            filters['expense_date__month'] = int(month)
        if category:
            filters['category'] = category
        
        # Get expenses
        expenses = Expense.objects.filter(**filters).order_by('-expense_date')
        
        # Serialize expenses
        expenses_data = []
        for expense in expenses:
            expenses_data.append({
                'id': expense.id,
                'description': expense.description,
                'amount': float(expense.amount),
                'formatted_amount': expense.formatted_amount,
                'category': expense.get_category_display(),
                'category_value': expense.category,
                'expense_date': expense.expense_date.strftime('%d/%m/%Y'),
                'vendor': expense.vendor or '',
                'receipt_number': expense.receipt_number or '',
                'notes': expense.notes or '',
                'created_at': expense.created_at.strftime('%d/%m/%Y %H:%M'),
            })
        
        return JsonResponse({
            'success': True,
            'expenses': expenses_data
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Perfil de médico não encontrado'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar despesas: {str(e)}'
        })


@login_required
@require_POST
def api_create_income(request):
    """API endpoint to create a new income"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
        # Get form data
        description = request.POST.get('description')
        amount = request.POST.get('amount')
        category = request.POST.get('category')
        income_date = request.POST.get('income_date')
        payment_method = request.POST.get('payment_method', '')
        notes = request.POST.get('notes', '')
        appointment_id = request.POST.get('appointment_id', '')
        patient_id = request.POST.get('patient_id', '')
        
        # Check if creating new patient
        create_patient = request.POST.get('create_patient', 'false') == 'true'
        patient = None
        
        # Handle patient creation or selection
        if create_patient:
            # Create new patient
            patient_first_name = request.POST.get('patient_first_name', '').strip()
            patient_last_name = request.POST.get('patient_last_name', '').strip()
            patient_date_of_birth = request.POST.get('patient_date_of_birth')
            patient_gender = request.POST.get('patient_gender')
            patient_email = request.POST.get('patient_email', '').strip()
            patient_phone = request.POST.get('patient_phone', '').strip()
            
            # Validate required patient fields
            if not all([patient_first_name, patient_last_name, patient_date_of_birth, patient_gender]):
                return JsonResponse({
                    'success': False,
                    'error': 'Nome, sobrenome, data de nascimento e sexo são obrigatórios para criar paciente'
                })
            
            # Check if patient already exists
            existing_patient = Patient.objects.filter(
                first_name__iexact=patient_first_name,
                last_name__iexact=patient_last_name,
                date_of_birth=patient_date_of_birth,
                doctor=current_doctor
            ).first()
            
            if existing_patient:
                patient = existing_patient
            else:
                # Create new patient
                patient = Patient.objects.create(
                    doctor=current_doctor,
                    first_name=patient_first_name,
                    last_name=patient_last_name,
                    date_of_birth=patient_date_of_birth,
                    gender=patient_gender,
                    email=patient_email if patient_email else None,
                    phone=patient_phone if patient_phone else None,
                    is_active=True
                )
        elif patient_id:
            # Use existing patient
            try:
                patient = Patient.objects.get(id=patient_id, doctor=current_doctor)
            except Patient.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Paciente não encontrado'
                })
        elif appointment_id:
            # Auto-link patient from appointment
            try:
                appointment = Appointment.objects.get(id=appointment_id, doctor=current_doctor)
                patient = appointment.patient
            except Appointment.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Consulta não encontrada'
                })
        
        # Validate required fields
        if not all([description, amount, category]):
            return JsonResponse({
                'success': False,
                'error': 'Descrição, valor e categoria são obrigatórios'
            })
        
        # Convert amount to decimal
        try:
            amount_decimal = Decimal(amount)
        except (ValueError, InvalidOperation):
            return JsonResponse({
                'success': False,
                'error': 'Valor inválido'
            })
        
        # Parse income date
        if income_date:
            try:
                income_date_obj = datetime.strptime(income_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Data inválida'
                })
        else:
            income_date_obj = timezone.now().date()
        
        # Get appointment if appointment_id is provided
        appointment = None
        if appointment_id:
            try:
                appointment = Appointment.objects.get(id=appointment_id, doctor=current_doctor)
            except Appointment.DoesNotExist:
                pass  # Appointment not found, but continue without it
        
        # Create the income
        income = Income.objects.create(
            doctor=current_doctor,
            amount=amount_decimal,
            description=description,
            category=category,
            income_date=income_date_obj,
            payment_method=payment_method,
            notes=notes,
            patient=patient,
            appointment=appointment
        )
        
        return JsonResponse({
            'success': True,
            'income_id': income.id,
            'message': f'Receita criada com sucesso: {description}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar receita: {str(e)}'
        })


@login_required
@require_POST
@csrf_exempt
def api_create_expense(request):
    """API endpoint to create a new expense"""
    try:
        # Get current user's doctor profile
        current_doctor = Doctor.objects.get(user=request.user)
        
        # Get form data
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '').strip()
        category = request.POST.get('category', '').strip()
        expense_date = request.POST.get('expense_date', '').strip()
        vendor = request.POST.get('vendor', '').strip()
        receipt_number = request.POST.get('receipt_number', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # Validate required fields
        if not description:
            return JsonResponse({
                'success': False,
                'error': 'Descrição é obrigatória'
            })
        
        if not amount:
            return JsonResponse({
                'success': False,
                'error': 'Valor é obrigatório'
            })
        
        if not category:
            return JsonResponse({
                'success': False,
                'error': 'Categoria é obrigatória'
            })
        
        # Validate amount
        try:
            amount = float(amount.replace(',', '.'))
            if amount <= 0:
                raise ValueError()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Valor deve ser um número positivo'
            })
        
        # Validate date
        if expense_date:
            try:
                from datetime import datetime
                expense_date = datetime.strptime(expense_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Data inválida'
                })
        else:
            expense_date = timezone.now().date()
        
        # Create expense
        expense = Expense.objects.create(
            doctor=current_doctor,
            description=description,
            amount=amount,
            category=category,
            expense_date=expense_date,
            vendor=vendor or None,
            receipt_number=receipt_number or None,
            notes=notes or None
        )
        
        return JsonResponse({
            'success': True,
            'expense': {
                'id': expense.id,
                'description': expense.description,
                'amount': float(expense.amount),
                'formatted_amount': expense.formatted_amount,
                'category': expense.get_category_display(),
                'expense_date': expense.expense_date.strftime('%d/%m/%Y'),
                'vendor': expense.vendor or '',
                'receipt_number': expense.receipt_number or '',
                'notes': expense.notes or '',
            }
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Perfil de médico não encontrado'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar despesa: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_expense_totals(request):
    """API endpoint to get expense totals by period"""
    try:
        # Get current user's doctor profile
        current_doctor = Doctor.objects.get(user=request.user)
        
        # Get filter parameters
        year = request.GET.get('year', timezone.now().year)
        month = request.GET.get('month', timezone.now().month)
        
        # Get expenses for the period
        expenses = Expense.objects.filter(
            doctor=current_doctor,
            expense_date__year=int(year),
            expense_date__month=int(month)
        )
        
        # Calculate totals
        total_amount = sum(expense.amount for expense in expenses)
        
        # Group by category
        category_totals = {}
        for expense in expenses:
            category = expense.get_category_display()
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += float(expense.amount)
        
        return JsonResponse({
            'success': True,
            'total_amount': float(total_amount),
            'formatted_total': f"R$ {total_amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'category_totals': category_totals,
            'expense_count': expenses.count()
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Perfil de médico não encontrado'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao calcular totais: {str(e)}'
        })


@login_required
@require_http_methods(["DELETE"])
def api_delete_expense(request, expense_id):
    """API endpoint to delete an expense"""
    try:
        # Get current user's doctor profile
        current_doctor = Doctor.objects.get(user=request.user)
        
        # Get the expense
        try:
            expense = Expense.objects.get(id=expense_id, doctor=current_doctor)
        except Expense.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Despesa não encontrada'
            })
        
        # Delete the expense
        expense.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Despesa "{expense.description}" excluída com sucesso'
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Perfil de médico não encontrado'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao excluir despesa: {str(e)}'
        })


@login_required
@require_http_methods(["DELETE"])
def api_delete_income(request, income_id):
    """API endpoint to delete an income"""
    try:
        # Get current user's doctor profile
        current_doctor = Doctor.objects.get(user=request.user)
        
        # Get the income
        try:
            income = Income.objects.get(id=income_id, doctor=current_doctor)
        except Income.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Receita não encontrada'
            })
        
        # Delete the income
        income.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Receita "{income.description}" excluída com sucesso'
        })
        
    except Doctor.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Perfil de médico não encontrado'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao excluir receita: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def api_deactivate_patient(request, patient_id):
    """API endpoint to deactivate a patient"""
    try:
        # Get the patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Paciente não encontrado'
            })
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para desativar este paciente'
            })
        
        # Check if patient is already inactive
        if not patient.is_active:
            return JsonResponse({
                'success': False,
                'error': 'Paciente já está inativo'
            })
        
        # Deactivate the patient
        patient.is_active = False
        patient.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Paciente "{patient.full_name}" desativado com sucesso'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao desativar paciente: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def api_activate_patient(request, patient_id):
    """API endpoint to activate a patient"""
    try:
        # Get the patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Paciente não encontrado'
            })
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para ativar este paciente'
            })
        
        # Check if patient is already active
        if patient.is_active:
            return JsonResponse({
                'success': False,
                'error': 'Paciente já está ativo'
            })
        
        # Activate the patient
        patient.is_active = True
        patient.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Paciente "{patient.full_name}" ativado com sucesso'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao ativar paciente: {str(e)}'
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
        cpf = request.POST.get('cpf', '').strip()
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        zip_code = request.POST.get('zip_code', '').strip()
        emergency_contact_name = request.POST.get('emergency_contact_name', '').strip()
        emergency_contact_phone = request.POST.get('emergency_contact_phone', '').strip()
        medical_insurance = request.POST.get('medical_insurance', '').strip()
        
        # Validate required fields
        if not all([first_name, last_name, date_of_birth, gender]):
            return JsonResponse({
                'success': False,
                'error': 'Nome, sobrenome, data de nascimento e sexo são obrigatórios'
            })
        
        # Get the current doctor for the user
        from accounts.utils import get_user_role
        from accounts.utils import get_doctor_for_user
        
        role = get_user_role(request.user)
        doctor = None
        
        if role == 'admin':
            # For admins, first check if they have a doctor_profile (some admins are also doctors)
            if hasattr(request.user, 'doctor_profile'):
                doctor = request.user.doctor_profile
            else:
                # Otherwise, use get_selected_doctor which checks session
                doctor = get_selected_doctor(request)
        else:
            doctor = get_doctor_for_user(request.user)
        
        if not doctor:
            error_msg = 'Usuário não tem um perfil de médico associado'
            if role == 'admin':
                error_msg += ' ou nenhum médico foi selecionado'
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        
        # Create the patient assigned to the current doctor
        patient = Patient.objects.create(
            doctor=doctor,
            first_name=first_name,
            last_name=last_name,
            email=email if email else None,
            phone=phone if phone else None,
            cpf=cpf if cpf else None,
            date_of_birth=date_of_birth,
            gender=gender,
            address=address if address else None,
            city=city if city else None,
            state=state if state else None,
            zip_code=zip_code if zip_code else None,
            emergency_contact_name=emergency_contact_name if emergency_contact_name else None,
            emergency_contact_phone=emergency_contact_phone if emergency_contact_phone else None,
            medical_insurance=medical_insurance if medical_insurance else None,
            is_active=True
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

@login_required
@require_POST
def api_update_patient(request):
    """API endpoint to update a patient"""
    try:
        # Get form data
        patient_id = request.POST.get('patient_id')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        cpf = request.POST.get('cpf', '').strip()
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        zip_code = request.POST.get('zip_code', '').strip()
        emergency_contact_name = request.POST.get('emergency_contact_name', '').strip()
        emergency_contact_phone = request.POST.get('emergency_contact_phone', '').strip()
        medical_insurance = request.POST.get('medical_insurance', '').strip()
        
        # Validate required fields
        if not all([patient_id, first_name, last_name, date_of_birth, gender]):
            return JsonResponse({
                'success': False,
                'error': 'ID do paciente, nome, sobrenome, data de nascimento e sexo são obrigatórios'
            })
        
        # Get the patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Paciente não encontrado'
            })
        
        # Check if user has access to this patient
        if not has_access_to_patient(request.user, patient):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para atualizar este paciente'
            })
        
        # Update patient fields
        patient.first_name = first_name
        patient.last_name = last_name
        patient.email = email if email else None
        patient.phone = phone if phone else None
        patient.cpf = cpf if cpf else None
        patient.date_of_birth = date_of_birth
        patient.gender = gender
        patient.address = address if address else None
        patient.city = city if city else None
        patient.state = state if state else None
        patient.zip_code = zip_code if zip_code else None
        patient.emergency_contact_name = emergency_contact_name if emergency_contact_name else None
        patient.emergency_contact_phone = emergency_contact_phone if emergency_contact_phone else None
        patient.medical_insurance = medical_insurance if medical_insurance else None
        
        patient.save()
        
        # Helper function to safely format dates
        def safe_date_format(date_obj, format_str):
            if date_obj and hasattr(date_obj, 'strftime'):
                return date_obj.strftime(format_str)
            elif date_obj:
                return str(date_obj)
            else:
                return ''
        
        # Return updated patient data
        patient_data = {
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'email': patient.email,
            'phone': patient.phone,
            'cpf': patient.cpf or '',
            'date_of_birth': safe_date_format(patient.date_of_birth, '%Y-%m-%d'),
            'gender': patient.gender,
            'address': patient.address,
            'city': patient.city,
            'state': patient.state,
            'zip_code': patient.zip_code,
            'emergency_contact_name': patient.emergency_contact_name,
            'emergency_contact_phone': patient.emergency_contact_phone,
            'medical_insurance': patient.medical_insurance,
            'full_name': patient.full_name,
            'age': patient.age if patient.age is not None else 0,
            'is_active': patient.is_active,
            'created_at': safe_date_format(patient.created_at, '%d/%m/%Y'),
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Paciente {patient.full_name} atualizado com sucesso',
            'patient': patient_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao atualizar paciente: {str(e)}'
        })


@login_required
@require_POST
def select_doctor(request):
    """API endpoint for admin to select a doctor to view as"""
    try:
        # Check if user is admin
        role = get_user_role(request.user)
        if role != 'admin':
            return JsonResponse({
                'success': False,
                'error': 'Apenas administradores podem selecionar médicos'
            })
        
        # Get doctor ID from request
        doctor_id = request.POST.get('doctor_id', '').strip()
        
        if not doctor_id:
            # Clear the selection to show all doctors
            request.session.pop('selected_doctor_id', None)
            
            return JsonResponse({
                'success': True,
                'message': 'Visualizando todos os médicos'
            })
        
        # Get the doctor
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado'
            })
        
        # Check if admin can access this doctor
        if not can_access_doctor(request.user, doctor):
            return JsonResponse({
                'success': False,
                'error': 'Você não tem acesso a este médico'
            })
        
        # Store selected doctor in session
        request.session['selected_doctor_id'] = doctor.id
        
        return JsonResponse({
            'success': True,
            'message': f'Visualizando como Dr. {doctor.full_name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao selecionar médico: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_quick_stats(request):
    """API endpoint to get quick stats for reports"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        
        # Get date range (optional, defaults to current month)
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date:
            start_date = timezone.now().date().replace(day=1)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        if not end_date:
            end_date = timezone.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get stats
        if current_doctor:
            completed_appointments = Appointment.objects.filter(
                doctor=current_doctor,
                appointment_date__range=[start_date, end_date],
                status='completed'
            ).count()
            
            total_revenue = Income.objects.filter(
                doctor=current_doctor,
                income_date__range=[start_date, end_date]
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            unique_patients = Appointment.objects.filter(
                doctor=current_doctor,
                appointment_date__range=[start_date, end_date],
                status='completed'
            ).values('patient').distinct().count()
        else:
            # For admins without doctor selection, show aggregated stats
            completed_appointments = Appointment.objects.filter(
                appointment_date__range=[start_date, end_date],
                status='completed'
            ).count()
            
            total_revenue = Income.objects.filter(
                income_date__range=[start_date, end_date]
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            unique_patients = Appointment.objects.filter(
                appointment_date__range=[start_date, end_date],
                status='completed'
            ).values('patient').distinct().count()
        
        return JsonResponse({
            'success': True,
            'stats': {
                'completed_appointments': completed_appointments,
                'total_revenue': float(total_revenue),
                'unique_patients': unique_patients,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao buscar estatísticas: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_generate_report(request):
    """API endpoint to generate report data"""
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        
        # Get report parameters
        report_type = request.GET.get('report_type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not all([report_type, start_date, end_date]):
            return JsonResponse({
                'success': False,
                'error': 'Parâmetros obrigatórios: report_type, start_date, end_date'
            })
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de data inválido (use YYYY-MM-DD)'
            })
        
        # Build base query
        base_filter = {
            'appointment_date__range': [start_date, end_date],
            'status': 'completed'
        }
        
        if current_doctor:
            base_filter['doctor'] = current_doctor
        
        # Generate report based on type
        if report_type == 'appointments':
            # Appointments report
            appointments = Appointment.objects.filter(**base_filter).select_related('patient', 'doctor')
            
            data = []
            for apt in appointments:
                data.append({
                    'date': apt.appointment_date.strftime('%d/%m/%Y'),
                    'time': apt.appointment_time.strftime('%H:%M'),
                    'patient': apt.patient.full_name,
                    'doctor': apt.doctor.full_name,
                    'type': apt.get_appointment_type_display(),
                    'payment': apt.get_payment_type_display(),
                    'value': float(apt.value) if apt.value else 0,
                    'status': apt.get_status_display(),
                })
            
            return JsonResponse({
                'success': True,
                'report_type': 'appointments',
                'data': data,
                'summary': {
                    'total_appointments': len(data),
                    'total_revenue': sum(item['value'] for item in data),
                    'start_date': start_date.strftime('%d/%m/%Y'),
                    'end_date': end_date.strftime('%d/%m/%Y'),
                }
            })
            
        elif report_type == 'payment_methods':
            # Payment methods report
            appointments = Appointment.objects.filter(**base_filter).values('payment_type')
            payment_methods = {}
            
            for apt in appointments:
                payment_type = apt['payment_type']
                payment_methods[payment_type] = payment_methods.get(payment_type, 0) + 1
            
            data = []
            for method, count in payment_methods.items():
                data.append({
                    'payment_method': method,
                    'count': count,
                })
            
            return JsonResponse({
                'success': True,
                'report_type': 'payment_methods',
                'data': data,
                'summary': {
                    'total_appointments': sum(item['count'] for item in data),
                    'start_date': start_date.strftime('%d/%m/%Y'),
                    'end_date': end_date.strftime('%d/%m/%Y'),
                }
            })
            
        elif report_type == 'patient_summary':
            # Patient summary report
            appointments = Appointment.objects.filter(**base_filter).values('patient', 'patient__first_name', 'patient__last_name')
            patient_counts = {}
            
            for apt in appointments:
                patient_id = apt['patient']
                patient_name = f"{apt['patient__first_name']} {apt['patient__last_name']}"
                patient_counts[patient_id] = {
                    'name': patient_name,
                    'count': patient_counts.get(patient_id, {}).get('count', 0) + 1
                }
            
            data = []
            for patient_id, info in patient_counts.items():
                data.append({
                    'patient_name': info['name'],
                    'total_appointments': info['count'],
                })
            
            # Sort by appointment count (descending)
            data.sort(key=lambda x: x['total_appointments'], reverse=True)
            
            return JsonResponse({
                'success': True,
                'report_type': 'patient_summary',
                'data': data[:20],  # Limit to top 20
                'summary': {
                    'total_patients': len(patient_counts),
                    'start_date': start_date.strftime('%d/%m/%Y'),
                    'end_date': end_date.strftime('%d/%m/%Y'),
                }
            })
            
        elif report_type == 'financial_summary':
            # Financial summary report
            appointments = Appointment.objects.filter(**base_filter)
            
            income_by_category = {}
            income_by_method = {}
            total_revenue = 0
            
            for apt in appointments:
                if apt.value:
                    category = apt.appointment_type
                    method = apt.payment_type
                    
                    income_by_category[category] = income_by_category.get(category, 0) + float(apt.value)
                    income_by_method[method] = income_by_method.get(method, 0) + float(apt.value)
                    total_revenue += float(apt.value)
            
            data = {
                'by_category': [{'category': k, 'amount': v} for k, v in income_by_category.items()],
                'by_method': [{'method': k, 'amount': v} for k, v in income_by_method.items()],
                'total_revenue': total_revenue,
            }
            
            return JsonResponse({
                'success': True,
                'report_type': 'financial_summary',
                'data': data,
                'summary': {
                    'total_revenue': total_revenue,
                    'start_date': start_date.strftime('%d/%m/%Y'),
                    'end_date': end_date.strftime('%d/%m/%Y'),
                }
            })
            
        elif report_type == 'monthly_appointments':
            # Monthly appointments report
            monthly_data = {}
            
            # Get all completed appointments in the date range
            appointments = Appointment.objects.filter(**base_filter)
            
            for apt in appointments:
                month_key = apt.appointment_date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'month': apt.appointment_date.strftime('%m/%Y'),
                        'count': 0
                    }
                monthly_data[month_key]['count'] += 1
            
            data = sorted(monthly_data.values(), key=lambda x: x['month'])
            
            return JsonResponse({
                'success': True,
                'report_type': 'monthly_appointments',
                'data': data,
                'summary': {
                    'total_appointments': sum(item['count'] for item in data),
                    'start_date': start_date.strftime('%d/%m/%Y'),
                    'end_date': end_date.strftime('%d/%m/%Y'),
                }
            })
        
        return JsonResponse({
            'success': False,
            'error': f'Tipo de relatório inválido: {report_type}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao gerar relatório: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def api_generate_pdf_report(request):
    """API endpoint to generate a PDF report"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from io import BytesIO
        
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        
        # Get report parameters
        report_type = request.GET.get('report_type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not all([report_type, start_date, end_date]):
            return JsonResponse({
                'success': False,
                'error': 'Parâmetros obrigatórios: report_type, start_date, end_date'
            })
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de data inválido (use YYYY-MM-DD)'
            })
        
        # Build base query
        base_filter = {
            'appointment_date__range': [start_date, end_date],
            'status': 'completed'
        }
        
        if current_doctor:
            base_filter['doctor'] = current_doctor
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, 
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        # Container for the PDF elements
        story = []
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Header style
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12
        )
        
        # Title
        title_text = "RELATÓRIO DE CONSULTAS" if report_type == 'appointments' else "RELATÓRIO"
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Doctor information
        if current_doctor:
            story.append(Paragraph(f"<b>Médico:</b> {current_doctor.full_name}", styles['Normal']))
            if hasattr(current_doctor, 'specialization') and current_doctor.specialization:
                story.append(Paragraph(f"<b>Especialização:</b> {current_doctor.specialization}", styles['Normal']))
            if hasattr(current_doctor, 'medical_license') and current_doctor.medical_license:
                story.append(Paragraph(f"<b>CRM:</b> {current_doctor.medical_license}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Period information
        story.append(Paragraph(f"<b>Período:</b> {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Get report data and generate content
        if report_type == 'appointments':
            appointments = Appointment.objects.filter(**base_filter).select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')
            
            story.append(Paragraph("Lista de Consultas Realizadas", header_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Table data
            table_data = [['Data', 'Horário', 'Paciente', 'Tipo', 'Pagamento', 'Valor']]
            
            for apt in appointments:
                date_str = apt.appointment_date.strftime('%d/%m/%Y')
                time_str = apt.appointment_time.strftime('%H:%M')
                value_str = f"R$ {apt.value:.2f}" if apt.value else "-"
                table_data.append([
                    date_str,
                    time_str,
                    apt.patient.full_name,
                    apt.get_appointment_type_display(),
                    apt.get_payment_type_display(),
                    value_str
                ])
            
            # Create table
            table = Table(table_data, colWidths=[1*inch, 0.8*inch, 2*inch, 1*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.2*inch))
            
            # Summary
            total_appointments = len(table_data) - 1
            total_revenue = sum(float(apt.value) if apt.value else 0 for apt in appointments)
            story.append(Paragraph(f"<b>Total de Consultas:</b> {total_appointments}", styles['Normal']))
            story.append(Paragraph(f"<b>Receita Total:</b> R$ {total_revenue:.2f}", styles['Normal']))
            
        elif report_type == 'financial_summary':
            appointments = Appointment.objects.filter(**base_filter)
            
            story.append(Paragraph("Resumo Financeiro", header_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Calculate totals
            income_by_category = {}
            income_by_method = {}
            total_revenue = 0
            
            for apt in appointments:
                if apt.value:
                    category = apt.get_appointment_type_display()
                    method = apt.get_payment_type_display()
                    
                    income_by_category[category] = income_by_category.get(category, 0) + float(apt.value)
                    income_by_method[method] = income_by_method.get(method, 0) + float(apt.value)
                    total_revenue += float(apt.value)
            
            # Revenue by category table
            if income_by_category:
                story.append(Paragraph("Receita por Categoria", styles['Heading3']))
                table_data = [['Categoria', 'Valor']]
                for category, amount in sorted(income_by_category.items(), key=lambda x: x[1], reverse=True):
                    table_data.append([category, f"R$ {amount:.2f}"])
                
                table = Table(table_data, colWidths=[3*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.2*inch))
            
            # Revenue by payment method table
            if income_by_method:
                story.append(Paragraph("Receita por Método de Pagamento", styles['Heading3']))
                table_data = [['Método', 'Valor']]
                for method, amount in sorted(income_by_method.items(), key=lambda x: x[1], reverse=True):
                    table_data.append([method, f"R$ {amount:.2f}"])
                
                table = Table(table_data, colWidths=[3*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.2*inch))
            
            # Total
            story.append(Paragraph(f"<b>Receita Total:</b> R$ {total_revenue:.2f}", styles['Heading2']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create HTTP response
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{report_type}_{start_date}_{end_date}.pdf"'
        return response
        
    except ImportError:
        return JsonResponse({
            'success': False,
            'error': 'Biblioteca reportlab não instalada. Execute: pip install reportlab'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao gerar PDF: {str(e)}'
        })


def get_selected_doctor(request):
    """Helper function to get the selected doctor from session"""
    role = get_user_role(request.user)
    
    if role == 'admin':
        # Admins can select a doctor to view as
        selected_doctor_id = request.session.get('selected_doctor_id')
        if selected_doctor_id:
            try:
                doctor = Doctor.objects.get(id=selected_doctor_id)
                # Verify admin still has access to this doctor
                if can_access_doctor(request.user, doctor):
                    return doctor
            except Doctor.DoesNotExist:
                pass
    elif role == 'doctor':
        # Doctors see their own data
        return getattr(request.user, 'doctor_profile', None)
    elif role == 'secretary':
        # Secretaries see their assigned doctor's data
        secretary_profile = getattr(request.user, 'secretary_profile', None)
        if secretary_profile:
            return secretary_profile.doctor
        return None
    
    return None