from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation
from .models import Appointment, Patient, Doctor, MedicalRecord, Prescription, PrescriptionItem, PrescriptionTemplate, Expense, Income

@login_required
def home(request):
    """Main medical dashboard view with agenda tab"""
    today = timezone.now().date()
    
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
    
    # Get this week's appointments for the calendar view (excluding cancelled)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    week_appointments = []
    if current_doctor:
        week_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date__range=[start_of_week, end_of_week]
        ).exclude(status='cancelled').order_by('appointment_date', 'appointment_time')
    
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
        
        # Get next appointment (from today onwards, including future appointments today)
        now = timezone.now()
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
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
        # Get form data
        patient_id = request.POST.get('patient')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        duration_minutes = request.POST.get('duration_minutes', 30)
        appointment_type = request.POST.get('appointment_type', 'consultation')
        status = request.POST.get('status', 'scheduled')
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        location = request.POST.get('location', '')
        value = request.POST.get('value', '')
        
        # Validate required fields
        if not all([patient_id, appointment_date, appointment_time]):
            return JsonResponse({
                'success': False,
                'error': 'Paciente, data e horário são obrigatórios'
            })
        
        # Get patient object
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Paciente não encontrado'
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
    """API endpoint to get appointments for a specific week"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
        # Get week parameter
        week_start = request.GET.get('week_start')
        if not week_start:
            return JsonResponse({
                'success': False,
                'error': 'Data de início da semana é obrigatória'
            })
        
        # Parse the date
        try:
            start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de data inválido'
            })
        
        # Calculate end of week
        end_date = start_date + timedelta(days=6)
        
        # Get appointments for the week (excluding cancelled)
        appointments = Appointment.objects.filter(
            doctor=current_doctor,
            appointment_date__range=[start_date, end_date]
        ).exclude(status='cancelled').order_by('appointment_date', 'appointment_time')
        
        # Format appointments for frontend
        appointments_data = []
        for appointment in appointments:
            appointments_data.append({
                'id': appointment.id,
                'patient_name': appointment.patient.full_name,
                'patient_id': appointment.patient.id,
                'doctor_name': appointment.doctor.full_name,
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                'appointment_time': appointment.appointment_time.strftime('%H:%M'),
                'duration_minutes': appointment.duration_minutes,
                'appointment_type': appointment.get_appointment_type_display(),
                'status': appointment.status,
                'reason': appointment.reason,
                'notes': appointment.notes,
                'location': appointment.location
            })
        
        return JsonResponse({
            'success': True,
            'appointments': appointments_data,
            'week_start': start_date.strftime('%Y-%m-%d'),
            'week_end': end_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao carregar consultas: {str(e)}'
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

@login_required
@require_POST
def api_cancel_appointment(request):
    """API endpoint to cancel an appointment"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
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
                doctor=current_doctor
            )
        except Appointment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Consulta não encontrada'
            })
        
        # Check if appointment can be cancelled
        if appointment.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'error': 'Esta consulta já foi cancelada'
            })
        
        if appointment.status == 'completed':
            return JsonResponse({
                'success': False,
                'error': 'Não é possível cancelar uma consulta já concluída'
            })
        
        # Remove any associated income records before cancelling
        income_deleted_count = 0
        associated_incomes = Income.objects.filter(appointment=appointment)
        if associated_incomes.exists():
            income_deleted_count = associated_incomes.count()
            associated_incomes.delete()
        
        # Cancel the appointment
        appointment.cancel(cancellation_reason)
        
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
@require_POST
def api_confirm_attendance(request):
    """API endpoint to confirm patient attendance"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
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
                doctor=current_doctor
            )
        except Appointment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Consulta não encontrada'
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
        
        # Create income record if appointment has a value and is today or in the past
        income_created = False
        if appointment.value and appointment.value > 0:
            # Only create income if appointment date is today or in the past
            from datetime import date
            today = date.today()
            if appointment.appointment_date <= today:
                # Check if income already exists for this appointment
                existing_income = Income.objects.filter(appointment=appointment).first()
                if not existing_income:
                    Income.objects.create(
                        doctor=current_doctor,
                        appointment=appointment,
                        amount=appointment.value,
                        description=f"Consulta - {appointment.patient.full_name}",
                        category=appointment.appointment_type,
                        income_date=appointment.appointment_date,
                        notes=f"Receita gerada pela consulta confirmada em {appointment.appointment_date} às {appointment.appointment_time}"
                    )
                    income_created = True
        
        message = f'Presença de {appointment.patient.full_name} confirmada com sucesso'
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
            'error': f'Erro ao confirmar presença: {str(e)}'
        })


@login_required
@require_POST
def api_sync_appointment_income(request):
    """API endpoint to sync income records for all completed appointments"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
        # Get all completed appointments with values that don't have income records
        # Only include appointments that are confirmed/completed, have values, are not cancelled,
        # and are today or in the past
        from datetime import date
        today = date.today()
        
        completed_appointments = Appointment.objects.filter(
            doctor=current_doctor,
            status__in=['confirmed', 'completed'],  # Both confirmed and completed count as "done"
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
        today = timezone.now().date()
        now = timezone.now()
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

# Prescription Views

@login_required
@require_http_methods(["GET"])
def api_prescriptions(request):
    """API endpoint to get prescriptions for a patient"""
    try:
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
            })
        
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
        
        # Get prescriptions for this patient and doctor
        prescriptions = Prescription.objects.filter(
            patient=patient,
            doctor=current_doctor
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
        # Get current user's doctor profile
        try:
            current_doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuário não é um médico válido'
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
        
        # Create the income
        income = Income.objects.create(
            doctor=current_doctor,
            amount=amount_decimal,
            description=description,
            category=category,
            income_date=income_date_obj,
            payment_method=payment_method,
            notes=notes
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