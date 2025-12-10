"""
Waiting List API Views
"""
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse
from .models import WaitingListEntry, Patient, Doctor

# Import get_selected_doctor from views (it's defined there)
# We'll define a local version to avoid circular import
def get_selected_doctor(request):
    """Get the currently selected doctor for the request"""
    from accounts.utils import get_user_role
    from .models import Doctor
    
    role = get_user_role(request.user)
    
    if role == 'admin':
        # Admins can select a doctor to view as
        selected_doctor_id = request.session.get('selected_doctor_id')
        if selected_doctor_id:
            try:
                doctor = Doctor.objects.get(id=selected_doctor_id)
                # Verify admin still has access to this doctor
                from accounts.utils import can_access_doctor
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


@login_required
@require_http_methods(["GET", "POST"])
def api_waiting_list(request):
    """
    API endpoint to get or create waiting list entries
    GET: Retrieve active waitlist, sorted by urgency (High first) then date (Oldest first)
    POST: Add a patient to the waitlist
    """
    try:
        # Get current doctor (from selection for admins, or user's doctor)
        current_doctor = get_selected_doctor(request)
        
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado'
            })
        
        if request.method == 'GET':
            # Get query parameters
            status_filter = request.GET.get('status', 'pending')  # Default to pending
            
            # Build query
            queryset = WaitingListEntry.objects.filter(doctor=current_doctor)
            
            # Filter by status if provided
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Sort by urgency (high first) then by created_at (oldest first)
            # We'll use a custom ordering
            entries = list(queryset.all())
            entries.sort(key=lambda x: (-x.get_urgency_priority(), x.created_at))
            
            # Serialize entries
            entries_data = []
            for entry in entries:
                entries_data.append({
                    'id': entry.id,
                    'patient_id': entry.patient.id if entry.patient else None,
                    'patient_name': entry.patient_name,
                    'phone': entry.phone or '',
                    'email': entry.email or '',
                    'preferred_days_times': entry.preferred_days_times or '',
                    'urgency_level': entry.urgency_level,
                    'urgency_display': entry.get_urgency_level_display(),
                    'status': entry.status,
                    'status_display': entry.get_status_display(),
                    'notes': entry.notes or '',
                    'created_at': entry.created_at.isoformat(),
                    'contact_info': entry.contact_info,
                })
            
            return JsonResponse({
                'success': True,
                'entries': entries_data,
                'count': len(entries_data)
            })
        
        elif request.method == 'POST':
            # Get form data
            patient_id = request.POST.get('patient_id')
            patient_name = request.POST.get('patient_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            preferred_days_times = request.POST.get('preferred_days_times', '').strip()
            urgency_level = request.POST.get('urgency_level', 'medium')
            notes = request.POST.get('notes', '').strip()
            
            # Validate required fields
            if not patient_name:
                return JsonResponse({
                    'success': False,
                    'error': 'Nome do paciente é obrigatório'
                })
            
            # Validate urgency level
            if urgency_level not in ['low', 'medium', 'high']:
                urgency_level = 'medium'
            
            # Get patient if patient_id is provided
            patient = None
            if patient_id:
                try:
                    patient = Patient.objects.get(id=patient_id)
                    # Use patient's name if not provided
                    if not patient_name:
                        patient_name = patient.full_name
                    # Use patient's contact info if not provided
                    if not phone and patient.phone:
                        phone = patient.phone
                    if not email and patient.email:
                        email = patient.email
                except Patient.DoesNotExist:
                    pass
            
            # Create waiting list entry
            entry = WaitingListEntry.objects.create(
                doctor=current_doctor,
                patient=patient,
                patient_name=patient_name,
                phone=phone or None,
                email=email or None,
                preferred_days_times=preferred_days_times or None,
                urgency_level=urgency_level,
                notes=notes or None,
                status='pending'
            )
            
            return JsonResponse({
                'success': True,
                'entry_id': entry.id,
                'message': f'{patient_name} adicionado à lista de espera com sucesso'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao processar lista de espera: {str(e)}'
        })


@login_required
@require_http_methods(["DELETE"])
def api_waiting_list_entry(request, entry_id):
    """
    API endpoint to delete a waiting list entry
    DELETE: Remove entry from list
    """
    try:
        # Get current doctor
        current_doctor = get_selected_doctor(request)
        
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado'
            })
        
        # Get entry
        try:
            entry = WaitingListEntry.objects.get(id=entry_id, doctor=current_doctor)
        except WaitingListEntry.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Entrada não encontrada'
            })
        
        entry.delete()
        return JsonResponse({
            'success': True,
            'message': 'Entrada removida da lista de espera'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao processar entrada: {str(e)}'
        })


