"""
WhatsApp webhook views for handling incoming messages and managing conversations
"""
import json
import os
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from datetime import datetime, timedelta
from .models import WhatsAppConversation, Doctor, Appointment, Patient
from .whatsapp_service import (
    send_whatsapp_message,
    send_whatsapp_interactive_message,
    get_available_doctors,
    get_available_dates_for_week,
    get_available_times,
    format_date_br,
    WHATSAPP_VERIFY_TOKEN
)

# Set up logger
logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    WhatsApp webhook endpoint for receiving messages and verifying webhook
    """
    if request.method == "GET":
        # Webhook verification
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token', '').strip()
        challenge = request.GET.get('hub.challenge')
        
        # Get verify token (trimmed)
        expected_token = WHATSAPP_VERIFY_TOKEN.strip() if WHATSAPP_VERIFY_TOKEN else ''
        
        # Debug logging
        logger.info(f"Webhook verification - Mode: {mode}, Token received: '{token}', Expected: '{expected_token}'")
        
        if mode == 'subscribe' and token == expected_token:
            logger.info(f"Verification successful! Returning challenge: {challenge}")
            return HttpResponse(challenge, content_type='text/plain')
        else:
            logger.warning(f"Verification failed - Mode match: {mode == 'subscribe'}, Token match: {token == expected_token}")
            return HttpResponse('Verification failed', status=403)
    
    elif request.method == "POST":
        # Handle incoming messages
        try:
            body = json.loads(request.body)
            
            # Log the full webhook payload
            logger.info(f"WhatsApp Webhook Received - Full payload: {json.dumps(body, indent=2)}")
            
            # WhatsApp webhook structure
            if 'entry' in body:
                for entry in body['entry']:
                    logger.info(f"Processing entry: {json.dumps(entry, indent=2)}")
                    
                    if 'changes' in entry:
                        for change in entry['changes']:
                            logger.info(f"Processing change: {json.dumps(change, indent=2)}")
                            
                            if 'value' in change:
                                value = change['value']
                                
                                # Log metadata
                                if 'metadata' in value:
                                    logger.info(f"Message metadata: {json.dumps(value['metadata'], indent=2)}")
                                
                                # Handle messages
                                if 'messages' in value:
                                    for message in value['messages']:
                                        logger.info(f"Received WhatsApp message: {json.dumps(message, indent=2)}")
                                        handle_whatsapp_message(message)
                                
                                # Log status updates
                                if 'statuses' in value:
                                    for status in value['statuses']:
                                        logger.info(f"Message status update: {json.dumps(status, indent=2)}")
            
            return JsonResponse({'status': 'ok'}, status=200)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)


def handle_whatsapp_message(message):
    """
    Handle incoming WhatsApp message and process conversation flow
    """
    try:
        phone_number = message.get('from')
        message_type = message.get('type')
        message_id = message.get('id')
        timestamp = message.get('timestamp')
        
        logger.info(f"Handling message from {phone_number} - Type: {message_type}, ID: {message_id}, Timestamp: {timestamp}")
        
        if message_type != 'text' and message_type != 'interactive':
            logger.info(f"Ignoring message type: {message_type}")
            return
        
        # Get or create conversation
        conversation, created = WhatsAppConversation.objects.get_or_create(
            phone_number=phone_number,
            defaults={'state': 'initial'}
        )
        
        if created:
            logger.info(f"Created new conversation for {phone_number}")
        else:
            logger.info(f"Found existing conversation for {phone_number} - State: {conversation.state}")
        
        # Get message text
        if message_type == 'text':
            message_text = message.get('text', {}).get('body', '').strip()
            logger.info(f"Text message received: '{message_text}'")
        elif message_type == 'interactive':
            # Handle button click
            interactive = message.get('interactive', {})
            button_response = interactive.get('button_reply', {})
            message_text = button_response.get('id', '').strip()
            logger.info(f"Interactive message (button) received: '{message_text}'")
        else:
            return
        
        # Process message based on conversation state
        logger.info(f"Processing conversation - State: {conversation.state}, Message: '{message_text}'")
        process_conversation(conversation, message_text)
        
    except Exception as e:
        logger.error(f"Error handling WhatsApp message: {e}", exc_info=True)
        import traceback
        traceback.print_exc()


def process_conversation(conversation, message_text):
    """
    Process conversation based on current state
    """
    message_text_lower = message_text.lower()
    
    # Handle cancel/restart commands
    if message_text_lower in ['cancelar', 'cancel', 'inicio', 'começar', 'comecar', 'start']:
        conversation.reset()
        send_whatsapp_message(
            conversation.phone_number,
            "✅ Conversa reiniciada! Como posso ajudá-lo hoje?"
        )
        return
    
    # State machine
    if conversation.state == 'initial':
        handle_initial_state(conversation, message_text)
    elif conversation.state == 'selecting_doctor':
        handle_doctor_selection(conversation, message_text)
    elif conversation.state == 'selecting_date':
        handle_date_selection(conversation, message_text)
    elif conversation.state == 'selecting_time':
        handle_time_selection(conversation, message_text)
    elif conversation.state == 'collecting_patient_info':
        handle_patient_info(conversation, message_text)
    else:
        send_whatsapp_message(
            conversation.phone_number,
            "Por favor, digite 'inicio' para começar uma nova conversa."
        )


def handle_initial_state(conversation, message_text):
    """Handle initial state - show available doctors"""
    doctors = get_available_doctors()
    
    if not doctors.exists():
        send_whatsapp_message(
            conversation.phone_number,
            "❌ Desculpe, não há médicos disponíveis no momento."
        )
        return
    
    doctor_list = list(doctors)
    
    # Build message with ALL doctors
    message = "👨‍⚕️ *Agendamento de Consulta*\n\n"
    message += "Selecione um médico digitando apenas o número:\n\n"
    
    # Show ALL doctors with numbers
    for i, doctor in enumerate(doctor_list, 1):
        message += f"{i}. {doctor.full_name} - {doctor.specialization}\n"
    
    message += "\n💡 Digite apenas o número do médico desejado (ex: 1, 2, 3...)"
    
    # Send as plain text message (no buttons, just numbers)
    send_whatsapp_message(conversation.phone_number, message)
    
    conversation.state = 'selecting_doctor'
    conversation.save()


def handle_doctor_selection(conversation, message_text):
    """Handle doctor selection by number only"""
    # Try to parse as number
    try:
        doctor_num = int(message_text.strip())
        doctors = list(get_available_doctors())
        
        if 1 <= doctor_num <= len(doctors):
            doctor = doctors[doctor_num - 1]
            logger.info(f"Selected doctor {doctor_num}: {doctor.full_name} for {conversation.phone_number}")
            
            conversation.selected_doctor = doctor
            conversation.state = 'selecting_date'
            conversation.save()
            
            # Show available dates
            show_available_dates(conversation)
        else:
            send_whatsapp_message(
                conversation.phone_number,
                f"❌ Número inválido. Por favor, digite um número entre 1 e {len(doctors)}."
            )
            handle_initial_state(conversation, "")
            return
    except ValueError:
        send_whatsapp_message(
            conversation.phone_number,
            "❌ Por favor, digite apenas o número do médico desejado (ex: 1, 2, 3...)."
        )
        handle_initial_state(conversation, "")
        return
    except Exception as e:
        logger.error(f"Error in handle_doctor_selection: {e}", exc_info=True)
        send_whatsapp_message(
            conversation.phone_number,
            "❌ Erro ao processar seleção. Por favor, tente novamente."
        )
        handle_initial_state(conversation, "")
        return


def show_available_dates(conversation):
    """Show available dates for selected doctor"""
    doctor = conversation.selected_doctor
    available_dates = get_available_dates_for_week(doctor)
    
    if not available_dates:
        send_whatsapp_message(
            conversation.phone_number,
            f"❌ Não há datas disponíveis para {doctor.full_name} na próxima semana.\n\n"
            "Digite 'inicio' para escolher outro médico."
        )
        conversation.reset()
        return
    
    # Create buttons for dates (max 3)
    buttons = []
    for i, date in enumerate(available_dates[:3]):
        date_str = date.strftime('%Y-%m-%d')
        date_label = format_date_br(date)
        buttons.append({
            'id': f'date_{date_str}',
            'title': date_label[:20]
        })
    
    message = f"📅 *Datas Disponíveis*\n\n"
    message += f"Médico: {doctor.full_name}\n\n"
    message += "Selecione uma data:\n\n"
    
    for i, date in enumerate(available_dates[:3], 1):
        message += f"{i}. {format_date_br(date)}\n"
    
    if len(available_dates) > 3:
        message += "\nOu digite o número da data desejada."
    
    try:
        send_whatsapp_interactive_message(conversation.phone_number, message, buttons)
    except:
        send_whatsapp_message(conversation.phone_number, message)
    
    conversation.state = 'selecting_date'
    conversation.save()


def handle_date_selection(conversation, message_text):
    """Handle date selection"""
    # Check if it's a button click
    if message_text.startswith('date_'):
        date_str = message_text.replace('date_', '')
        selected_date = parse_date(date_str)
    else:
        # Try to parse as number
        try:
            date_num = int(message_text)
            doctor = conversation.selected_doctor
            available_dates = get_available_dates_for_week(doctor)
            
            if 1 <= date_num <= len(available_dates):
                selected_date = available_dates[date_num - 1]
            else:
                send_whatsapp_message(
                    conversation.phone_number,
                    "❌ Número inválido. Por favor, selecione uma data da lista."
                )
                show_available_dates(conversation)
                return
        except (ValueError, IndexError):
            send_whatsapp_message(
                conversation.phone_number,
                "❌ Por favor, selecione uma data usando os botões ou digite o número."
            )
            show_available_dates(conversation)
            return
    
    if not selected_date:
        send_whatsapp_message(
            conversation.phone_number,
            "❌ Data inválida. Por favor, tente novamente."
        )
        show_available_dates(conversation)
        return
    
    conversation.selected_date = selected_date
    conversation.state = 'selecting_time'
    conversation.save()
    
    # Show available times
    show_available_times(conversation)


def show_available_times(conversation):
    """Show available times for selected date"""
    doctor = conversation.selected_doctor
    date = conversation.selected_date
    available_times = get_available_times(doctor, date)
    
    if not available_times:
        send_whatsapp_message(
            conversation.phone_number,
            f"❌ Não há horários disponíveis para {format_date_br(date)}.\n\n"
            "Digite 'inicio' para escolher outra data."
        )
        conversation.state = 'selecting_date'
        conversation.selected_date = None
        conversation.save()
        show_available_dates(conversation)
        return
    
    # Build message with ALL available times
    message = f"⏰ *Horários Disponíveis*\n\n"
    message += f"Data: {format_date_br(date)}\n"
    message += f"Médico: {doctor.full_name}\n\n"
    message += "Selecione um horário digitando apenas o número:\n\n"
    
    # Show ALL available times with numbers
    for i, time_str in enumerate(available_times, 1):
        message += f"{i}. {time_str}\n"
    
    message += "\n💡 Digite apenas o número do horário desejado (ex: 1, 2, 3...)"
    
    # Send as plain text message (no buttons, just numbers)
    send_whatsapp_message(conversation.phone_number, message)


def handle_time_selection(conversation, message_text):
    """Handle time selection by number only"""
    selected_time = None
    
    # Try to parse as number
    try:
        time_num = int(message_text.strip())
        doctor = conversation.selected_doctor
        date = conversation.selected_date
        available_times = get_available_times(doctor, date)
        
        if 1 <= time_num <= len(available_times):
            time_str = available_times[time_num - 1]
            selected_time = parse_time(time_str)
            logger.info(f"Selected time {time_num}: {time_str} for {conversation.phone_number}")
        else:
            send_whatsapp_message(
                conversation.phone_number,
                f"❌ Número inválido. Por favor, digite um número entre 1 e {len(available_times)}."
            )
            show_available_times(conversation)
            return
    except ValueError:
        send_whatsapp_message(
            conversation.phone_number,
            "❌ Por favor, digite apenas o número do horário desejado (ex: 1, 2, 3...)."
        )
        show_available_times(conversation)
        return
    except Exception as e:
        logger.error(f"Error in handle_time_selection: {e}", exc_info=True)
        send_whatsapp_message(
            conversation.phone_number,
            "❌ Erro ao processar seleção. Por favor, tente novamente."
        )
        show_available_times(conversation)
        return
    
    if not selected_time:
        send_whatsapp_message(
            conversation.phone_number,
            "❌ Horário inválido. Por favor, tente novamente."
        )
        show_available_times(conversation)
        return
    
    conversation.selected_time = selected_time
    conversation.state = 'collecting_patient_info'
    conversation.save()
    
    # Ask for patient information
    send_whatsapp_message(
        conversation.phone_number,
        "📝 *Informações do Paciente*\n\n"
        "Por favor, envie o nome completo do paciente:"
    )


def handle_patient_info(conversation, message_text):
    """Handle patient information collection and create appointment"""
    if not conversation.patient_name:
        # First message is patient name
        conversation.patient_name = message_text.strip()
        conversation.save()
        
        send_whatsapp_message(
            conversation.phone_number,
            "📞 Agora, por favor, envie o telefone do paciente (com DDD):"
        )
        return
    
    # Second message is phone
    phone = message_text.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    conversation.patient_phone = phone
    conversation.save()
    
    # Create or get patient
    try:
        # Try to find existing patient by phone
        patient = Patient.objects.filter(phone__icontains=phone).first()
        
        if not patient:
            # Create new patient
            # We need a doctor to assign the patient to
            doctor = conversation.selected_doctor
            
            # Create patient with minimal required info
            patient = Patient.objects.create(
                doctor=doctor,
                first_name=conversation.patient_name.split()[0] if conversation.patient_name else "Paciente",
                last_name=' '.join(conversation.patient_name.split()[1:]) if len(conversation.patient_name.split()) > 1 else "",
                phone=phone,
                date_of_birth=timezone.now().date() - timedelta(days=365*30),  # Default age 30
                gender='O',  # Other as default
                is_active=True
            )
        
        # Create appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=conversation.selected_doctor,
            appointment_date=conversation.selected_date,
            appointment_time=conversation.selected_time,
            duration_minutes=30,
            appointment_type='consultation',
            payment_type='particular',  # Default
            status='scheduled',
            reason='Agendado via WhatsApp'
        )
        
        conversation.appointment = appointment
        conversation.state = 'completed'
        conversation.completed_at = timezone.now()
        conversation.save()
        
        # Send confirmation
        confirmation_message = "✅ *Consulta Agendada com Sucesso!*\n\n"
        confirmation_message += f"👨‍⚕️ Médico: {conversation.selected_doctor.full_name}\n"
        confirmation_message += f"👤 Paciente: {patient.full_name}\n"
        confirmation_message += f"📅 Data: {format_date_br(conversation.selected_date)}\n"
        confirmation_message += f"⏰ Horário: {conversation.selected_time.strftime('%H:%M')}\n\n"
        confirmation_message += "Obrigado por usar nosso serviço!"
        
        send_whatsapp_message(conversation.phone_number, confirmation_message)
        
    except Exception as e:
        print(f"Error creating appointment: {e}")
        import traceback
        traceback.print_exc()
        send_whatsapp_message(
            conversation.phone_number,
            f"❌ Erro ao criar agendamento: {str(e)}\n\n"
            "Por favor, tente novamente ou entre em contato com o suporte."
        )
        conversation.reset()