@login_required
@require_http_methods(["PUT", "POST"])
def api_update_waiting_list_entry(request, entry_id):
    """
    API endpoint to update a waiting list entry
    PUT/POST: Update entry fields
    """
    try:
        # Get current doctor
        current_doctor = get_selected_doctor(request)
        
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado'
            })
        
        # Get entry
        try:
            entry = WaitingListEntry.objects.get(id=entry_id, doctor=current_doctor)
        except WaitingListEntry.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Entrada não encontrada'
            })
        
        # Get update data - FormData is sent as multipart/form-data
        # Use request.POST which Django parses automatically for POST/PUT with FormData
        data = request.POST
        
        # Update fields if provided
        if 'status' in data:
            entry.status = data['status']
        
        if 'urgency_level' in data:
            urgency = data['urgency_level']
            if urgency in ['low', 'medium', 'high']:
                entry.urgency_level = urgency
        
        # Update patient if patient_id is provided
        if 'patient_id' in data:
            patient_id = data['patient_id']
            if patient_id and str(patient_id).strip():
                try:
                    patient = Patient.objects.get(id=patient_id, doctor=current_doctor)
                    entry.patient = patient
                except Patient.DoesNotExist:
                    pass
            else:
                # If patient_id is empty, set patient to None
                entry.patient = None
        
        if 'patient_name' in data:
            entry.patient_name = data['patient_name'].strip()
        
        if 'phone' in data:
            entry.phone = data['phone'].strip() or None
        
        if 'email' in data:
            entry.email = data['email'].strip() or None
        
        if 'preferred_days_times' in data:
            entry.preferred_days_times = data['preferred_days_times'].strip() or None
        
        if 'notes' in data:
            entry.notes = data['notes'].strip() or None
        
        entry.save()
        
        # Return complete entry data
        return JsonResponse({
            'success': True,
            'message': 'Entrada atualizada com sucesso',
            'entry': {
                'id': entry.id,
                'patient_id': entry.patient.id if entry.patient else None,
                'patient_name': entry.patient_name,
                'phone': entry.phone or '',
                'email': entry.email or '',
                'preferred_days_times': entry.preferred_days_times or '',
                'urgency_level': entry.urgency_level,
                'urgency_display': entry.get_urgency_level_display(),
                'status': entry.status,
                'status_display': entry.get_status_display(),
                'notes': entry.notes or '',
                'created_at': entry.created_at.isoformat(),
                'contact_info': entry.contact_info,
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao atualizar entrada: {str(e)}'
        })


@login_required
@require_POST
def api_convert_waitlist_to_appointment(request, entry_id):
    """
    API endpoint to convert a waiting list entry to an appointment
    This will pre-fill the appointment form with the patient's data
    """
    try:
        # Get current doctor
        current_doctor = get_selected_doctor(request)
        
        if not current_doctor:
            return JsonResponse({
                'success': False,
                'error': 'Médico não encontrado'
            })
        
        # Get entry
        try:
            entry = WaitingListEntry.objects.get(id=entry_id, doctor=current_doctor)
        except WaitingListEntry.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Entrada não encontrada'
            })
        
        # Return entry data for pre-filling appointment form
        return JsonResponse({
            'success': True,
            'entry': {
                'id': entry.id,
                'patient_id': entry.patient.id if entry.patient else None,
                'patient_name': entry.patient_name,
                'phone': entry.phone or '',
                'email': entry.email or '',
                'preferred_days_times': entry.preferred_days_times or '',
                'urgency_level': entry.urgency_level,
                'notes': entry.notes or '',
            },
            'message': 'Dados do paciente carregados. Preencha a data e horário da consulta.'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao converter entrada: {str(e)}'
        })

