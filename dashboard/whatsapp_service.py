"""
WhatsApp Business API service for handling messages and appointments
"""
import os
import requests
import json
from pathlib import Path
from datetime import datetime, timedelta, time as dt_time
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from .models import Doctor, Appointment, Patient, FAQEntry, WhatsAppConversation, AppointmentSettings

# Get BASE_DIR (go up from dashboard to project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
try:
    from decouple import config, Config, RepositoryEnv
    # Try to load .env file from project root
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        config = Config(RepositoryEnv(str(env_file)))
        WHATSAPP_TOKEN = config('WHATSAPP_TOKEN', default='')
        WHATSAPP_PHONE_NUMBER_ID = config('WHATSAPP_PHONE_NUMBER_ID', default='')
        WHATSAPP_VERIFY_TOKEN = config('WHATSAPP_VERIFY_TOKEN', default='whatsapp_verify_token_123')
    else:
        # Fallback to default config (searches for .env automatically)
        from decouple import config as default_config
        WHATSAPP_TOKEN = default_config('WHATSAPP_TOKEN', default='')
        WHATSAPP_PHONE_NUMBER_ID = default_config('WHATSAPP_PHONE_NUMBER_ID', default='')
        WHATSAPP_VERIFY_TOKEN = default_config('WHATSAPP_VERIFY_TOKEN', default='whatsapp_verify_token_123')
except ImportError:
    # Fallback to os.environ if decouple is not available
    # Try to load .env manually
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN', '')
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
    WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'whatsapp_verify_token_123')

# Mensagem personalizada da clínica enviada após "Obrigado pelo contato" ao encerrar (deixe vazia para não enviar)
WHATSAPP_CLINIC_MESSAGE = (
    "Horário: Seg a Sex 8h-18h. Entre em contato para mais informações."
)

# WhatsApp Business API base URL (will be set dynamically)
def get_whatsapp_api_url():
    """Get WhatsApp API URL with phone number ID"""
    if not WHATSAPP_PHONE_NUMBER_ID:
        # Try to extract from token or use a default
        # For now, we'll require it in the config
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID must be set in .env file")
    return f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"


def send_whatsapp_message(phone_number, message):
    """
    Send a WhatsApp message using the Meta WhatsApp Business API
    
    Args:
        phone_number: Phone number in international format (e.g., +5511999999999)
        message: Message text to send
    
    Returns:
        dict: Response from API
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise ValueError("WhatsApp token or phone number ID not configured")
    
    # Format phone number (remove + if present, WhatsApp API expects it without +)
    phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
    
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    payload = {
        'messaging_product': 'whatsapp',
        'to': phone,
        'type': 'text',
        'text': {
            'body': message
        }
    }
    
    try:
        api_url = get_whatsapp_api_url()
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def send_whatsapp_interactive_message(phone_number, message, buttons):
    """
    Send an interactive WhatsApp message with buttons
    
    Args:
        phone_number: Phone number in international format
        message: Message text
        buttons: List of button dicts with 'id' and 'title' keys
    
    Returns:
        dict: Response from API
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise ValueError("WhatsApp token or phone number ID not configured")
    
    phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
    
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    # Format buttons for WhatsApp API
    formatted_buttons = []
    for i, button in enumerate(buttons[:3]):  # WhatsApp allows max 3 buttons
        formatted_buttons.append({
            'type': 'reply',
            'reply': {
                'id': button['id'],
                'title': button['title']
            }
        })
    
    payload = {
        'messaging_product': 'whatsapp',
        'to': phone,
        'type': 'interactive',
        'interactive': {
            'type': 'button',
            'body': {
                'text': message
            },
            'action': {
                'buttons': formatted_buttons
            }
        }
    }
    
    try:
        api_url = get_whatsapp_api_url()
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp interactive message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def get_available_doctors():
    """Get all active doctors"""
    return Doctor.objects.filter(is_active=True).select_related('user').order_by('user__first_name', 'user__last_name')


def get_available_dates_for_week(doctor, start_date=None):
    """
    Get available dates for the next week for a doctor
    
    Args:
        doctor: Doctor instance
        start_date: Starting date (defaults to today)
    
    Returns:
        list: List of available dates (date objects)
    """
    if start_date is None:
        start_date = timezone.localtime(timezone.now()).date()
    
    available_dates = []
    current_date = start_date
    
    # Get dates for the next 7 days (excluding weekends)
    for i in range(14):  # Check up to 14 days to get 7 weekdays
        if current_date.weekday() < 5:  # Monday to Friday (0-4)
            # Check if there are any available time slots for this date
            if has_available_slots(doctor, current_date):
                available_dates.append(current_date)
        
        current_date += timedelta(days=1)
        
        # Stop when we have 7 weekdays
        if len(available_dates) >= 7:
            break
    
    return available_dates


def has_available_slots(doctor, date):
    """Check if a doctor has available time slots on a given date"""
    # Business hours: 8:00 to 18:00
    start_time = dt_time(8, 0)
    end_time = dt_time(18, 0)
    
    # Get existing appointments for this date
    existing_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=date
    ).exclude(status='cancelled')
    
    # Get all booked times
    booked_times = set()
    for appointment in existing_appointments:
        booked_times.add(appointment.appointment_time)
        # Also mark the end time as booked
        end_datetime = datetime.combine(date, appointment.appointment_time) + timedelta(minutes=appointment.duration_minutes)
        booked_times.add(end_datetime.time())
    
    # Check if there's at least one available slot (30-minute intervals)
    current_time = datetime.combine(date, start_time)
    end_datetime = datetime.combine(date, end_time)
    
    while current_time < end_datetime:
        time_slot = current_time.time()
        if time_slot not in booked_times:
            return True
        current_time += timedelta(minutes=30)
    
    return False


def get_available_times(doctor, date):
    """
    Get available time slots for a doctor on a specific date
    
    Args:
        doctor: Doctor instance
        date: Date object
    
    Returns:
        list: List of available time strings (HH:MM format)
    """
    # Business hours: 8:00 to 18:00
    start_time = dt_time(8, 0)
    end_time = dt_time(18, 0)
    
    # Get existing appointments for this date
    existing_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=date
    ).exclude(status='cancelled')
    
    # Get all booked time ranges
    booked_ranges = []
    for appointment in existing_appointments:
        start = appointment.appointment_time
        end_datetime = datetime.combine(date, start) + timedelta(minutes=appointment.duration_minutes)
        end = end_datetime.time()
        booked_ranges.append((start, end))
    
    # Generate available time slots (30-minute intervals)
    available_times = []
    current_time = datetime.combine(date, start_time)
    end_datetime = datetime.combine(date, end_time)
    
    while current_time < end_datetime:
        time_slot = current_time.time()
        
        # Check if this time slot conflicts with any existing appointment
        is_available = True
        for booked_start, booked_end in booked_ranges:
            if booked_start <= time_slot < booked_end:
                is_available = False
                break
        
        if is_available:
            available_times.append(time_slot.strftime('%H:%M'))
        
        current_time += timedelta(minutes=30)
    
    return available_times


def format_date_br(date):
    """Format date in Brazilian format"""
    days = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    months = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
              'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    weekday = days[date.weekday()]
    day = date.day
    month = months[date.month]
    
    return f"{weekday}, {day} de {month}"


# --- Horário comercial (para fluxo de ligação) ---
BUSINESS_HOURS_START = (8, 0)   # 08:00
BUSINESS_HOURS_END = (18, 0)    # 18:00
BUSINESS_DAYS = (0, 1, 2, 3, 4)  # Segunda a Sexta


def is_business_hours():
    """Verifica se está em horário comercial (segunda a sexta, 8h-18h)."""
    now = timezone.localtime(timezone.now())
    if now.weekday() not in BUSINESS_DAYS:
        return False
    start = dt_time(*BUSINESS_HOURS_START)
    end = dt_time(*BUSINESS_HOURS_END)
    return start <= now.time() < end


# --- Busca de profissionais e horários (para agendamento) ---

def normalize_for_search(text):
    """
    Normaliza texto para comparação: minúsculas e sem acentos.
    Usado para busca por proximidade de nome (ex: "João" encontra "joao").
    """
    if not text:
        return ""
    import unicodedata
    s = text.strip().lower()
    # NFD = decomposed form (á -> a + combining accent); remove combining chars
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def get_doctors_by_name(name):
    """
    Busca médicos ativos por proximidade do nome.
    Comparação normalizada: minúsculas e sem acentos (ex: "maria" ou "María" encontra "Maria").
    """
    if not name or not name.strip():
        return Doctor.objects.none()
    query_norm = normalize_for_search(name)
    if not query_norm:
        return Doctor.objects.none()
    doctors = list(
        Doctor.objects.filter(is_active=True)
        .select_related("user")
        .order_by("user__first_name", "user__last_name")
    )
    result = []
    for doc in doctors:
        first_norm = normalize_for_search(doc.user.first_name or "")
        last_norm = normalize_for_search(doc.user.last_name or "")
        full_norm = f"{first_norm} {last_norm}".strip()
        full_no_space = full_norm.replace(" ", "")
        # Match por proximidade: termo normalizado no nome (com ou sem acentos/maíusc.)
        if (
            query_norm in full_norm
            or query_norm in first_norm
            or query_norm in last_norm
            or (full_no_space and query_norm in full_no_space)
        ):
            result.append(doc)
    return result


def get_doctors_by_specialty(specialty):
    """Busca médicos ativos por especialidade."""
    if not specialty or not specialty.strip():
        return Doctor.objects.none()
    return Doctor.objects.filter(
        is_active=True,
        specialization__icontains=specialty.strip()
    ).select_related('user').order_by('user__first_name', 'user__last_name')


def get_next_available_slots(limit=10, start_date=None):
    """
    Retorna as próximas vagas disponíveis (qualquer médico), ordenadas por data/hora.
    Cada item: {'doctor': Doctor, 'date': date, 'time': time_str, 'date_label': str}
    """
    if start_date is None:
        start_date = timezone.localtime(timezone.now()).date()
    doctors = get_available_doctors()
    results = []
    current = start_date
    for _ in range(60):  # até 60 dias
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        for doctor in doctors:
            if has_available_slots(doctor, current):
                times = get_available_times(doctor, current)
                for t in times[:3]:
                    results.append({
                        'doctor': doctor,
                        'date': current,
                        'time': t,
                        'date_label': format_date_br(current),
                    })
                    if len(results) >= limit:
                        return results
            if len(results) >= limit:
                break
        current += timedelta(days=1)
    return results


def search_faq(query, limit=5):
    """
    Consulta a base de conhecimento por pergunta ou palavras-chave.
    Retorna lista de FAQEntry ordenados por relevância (match em question/answer/keywords).
    """
    if not query or not query.strip():
        return []
    q = query.strip().lower()
    entries = list(FAQEntry.objects.filter(is_active=True))
    scored = []
    for e in entries:
        score = 0
        if q in (e.question or '').lower():
            score += 10
        if q in (e.answer or '').lower():
            score += 5
        if e.keywords:
            for kw in e.keywords.lower().split(','):
                kw = kw.strip()
                if kw and kw in q:
                    score += 7
                if kw and q in kw:
                    score += 3
        if score > 0:
            scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:limit]]


# ========== Máquina de estados (fluxo Agendamento + FAQ + Encerramento) ==========

def _send(phone_number, text, buttons=None):
    """Envia mensagem de texto ou com botões."""
    if buttons:
        try:
            send_whatsapp_interactive_message(phone_number, text, buttons)
        except Exception:
            send_whatsapp_message(phone_number, text)
    else:
        send_whatsapp_message(phone_number, text)


def process_flow(conversation, message_text):
    """
    Processa a mensagem do usuário de acordo com o estado atual da conversa.
    Atualiza conversation (state, context, FKs) e envia as respostas pelo WhatsApp.
    Fluxo: channel_choice -> main_menu -> (schedule_* | faq_*) -> loop_desire_more -> end
    """
    phone = conversation.phone_number
    msg = (message_text or '').strip()
    msg_lower = msg.lower()

    # Comandos globais: reiniciar
    if msg_lower in ('cancelar', 'cancel', 'inicio', 'começar', 'comecar', 'start', 'menu'):
        conversation.reset()
        _send(phone, "✅ Conversa reiniciada. Como posso ajudá-lo?")
        _send_channel_choice(conversation)
        return

    state = conversation.state

    # Inicial: tratar como channel_choice (compatibilidade)
    if state == 'initial':
        _send_channel_choice(conversation)
        return

    if state == 'channel_choice':
        _handle_channel_choice(conversation, msg_lower)
        return

    if state == 'patient_cpf':
        _handle_patient_cpf(conversation, msg)
        return

    if state == 'patient_register_name':
        _handle_patient_register_name(conversation, msg)
        return

    if state == 'patient_register_phone':
        _handle_patient_register_phone(conversation, msg)
        return

    if state == 'patient_register_gender':
        _handle_patient_register_gender(conversation, msg_lower)
        return

    if state == 'patient_register_birth':
        _handle_patient_register_birth(conversation, msg)
        return

    if state == 'schedule_payment_type':
        _handle_schedule_payment_type(conversation, msg_lower)
        return

    if state == 'schedule_select_insurance':
        _handle_schedule_select_insurance(conversation, msg)
        return

    if state == 'schedule_confirm_final':
        _handle_schedule_confirm_final(conversation, msg_lower)
        return

    if state == 'consult_cpf':
        _handle_consult_cpf(conversation, msg)
        return

    if state == 'consult_list':
        _handle_consult_list(conversation, msg_lower)
        return

    if state == 'consult_cancel_select':
        _handle_consult_cancel_select(conversation, msg)
        return

    if state == 'consult_cancel_confirm':
        _handle_consult_cancel_confirm(conversation, msg_lower)
        return

    if state == 'main_menu':
        _handle_main_menu(conversation, msg_lower)
        return

    if state == 'schedule_alert':
        _handle_schedule_alert(conversation, msg_lower)
        return

    if state == 'schedule_search_type':
        _handle_schedule_search_type(conversation, msg_lower)
        return

    if state == 'schedule_search_name':
        _handle_schedule_search_name(conversation, msg)
        return

    if state == 'schedule_search_specialty':
        _handle_schedule_search_specialty(conversation, msg)
        return

    if state == 'schedule_search_date':
        _handle_schedule_search_date(conversation, msg)
        return

    if state == 'schedule_select_doctor':
        _handle_schedule_select_doctor(conversation, msg)
        return

    if state == 'schedule_select_date':
        _handle_schedule_select_date(conversation, msg)
        return

    if state == 'schedule_list':
        _handle_schedule_list(conversation, msg)
        return

    if state == 'schedule_confirm':
        _handle_schedule_confirm(conversation, msg_lower)
        return

    if state == 'schedule_collecting_patient':
        _handle_schedule_collecting_patient(conversation, msg)
        return

    if state == 'faq_question':
        _handle_faq_question(conversation, msg)
        return

    if state == 'faq_resolved':
        _handle_faq_resolved(conversation, msg_lower)
        return

    if state == 'loop_desire_more':
        _handle_loop_desire_more(conversation, msg_lower)
        return

    # Estados antigos (selecting_doctor, selecting_date, etc.): manter fluxo legado nas views
    # Se cair aqui com estado novo, voltar ao menu
    conversation.state = 'main_menu'
    conversation.save()
    _send_main_menu(conversation)


def _normalize_cpf(cpf_str):
    """Retorna apenas os 11 dígitos do CPF para comparação."""
    if not cpf_str:
        return ""
    return "".join(c for c in str(cpf_str).strip() if c.isdigit())[:11]


def _is_valid_cpf(cpf_digits):
    """
    Valida CPF pelos dígitos verificadores (algoritmo oficial brasileiro).
    cpf_digits: string com exatamente 11 dígitos.
    """
    if not cpf_digits or len(cpf_digits) != 11:
        return False
    if not cpf_digits.isdigit():
        return False
    # Rejeita sequências inválidas (todos iguais)
    if len(set(cpf_digits)) == 1:
        return False
    # Primeiro dígito verificador
    soma = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    d10 = 0 if resto < 2 else 11 - resto
    if int(cpf_digits[9]) != d10:
        return False
    # Segundo dígito verificador
    soma = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    d11 = 0 if resto < 2 else 11 - resto
    if int(cpf_digits[10]) != d11:
        return False
    return True


def _find_patient_by_cpf(cpf_normalized):
    """Busca paciente por CPF (comparação apenas com dígitos)."""
    if len(cpf_normalized) != 11:
        return None
    for p in Patient.objects.exclude(cpf__isnull=True).exclude(cpf=""):
        if _normalize_cpf(p.cpf) == cpf_normalized:
            return p
    return None


def _handle_patient_cpf(conversation, msg):
    cpf_digits = _normalize_cpf(msg)
    if len(cpf_digits) != 11:
        _send(
            conversation.phone_number,
            "CPF inválido. Envie apenas os *11 números* (ex: 12345678900)."
        )
        return
    if not _is_valid_cpf(cpf_digits):
        _send(
            conversation.phone_number,
            "CPF inválido. Verifique os números e envie novamente."
        )
        return
    patient = _find_patient_by_cpf(cpf_digits)
    if patient:
        conversation.patient = patient
        conversation.save()
        from_schedule_confirm = conversation.context.get("from_schedule_confirm", False)
        if from_schedule_confirm and conversation.selected_doctor_id:
            _send(
                conversation.phone_number,
                f"✅ *Bem-vindo de volta,* {patient.full_name}!"
            )
            conversation.state = "schedule_payment_type"
            conversation.save()
            _send_schedule_payment_type_message(conversation)
            return
        _send(conversation.phone_number, f"✅ Olá, *{patient.full_name}*!")
        conversation.state = "main_menu"
        conversation.save()
        _send_main_menu(conversation)
        return
    conversation.context["patient_cpf"] = cpf_digits
    conversation.state = "patient_register_name"
    conversation.save()
    _send(
        conversation.phone_number,
        "CPF não encontrado. Vamos cadastrá-lo.\n\n"
        "Envie seu *nome completo*:"
    )


def _handle_patient_register_name(conversation, msg):
    name = (msg or "").strip()
    if not name or len(name) < 3:
        _send(conversation.phone_number, "Por favor, envie seu nome completo (mínimo 3 caracteres).")
        return
    conversation.context["patient_name"] = name
    conversation.state = "patient_register_phone"
    conversation.save()
    _send(conversation.phone_number, "Agora envie seu *telefone* (com DDD):\nExemplo: 11999998888")


def _handle_patient_register_phone(conversation, msg):
    phone = (msg or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    phone = "".join(c for c in phone if c.isdigit())
    if len(phone) < 10:
        _send(conversation.phone_number, "Telefone inválido. Envie com DDD (ex: 11999998888).")
        return
    conversation.context["patient_phone"] = phone
    cpf_digits = conversation.context.get("patient_cpf") or ""
    if len(cpf_digits) != 11 or not _is_valid_cpf(cpf_digits):
        _send(
            conversation.phone_number,
            "O CPF informado é inválido. Inicie o agendamento novamente e envie um CPF válido."
        )
        conversation.state = "main_menu"
        conversation.context.pop("patient_cpf", None)
        conversation.context.pop("patient_name", None)
        conversation.context.pop("from_schedule_confirm", None)
        conversation.save()
        _send_main_menu(conversation)
        return
    from_schedule_confirm = conversation.context.get("from_schedule_confirm", False)
    if from_schedule_confirm:
        conversation.state = "patient_register_gender"
        conversation.save()
        _send(
            conversation.phone_number,
            "Qual seu *sexo*?\n\n1. Masculino\n2. Feminino\n3. Outro"
        )
        return
    full_name = (conversation.context.get("patient_name") or "").strip()
    parts = full_name.split(None, 1)
    first_name = parts[0] if parts else "Paciente"
    last_name = parts[1] if len(parts) > 1 else ""
    cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
    try:
        patient = Patient.objects.create(
            clinic=conversation.selected_doctor.clinic if conversation.selected_doctor else None,
            first_name=first_name,
            last_name=last_name,
            cpf=cpf_formatted or None,
            phone=phone,
            date_of_birth=timezone.now().date() - timedelta(days=365 * 30),
            gender="O",
            is_active=True,
        )
        conversation.patient = patient
        conversation.context.pop("patient_cpf", None)
        conversation.context.pop("patient_name", None)
        conversation.save()
        _send(conversation.phone_number, f"✅ Cadastro realizado! Olá, *{patient.full_name}*!")
        conversation.state = "main_menu"
        conversation.save()
        _send_main_menu(conversation)
    except Exception as e:
        _send(
            conversation.phone_number,
            f"Não foi possível concluir o cadastro. Tente novamente ou fale com o suporte."
        )


def _handle_patient_register_gender(conversation, msg_lower):
    gender_map = {
        "1": "M", "masculino": "M", "m": "M",
        "2": "F", "feminino": "F", "f": "F",
        "3": "O", "outro": "O", "o": "O",
    }
    g = gender_map.get(msg_lower.strip())
    if not g:
        _send(
            conversation.phone_number,
            "Opção inválida. Envie *1* (Masculino), *2* (Feminino) ou *3* (Outro)."
        )
        return
    conversation.context["patient_gender"] = g
    conversation.state = "patient_register_birth"
    conversation.save()
    _send(
        conversation.phone_number,
        "Qual sua *data de nascimento*?\n\n📌 Modelo: DD/MM/AAAA\nExemplo: 15/03/1990"
    )


def _handle_patient_register_birth(conversation, msg):
    date_val = _parse_user_date(msg)
    if not date_val:
        _send(
            conversation.phone_number,
            "Data inválida. Use o modelo *DD/MM/AAAA* (ex: 15/03/1990)."
        )
        return
    today = timezone.localtime(timezone.now()).date()
    if date_val > today:
        _send(conversation.phone_number, "A data de nascimento não pode ser no futuro.")
        return
    conversation.context["patient_birth"] = date_val.isoformat()
    conversation.state = "schedule_payment_type"
    conversation.save()
    _send_schedule_payment_type_message(conversation)


def _get_particular_price_str():
    """Retorna o valor da consulta particular formatado (ex: R$ 150,00)."""
    p = _get_particular_price_decimal()
    if p is not None:
        return f"R$ {p:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ 150,00"


def _get_particular_price_decimal():
    """Retorna o valor decimal da consulta particular ou None."""
    try:
        s = AppointmentSettings.get_settings()
        price = getattr(s, "default_particular_price", None)
        if price is not None and str(price).strip():
            try:
                from decimal import Decimal
                return Decimal(str(price).replace(",", "."))
            except (ValueError, TypeError, Exception):
                pass
    except Exception:
        pass
    try:
        from decimal import Decimal
        return Decimal("150.00")
    except Exception:
        return None


def _get_appointment_payment_info(conversation):
    """Retorna (payment_type, insurance_operator, value) para criar o Appointment."""
    from decimal import Decimal
    payment_type = conversation.context.get("payment_type") or "particular"
    insurance_operator = conversation.context.get("insurance_operator") or None
    value = None
    if payment_type == "particular":
        value = _get_particular_price_decimal()
    else:
        try:
            s = AppointmentSettings.get_settings()
            prices = s.convenio_prices or {}
            price_str = prices.get(insurance_operator or "", "0")
            value = Decimal(str(price_str).replace(",", "."))
        except Exception:
            value = None
    return payment_type, insurance_operator, value


def _send_schedule_payment_type_message(conversation):
    """Pergunta se é particular ou por seguro."""
    _send(
        conversation.phone_number,
        "A consulta é *particular* ou *por seguro*?",
        [
            {"id": "pag_particular", "title": "Particular"},
            {"id": "pag_seguro", "title": "Por seguro"},
        ]
    )


def _handle_schedule_payment_type(conversation, msg_lower):
    if msg_lower in ("pag_particular", "particular", "1"):
        conversation.context["payment_type"] = "particular"
        conversation.context.pop("insurance_operator", None)
        conversation.state = "schedule_confirm_final"
        conversation.save()
        _send_schedule_confirm_final_message(conversation)
        return
    if msg_lower in ("pag_seguro", "seguro", "2"):
        conversation.state = "schedule_select_insurance"
        conversation.context.pop("insurance_not_listed", None)
        conversation.save()
        _send_schedule_select_insurance_message(conversation)
        return
    _send(
        conversation.phone_number,
        "Escolha: *1* – Particular ou *2* – Por seguro."
    )


def _send_schedule_select_insurance_message(conversation, from_not_listed=False):
    """Lista convênios cadastrados + última opção 'Meu seguro não aparece'."""
    try:
        settings = AppointmentSettings.get_settings()
        operators = list(settings.insurance_operators or [])
    except Exception:
        operators = []
    if not from_not_listed:
        conversation.context.pop("insurance_not_listed", None)
    lines = ["📋 *Convênios/seguros aceitos:*\n\nDigite o *número* do seu convênio:\n"]
    for i, op in enumerate(operators, 1):
        lines.append(f"{i}. {op}")
    n = len(operators) + 1
    lines.append(f"{n}. Meu seguro não aparece")
    lines.append("\n💡 Digite o número da sua opção.")
    _send(conversation.phone_number, "\n".join(lines))


def _handle_schedule_select_insurance(conversation, msg):
    msg_lower = (msg or "").strip().lower()
    if conversation.context.get("insurance_not_listed"):
        _handle_schedule_select_insurance_after_not_listed(conversation, msg_lower)
        return
    try:
        settings = AppointmentSettings.get_settings()
        operators = list(settings.insurance_operators or [])
    except Exception:
        operators = []
    n_total = len(operators) + 1
    try:
        num = int((msg or "").strip())
    except (ValueError, TypeError):
        _send(conversation.phone_number, f"Digite um número de 1 a {n_total}.")
        return
    if num < 1 or num > n_total:
        _send(conversation.phone_number, f"Digite um número de 1 a {n_total}.")
        return
    if num == n_total:
        conversation.context["insurance_not_listed"] = True
        conversation.save()
        _send(
            conversation.phone_number,
            "Infelizmente *não aceitamos* esse convênio no momento.\n\n"
            "Deseja *escolher outro convênio* ou *particular*?"
        )
        _send(
            conversation.phone_number,
            "Escolha:",
            [
                {"id": "outro_conv", "title": "1. Outro convênio"},
                {"id": "fazer_particular", "title": "2. Particular"},
            ]
        )
        return
    if conversation.context.pop("insurance_not_listed", None):
        pass
    selected = operators[num - 1]
    conversation.context["payment_type"] = "convenio"
    conversation.context["insurance_operator"] = selected
    conversation.state = "schedule_confirm_final"
    conversation.save()
    _send_schedule_confirm_final_message(conversation)


def _handle_schedule_select_insurance_after_not_listed(conversation, msg_lower):
    """Quando o usuário escolheu 'Meu seguro não aparece' e agora escolhe 1 ou 2."""
    if msg_lower in ("outro_conv", "1", "outro"):
        conversation.context.pop("insurance_not_listed", None)
        conversation.save()
        _send_schedule_select_insurance_message(conversation)
        return
    if msg_lower in ("fazer_particular", "2", "particular"):
        conversation.context["payment_type"] = "particular"
        conversation.context.pop("insurance_operator", None)
        conversation.context.pop("insurance_not_listed", None)
        conversation.state = "schedule_confirm_final"
        conversation.save()
        _send_schedule_confirm_final_message(conversation)
        return
    _send(conversation.phone_number, "Escolha *1* (Outro convênio) ou *2* (Particular).")


def _send_schedule_confirm_final_message(conversation):
    """Envia resumo do agendamento (com tipo de pagamento e preço se particular) e pergunta se confirma."""
    doc = conversation.selected_doctor
    date_label = format_date_br(conversation.selected_date) if conversation.selected_date else ""
    time_str = conversation.selected_time.strftime("%H:%M") if conversation.selected_time else ""
    if conversation.patient_id:
        name = conversation.patient.full_name
    else:
        name = conversation.context.get("patient_name", "Paciente")
    payment_type = conversation.context.get("payment_type", "particular")
    insurance_operator = conversation.context.get("insurance_operator", "")
    body = (
        f"✅ *Resumo do agendamento*\n\n"
        f"Profissional: {doc.full_name if doc else ''}\n"
        f"Paciente: {name}\n"
        f"Data: {date_label}\n"
        f"Horário: {time_str}\n"
    )
    if payment_type == "particular":
        body += f"\nForma: *Particular*\n"
        body += f"Valor: *{_get_particular_price_str()}*\n"
    else:
        body += f"\nForma: *Convênio/Seguro*\n"
        body += f"Convênio: *{insurance_operator}*\n"
    body += "\nConfirma o agendamento? (Sim / Não)"
    _send(conversation.phone_number, body)
    _send(
        conversation.phone_number,
        "Confirma?",
        [{"id": "conf_final_sim", "title": "Sim"}, {"id": "conf_final_nao", "title": "Não"}]
    )


def _handle_schedule_confirm_final(conversation, msg_lower):
    if msg_lower in ("conf_final_sim", "sim", "1"):
        if conversation.patient_id:
            try:
                patient = conversation.patient
                pay_type, ins_op, val = _get_appointment_payment_info(conversation)
                apt = Appointment.objects.create(
                    patient=patient,
                    doctor=conversation.selected_doctor,
                    appointment_date=conversation.selected_date,
                    appointment_time=conversation.selected_time,
                    duration_minutes=30,
                    appointment_type="consultation",
                    payment_type=pay_type,
                    insurance_operator=ins_op or None,
                    value=val,
                    status="scheduled",
                    reason="Agendado via WhatsApp",
                )
                conversation.appointment = apt
                conversation.state = "loop_desire_more"
                conversation.completed_at = timezone.now()
                for k in ("from_schedule_confirm", "payment_type", "insurance_operator"):
                    conversation.context.pop(k, None)
                conversation.save()
                _send(
                    conversation.phone_number,
                    f"✅ *Agendamento realizado com sucesso!*\n\n"
                    f"Profissional: {conversation.selected_doctor.full_name}\n"
                    f"Paciente: {patient.full_name}\n"
                    f"Data: {format_date_br(conversation.selected_date)}\n"
                    f"Horário: {conversation.selected_time.strftime('%H:%M')}\n\n"
                    "Obrigado!"
                )
                _send_loop_desire_more(conversation)
                return
            except Exception as e:
                _send(
                    conversation.phone_number,
                    f"❌ Erro ao registrar agendamento: {str(e)}. Tente novamente."
                )
                return
        if conversation.context.get("patient_name") and conversation.selected_doctor_id:
            full_name = (conversation.context.get("patient_name") or "").strip()
            parts = full_name.split(None, 1)
            first_name = parts[0] if parts else "Paciente"
            last_name = parts[1] if len(parts) > 1 else ""
            cpf_digits = conversation.context.get("patient_cpf") or ""
            cpf_formatted = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}" if len(cpf_digits) == 11 else ""
            phone = conversation.context.get("patient_phone") or ""
            gender = conversation.context.get("patient_gender") or "O"
            birth_str = conversation.context.get("patient_birth") or ""
            try:
                birth_date = datetime.strptime(birth_str, "%Y-%m-%d").date() if birth_str else (timezone.now().date() - timedelta(days=365 * 30))
            except (ValueError, TypeError):
                birth_date = timezone.now().date() - timedelta(days=365 * 30)
            try:
                patient = Patient.objects.create(
                    clinic=conversation.selected_doctor.clinic if conversation.selected_doctor else None,
                    first_name=first_name,
                    last_name=last_name,
                    cpf=cpf_formatted or None,
                    phone=phone,
                    date_of_birth=birth_date,
                    gender=gender,
                    is_active=True,
                )
                pay_type, ins_op, val = _get_appointment_payment_info(conversation)
                apt = Appointment.objects.create(
                    patient=patient,
                    doctor=conversation.selected_doctor,
                    appointment_date=conversation.selected_date,
                    appointment_time=conversation.selected_time,
                    duration_minutes=30,
                    appointment_type="consultation",
                    payment_type=pay_type,
                    insurance_operator=ins_op or None,
                    value=val,
                    status="scheduled",
                    reason="Agendado via WhatsApp",
                )
                conversation.patient = patient
                conversation.appointment = apt
                conversation.state = "loop_desire_more"
                conversation.completed_at = timezone.now()
                for k in ("patient_cpf", "patient_name", "patient_phone", "patient_gender", "patient_birth", "from_schedule_confirm", "payment_type", "insurance_operator"):
                    conversation.context.pop(k, None)
                conversation.save()
                _send(
                    conversation.phone_number,
                    f"✅ *Cadastro e agendamento realizados!*\n\n"
                    f"Você foi cadastrado para *{conversation.selected_doctor.full_name}*.\n\n"
                    f"Data: {format_date_br(conversation.selected_date)}\n"
                    f"Horário: {conversation.selected_time.strftime('%H:%M')}\n\n"
                    "Obrigado!"
                )
                _send_loop_desire_more(conversation)
                return
            except Exception as e:
                _send(
                    conversation.phone_number,
                    f"❌ Erro ao cadastrar/agendar: {str(e)}. Tente novamente."
                )
                return
        _send(conversation.phone_number, "Dados incompletos. Inicie o agendamento novamente.")
        conversation.state = "main_menu"
        conversation.save()
        _send_main_menu(conversation)
        return
    if msg_lower in ("conf_final_nao", "não", "nao", "2"):
        conversation.state = "schedule_search_type"
        conversation.context = {}
        conversation.selected_doctor = None
        conversation.selected_date = None
        conversation.selected_time = None
        conversation.patient = None
        conversation.appointment = None
        conversation.save()
        _send(conversation.phone_number, "Agendamento cancelado.")
        _send_schedule_search_options(conversation)
        return
    _send(conversation.phone_number, "Responda *Sim* ou *Não* para confirmar o agendamento.")


def _send_channel_choice(conversation):
    conversation.state = 'channel_choice'
    conversation.save()
    _send(
        conversation.phone_number,
        "Olá! Como deseja falar conosco?",
        [
            {'id': 'canal_texto', 'title': '💬 Texto (Chat)'},
            {'id': 'canal_ligacao', 'title': '📞 Ligação'},
        ]
    )


def _handle_channel_choice(conversation, msg_lower):
    if msg_lower in ('canal_texto', 'texto', 'chat', '1'):
        conversation.state = 'main_menu'
        conversation.save()
        _send_main_menu(conversation)
        return
    if msg_lower in ('canal_ligacao', 'ligação', 'ligacao', 'ligar', '2'):
        if is_business_hours():
            _send(
                conversation.phone_number,
                "No momento estamos ocupados. Por favor, tente novamente em alguns minutos ou use o *chat* para agendar."
            )
        else:
            _send(
                conversation.phone_number,
                "Estamos *fora do horário comercial* (Segunda a Sexta, 8h às 18h). Use o *chat* para agendar ou deixe seu recado."
            )
        conversation.state = 'loop_desire_more'
        conversation.context = {}
        conversation.save()
        _send_loop_desire_more(conversation)
        return
    _send_channel_choice(conversation)


def _send_main_menu(conversation):
    # Títulos com até 20 caracteres (limite da API WhatsApp) para os 3 botões aparecerem
    _send(
        conversation.phone_number,
        "📋 *Menu Principal*\n\nEscolha uma opção:\n\n1️⃣ Fazer Agendamento\n2️⃣ Consultar/Desmarcar\n3️⃣ Tirar Dúvidas\n\nOu digite *4* para Outros/Encerrar.",
        [
            {'id': 'menu_agendamento', 'title': '1. Agendamento'},
            {'id': 'menu_consultar', 'title': '2. Ver/Desmarcar'},
            {'id': 'menu_duvidas', 'title': '3. Dúvidas'},
        ]
    )


def _handle_main_menu(conversation, msg_lower):
    if msg_lower in ('menu_agendamento', 'agendamento', 'agendar', '1'):
        conversation.state = 'schedule_search_type'
        conversation.context = {}
        conversation.save()
        _send_schedule_search_options(conversation)
        return
    if msg_lower in ('menu_consultar', 'consultar', 'desmarcar', '2'):
        conversation.state = 'consult_cpf'
        conversation.context = {}
        conversation.save()
        _send(
            conversation.phone_number,
            "📋 *Consultar ou desmarcar agendamentos*\n\n"
            "Envie seu *CPF* (apenas números, 11 dígitos):\n"
            "Exemplo: 12345678900"
        )
        return
    if msg_lower in ('menu_duvidas', 'dúvidas', 'duvidas', 'faq', '3'):
        conversation.state = 'faq_question'
        conversation.context = {}
        conversation.save()
        _send(
            conversation.phone_number,
            "❓ *Tirar Dúvidas*\n\nDigite sua pergunta ou palavras-chave para buscar na base de conhecimento:"
        )
        return
    if msg_lower in ('menu_outros', 'outros', 'encerrar', '4'):
        conversation.state = 'loop_desire_more'
        conversation.save()
        _send_loop_desire_more(conversation)
        return
    _send_main_menu(conversation)


def _get_future_appointments_for_patient(patient):
    """Retorna agendamentos do paciente (não cancelados, data >= hoje) ordenados por data/hora."""
    today = timezone.localtime(timezone.now()).date()
    return (
        Appointment.objects.filter(patient=patient)
        .exclude(status="cancelled")
        .filter(appointment_date__gte=today)
        .select_related("doctor")
        .order_by("appointment_date", "appointment_time")
    )


def _handle_consult_cpf(conversation, msg):
    cpf_digits = _normalize_cpf(msg)
    if len(cpf_digits) != 11:
        _send(
            conversation.phone_number,
            "CPF inválido. Envie apenas os *11 números* (ex: 12345678900)."
        )
        return
    if not _is_valid_cpf(cpf_digits):
        _send(
            conversation.phone_number,
            "CPF inválido. Verifique os números e envie novamente."
        )
        return
    patient = _find_patient_by_cpf(cpf_digits)
    if not patient:
        _send(
            conversation.phone_number,
            "CPF não encontrado. Verifique o número ou faça um agendamento primeiro."
        )
        return
    appointments = list(_get_future_appointments_for_patient(patient))
    conversation.context["consult_patient_id"] = patient.id
    conversation.context["consult_appointment_ids"] = [a.id for a in appointments]
    conversation.state = "consult_list"
    conversation.save()
    if not appointments:
        _send(
            conversation.phone_number,
            f"Olá, *{patient.full_name}*!\n\nVocê *não tem agendamentos* no momento."
        )
        _send(
            conversation.phone_number,
            "O que deseja fazer?",
            [{"id": "consult_inicio", "title": "Início"}]
        )
        return
    lines = [f"📋 *Seus agendamentos* – Olá, *{patient.full_name}*!\n"]
    for a in appointments:
        lines.append(f"• {format_date_br(a.appointment_date)} às {a.appointment_time.strftime('%H:%M')} – {a.doctor.full_name}")
    _send(conversation.phone_number, "\n".join(lines))
    _send(
        conversation.phone_number,
        "O que deseja fazer?",
        [
            {"id": "consult_inicio", "title": "Início"},
            {"id": "consult_desmarcar", "title": "Desmarcar"},
        ]
    )


def _handle_consult_list(conversation, msg_lower):
    if msg_lower in ("consult_inicio", "inicio", "início", "1"):
        conversation.state = "main_menu"
        conversation.context.pop("consult_patient_id", None)
        conversation.context.pop("consult_appointment_ids", None)
        conversation.save()
        _send_main_menu(conversation)
        return
    if msg_lower in ("consult_desmarcar", "desmarcar", "2"):
        appointment_ids = conversation.context.get("consult_appointment_ids") or []
        if not appointment_ids:
            _send(conversation.phone_number, "Não há agendamentos para desmarcar.")
            conversation.state = "main_menu"
            conversation.save()
            _send_main_menu(conversation)
            return
        conversation.state = "consult_cancel_select"
        conversation.save()
        appointments = list(
            Appointment.objects.filter(id__in=appointment_ids)
            .select_related("doctor")
            .order_by("appointment_date", "appointment_time")
        )
        lines = ["📋 *Desmarcar agendamento*\n\nDigite o *número* do agendamento que deseja desmarcar:\n"]
        for i, a in enumerate(appointments, 1):
            lines.append(f"{i}. {format_date_br(a.appointment_date)} às {a.appointment_time.strftime('%H:%M')} – {a.doctor.full_name}")
        _send(conversation.phone_number, "\n".join(lines))
        return
    _send(
        conversation.phone_number,
        "Escolha *Início* ou *Desmarcar*."
    )


def _handle_consult_cancel_select(conversation, msg):
    appointment_ids = conversation.context.get("consult_appointment_ids") or []
    try:
        num = int((msg or "").strip())
    except (ValueError, TypeError):
        _send(conversation.phone_number, f"Digite o número do agendamento (1 a {len(appointment_ids)}).")
        return
    if num < 1 or num > len(appointment_ids):
        _send(conversation.phone_number, f"Digite um número de 1 a {len(appointment_ids)}.")
        return
    apt_id = appointment_ids[num - 1]
    apt = Appointment.objects.filter(id=apt_id).select_related("doctor").first()
    if not apt:
        _send(conversation.phone_number, "Agendamento não encontrado.")
        conversation.state = "main_menu"
        conversation.save()
        _send_main_menu(conversation)
        return
    conversation.context["consult_cancel_appointment_id"] = apt.id
    conversation.state = "consult_cancel_confirm"
    conversation.save()
    _send(
        conversation.phone_number,
        f"Confirma o *desmarque* do agendamento?\n\n"
        f"📅 {format_date_br(apt.appointment_date)} às {apt.appointment_time.strftime('%H:%M')}\n"
        f"👨‍⚕️ {apt.doctor.full_name}"
    )
    _send(
        conversation.phone_number,
        "Confirma?",
        [{"id": "desmarcar_sim", "title": "Sim"}, {"id": "desmarcar_nao", "title": "Não"}]
    )


def _handle_consult_cancel_confirm(conversation, msg_lower):
    if msg_lower in ("desmarcar_sim", "sim", "1"):
        apt_id = conversation.context.pop("consult_cancel_appointment_id", None)
        if apt_id:
            apt = Appointment.objects.filter(id=apt_id).first()
            if apt:
                apt.status = "cancelled"
                apt.save()
                _send(
                    conversation.phone_number,
                    "✅ *Agendamento desmarcado com sucesso.*"
                )
        conversation.state = "loop_desire_more"
        conversation.context.pop("consult_patient_id", None)
        conversation.context.pop("consult_appointment_ids", None)
        conversation.save()
        _send_loop_desire_more(conversation)
        return
    if msg_lower in ("desmarcar_nao", "não", "nao", "2"):
        conversation.context.pop("consult_cancel_appointment_id", None)
        conversation.state = "consult_list"
        conversation.save()
        patient_id = conversation.context.get("consult_patient_id")
        if patient_id:
            patient = Patient.objects.filter(id=patient_id).first()
            if patient:
                appointments = list(_get_future_appointments_for_patient(patient))
                conversation.context["consult_appointment_ids"] = [a.id for a in appointments]
                conversation.save()
                if appointments:
                    lines = ["📋 *Seus agendamentos*\n"]
                    for a in appointments:
                        lines.append(f"• {format_date_br(a.appointment_date)} às {a.appointment_time.strftime('%H:%M')} – {a.doctor.full_name}")
                    _send(conversation.phone_number, "\n".join(lines))
                    _send(
                        conversation.phone_number,
                        "O que deseja fazer?",
                        [{"id": "consult_inicio", "title": "Início"}, {"id": "consult_desmarcar", "title": "Desmarcar"}]
                    )
                    return
        conversation.state = "main_menu"
        conversation.save()
        _send_main_menu(conversation)
        return
    _send(conversation.phone_number, "Responda *Sim* ou *Não* para confirmar o desmarque.")


def _send_schedule_search_options(conversation):
    """Envia as opções de busca do agendamento: Nome, Especialidade ou Data (em texto e botões)."""
    body = (
        "📅 *Como deseja buscar o médico/serviço?*\n\n"
        "Escolha uma opção (pode digitar o número ou tocar no botão):\n\n"
        "1️⃣ *Por Nome do Profissional* – busque pelo nome do médico\n"
        "2️⃣ *Por Especialidade* – ex: Cardiologia, Clínico Geral\n"
        "3️⃣ *Por Data / Próxima vaga* – informe uma data ou peça a próxima disponível"
    )
    buttons = [
        {'id': 'busca_nome', 'title': '1. Nome'},
        {'id': 'busca_especialidade', 'title': '2. Especialidade'},
        {'id': 'busca_data', 'title': '3. Data / Próxima'},
    ]
    _send(conversation.phone_number, body, buttons)


def _handle_schedule_alert(conversation, msg_lower):
    if msg_lower in ('lgpd_sim', 'sim', 'continuar', '1'):
        conversation.state = 'schedule_search_type'
        conversation.context = {}
        conversation.save()
        _send_schedule_search_options(conversation)
        return
    if msg_lower in ('lgpd_nao', 'não', 'nao', '2'):
        conversation.state = 'main_menu'
        conversation.save()
        _send(conversation.phone_number, "Ok. Voltando ao menu.")
        _send_main_menu(conversation)
        return
    _send(conversation.phone_number, "Por favor, responda *Sim* para continuar ou *Não* para voltar ao menu.")


def _handle_schedule_search_type(conversation, msg_lower):
    if msg_lower in ('busca_nome', 'nome', '1'):
        conversation.state = 'schedule_search_name'
        conversation.context = {'search_type': 'name'}
        conversation.save()
        _send(conversation.phone_number, "Digite o *nome do profissional* que deseja:")
        return
    if msg_lower in ('busca_especialidade', 'especialidade', '2'):
        conversation.state = 'schedule_search_specialty'
        conversation.context = {'search_type': 'specialty'}
        conversation.save()
        _send(conversation.phone_number, "Digite a *especialidade* desejada (ex: Cardiologia, Clínico Geral):")
        return
    if msg_lower in ('busca_data', 'data', 'próxima', 'proxima', '3'):
        conversation.state = 'schedule_search_date'
        conversation.context = {'search_type': 'date'}
        conversation.save()
        _send(
            conversation.phone_number,
            "Digite uma *data* (ex: 15/03/2026) ou escreva *próxima* para a primeira vaga disponível:"
        )
        return
    _send_schedule_search_options(conversation)


def _handle_schedule_search_name(conversation, msg):
    doctors = list(get_doctors_by_name(msg))
    if not doctors:
        _send(
            conversation.phone_number,
            "Nenhum profissional encontrado com esse nome. Tente outro nome ou escolha buscar por especialidade."
        )
        return
    # Guardar lista de médicos no contexto e mostrar opções numeradas
    doctor_list = [
        {
            "doctor_id": d.id,
            "doctor_name": d.full_name,
            "specialization": getattr(d, "specialization", "") or "",
            "doctor": d,
        }
        for d in doctors[:15]
    ]
    conversation.context["doctor_list"] = [
        {"doctor_id": d["doctor_id"], "doctor_name": d["doctor_name"], "specialization": d["specialization"]}
        for d in doctor_list
    ]
    conversation.state = "schedule_select_doctor"
    conversation.save()
    # Montar mensagem com lista numerada (sem o objeto Doctor no dict para serialização)
    lines = [
        "👨‍⚕️ *Profissionais encontrados:*\n\nDigite o *número* do profissional desejado:\n"
    ]
    for i, doc in enumerate(doctor_list, 1):
        spec = doc["specialization"]
        name = doc["doctor_name"]
        if spec:
            lines.append(f"{i}. {name} – {spec}")
        else:
            lines.append(f"{i}. {name}")
    lines.append("\n💡 Exemplo: digite *1* para o primeiro da lista.")
    _send(conversation.phone_number, "\n".join(lines))


def _handle_schedule_search_specialty(conversation, msg):
    doctors = list(get_doctors_by_specialty(msg))
    if not doctors:
        _send(
            conversation.phone_number,
            "Nenhum profissional encontrado para essa especialidade. Tente outro termo."
        )
        return
    doctor_list = [
        {
            "doctor_id": d.id,
            "doctor_name": d.full_name,
            "specialization": getattr(d, "specialization", "") or "",
        }
        for d in doctors[:15]
    ]
    conversation.context["doctor_list"] = doctor_list
    conversation.state = "schedule_select_doctor"
    conversation.save()
    lines = [
        "👨‍⚕️ *Profissionais encontrados:*\n\nDigite o *número* do profissional desejado:\n"
    ]
    for i, doc in enumerate(doctor_list, 1):
        spec = doc["specialization"]
        name = doc["doctor_name"]
        if spec:
            lines.append(f"{i}. {name} – {spec}")
        else:
            lines.append(f"{i}. {name}")
    lines.append("\n💡 Exemplo: digite *1* para o primeiro da lista.")
    _send(conversation.phone_number, "\n".join(lines))


def _handle_schedule_select_doctor(conversation, msg):
    """Paciente digitou o número do profissional; buscar horários desse médico e mostrar lista."""
    doctor_list = conversation.context.get("doctor_list") or []
    if not doctor_list:
        conversation.state = "schedule_search_type"
        conversation.save()
        _send_schedule_search_options(conversation)
        return
    try:
        num = int(msg.strip())
    except (ValueError, TypeError):
        _send(
            conversation.phone_number,
            f"Digite apenas o *número* do profissional (1 a {len(doctor_list)})."
        )
        return
    if num < 1 or num > len(doctor_list):
        _send(
            conversation.phone_number,
            f"Número inválido. Digite um número entre 1 e {len(doctor_list)}."
        )
        return
    chosen = doctor_list[num - 1]
    doctor_id = chosen["doctor_id"]
    doctor = Doctor.objects.filter(id=doctor_id, is_active=True).select_related("user").first()
    if not doctor:
        _send(conversation.phone_number, "Profissional não encontrado. Tente outra busca.")
        conversation.state = "schedule_search_type"
        conversation.save()
        _send_schedule_search_options(conversation)
        return
    conversation.context["selected_doctor_id"] = doctor.id
    conversation.context["selected_doctor_name"] = doctor.full_name
    conversation.state = "schedule_select_date"
    conversation.save()
    _send(
        conversation.phone_number,
        f"📅 Você escolheu *{doctor.full_name}*.\n\n"
        "Informe a *melhor data* para sua consulta.\n\n"
        "📌 *Modelo:* 15/03/2026 ou 15-03-2026\n"
        "(dia/mês/ano)"
    )


def _parse_user_date(msg):
    """Tenta interpretar a mensagem como data. Retorna date ou None."""
    msg = (msg or "").strip().replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(msg, fmt).date()
        except ValueError:
            continue
    return None


def _handle_schedule_select_date(conversation, msg):
    """Usuário informou a data desejada; buscar horários desse médico naqueles dias."""
    doctor_id = conversation.context.get("selected_doctor_id")
    doctor_name = conversation.context.get("selected_doctor_name", "o profissional")
    if not doctor_id:
        conversation.state = "schedule_search_type"
        conversation.save()
        _send_schedule_search_options(conversation)
        return
    doctor = Doctor.objects.filter(id=doctor_id, is_active=True).select_related("user").first()
    if not doctor:
        _send(conversation.phone_number, "Profissional não encontrado. Tente novamente.")
        conversation.state = "schedule_search_type"
        conversation.save()
        _send_schedule_search_options(conversation)
        return
    date_val = _parse_user_date(msg)
    if not date_val:
        _send(
            conversation.phone_number,
            "Data inválida. Use o modelo: *DD/MM/AAAA* (ex: 15/03/2026 ou 15-03-2026)."
        )
        return
    today = timezone.localtime(timezone.now()).date()
    if date_val < today:
        _send(
            conversation.phone_number,
            "Essa data já passou. Informe uma data a partir de hoje."
        )
        return
    times = get_available_times(doctor, date_val)
    if not times:
        _send(
            conversation.phone_number,
            f"Não há horários disponíveis para *{doctor.full_name}* em {format_date_br(date_val)}. "
            "Informe outra data (ex: 20/03/2026)."
        )
        return
    slots = [
        {
            "doctor_id": doctor.id,
            "doctor_name": doctor.full_name,
            "date": date_val.isoformat(),
            "time": t,
            "date_label": format_date_br(date_val),
        }
        for t in times
    ]
    conversation.context["search_results"] = slots
    conversation.state = "schedule_list"
    conversation.save()
    _send_schedule_list(conversation)


def _handle_schedule_search_date(conversation, msg):
    if msg.lower() in ('próxima', 'proxima', 'proximo'):
        slots = get_next_available_slots(limit=10)
    else:
        # Tentar parsear data (dd/mm/yyyy ou yyyy-mm-dd)
        from django.utils.dateparse import parse_date
        date_val = None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y'):
            try:
                date_val = datetime.strptime(msg.strip(), fmt).date()
                break
            except ValueError:
                pass
        if not date_val:
            _send(
                conversation.phone_number,
                "Data inválida. Use o formato DD/MM/AAAA ou escreva *próxima* para a primeira vaga."
            )
            return
        slots = []
        for item in get_next_available_slots(limit=20):
            if item['date'] == date_val:
                slots.append({
                    'doctor_id': item['doctor'].id,
                    'doctor_name': item['doctor'].full_name,
                    'date': item['date'].isoformat(),
                    'time': item['time'],
                    'date_label': item['date_label'],
                })
    if not slots:
        _send(
            conversation.phone_number,
            "Nenhuma vaga encontrada para a data informada. Tente *próxima* ou outra data."
        )
        return
    conversation.context['search_results'] = slots[:10]
    conversation.state = 'schedule_list'
    conversation.save()
    _send_schedule_list(conversation)


def _send_schedule_list(conversation):
    results = conversation.context.get('search_results', [])
    lines = ["📅 *Horários disponíveis*\n\nSelecione pelo *número*:\n"]
    for i, s in enumerate(results, 1):
        lines.append(f"{i}. {s['doctor_name']} - {s['date_label']} às {s['time']}")
    _send(conversation.phone_number, "\n".join(lines))


def _handle_schedule_list(conversation, msg):
    results = conversation.context.get('search_results', [])
    try:
        num = int(msg.strip())
        if 1 <= num <= len(results):
            slot = results[num - 1]
            conversation.context['selected_slot'] = slot
            conversation.selected_doctor_id = slot['doctor_id']
            conversation.selected_date = datetime.strptime(slot['date'], '%Y-%m-%d').date()
            conversation.selected_time = datetime.strptime(slot['time'], '%H:%M').time()
            conversation.state = 'patient_cpf'
            conversation.context['from_schedule_confirm'] = True
            conversation.save()
            _send(
                conversation.phone_number,
                "⚠️ *LGPD – Proteção de Dados*\n\n"
                "Seus dados serão usados apenas para identificação e agendamento. "
                "Ao enviar seu CPF, você concorda com o uso conforme nossa política de privacidade.\n\n"
                "📌 Envie seu *CPF* (apenas números, 11 dígitos):\n"
                "Exemplo: 12345678900"
            )
            return
    except (ValueError, IndexError, KeyError):
        pass
    _send(
        conversation.phone_number,
        f"Por favor, digite um número entre 1 e {len(results)}."
    )


def _handle_schedule_confirm(conversation, msg_lower):
    if msg_lower in ('conf_sim', 'sim', '1'):
        if conversation.patient_id:
            try:
                patient = conversation.patient
                apt = Appointment.objects.create(
                    patient=patient,
                    doctor=conversation.selected_doctor,
                    appointment_date=conversation.selected_date,
                    appointment_time=conversation.selected_time,
                    duration_minutes=30,
                    appointment_type='consultation',
                    payment_type='particular',
                    status='scheduled',
                    reason='Agendado via WhatsApp',
                )
                conversation.appointment = apt
                conversation.state = 'loop_desire_more'
                conversation.completed_at = timezone.now()
                conversation.save()
                _send(
                    conversation.phone_number,
                    f"✅ *Agendamento realizado com sucesso!*\n\n"
                    f"Profissional: {conversation.selected_doctor.full_name}\n"
                    f"Paciente: {patient.full_name}\n"
                    f"Data: {format_date_br(conversation.selected_date)}\n"
                    f"Horário: {conversation.selected_time.strftime('%H:%M')}\n\n"
                    "Obrigado!"
                )
                _send_loop_desire_more(conversation)
                return
            except Exception as e:
                _send(
                    conversation.phone_number,
                    f"❌ Erro ao registrar agendamento: {str(e)}. Tente novamente."
                )
                return
        # Identificação/cadastro só depois de confirmar o horário: LGPD + CPF
        conversation.state = 'patient_cpf'
        conversation.context['from_schedule_confirm'] = True
        conversation.save()
        _send(
            conversation.phone_number,
            "⚠️ *LGPD – Proteção de Dados*\n\n"
            "Seus dados serão usados apenas para identificação e agendamento. "
            "Ao enviar seu CPF, você concorda com o uso conforme nossa política de privacidade.\n\n"
            "📌 Envie seu *CPF* (apenas números, 11 dígitos):\n"
            "Exemplo: 12345678900"
        )
        return
    if msg_lower in ('conf_nao', 'não', 'nao', '2'):
        conversation.state = 'schedule_search_type'
        conversation.context = {}
        conversation.selected_doctor = None
        conversation.selected_date = None
        conversation.selected_time = None
        conversation.save()
        _send(conversation.phone_number, "Agendamento cancelado.")
        _send_schedule_search_options(conversation)
        return
    _send(conversation.phone_number, "Responda *Sim* para confirmar ou *Não* para cancelar.")


def _handle_schedule_collecting_patient(conversation, msg):
    step = conversation.context.get('patient_step', 'name')
    if step == 'name':
        conversation.patient_name = msg.strip()
        conversation.context['patient_step'] = 'phone'
        conversation.save()
        _send(conversation.phone_number, "Agora envie o *telefone* do paciente (com DDD):")
        return
    # step == 'phone'
    conversation.patient_phone = msg.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    conversation.context['patient_step'] = None
    conversation.save()
    # Criar paciente e agendamento
    try:
        patient = Patient.objects.filter(phone__icontains=conversation.patient_phone).first()
        if not patient:
            patient = Patient.objects.create(
                clinic=conversation.selected_doctor.clinic if conversation.selected_doctor else None,
                first_name=(conversation.patient_name or 'Paciente').split()[0],
                last_name=' '.join((conversation.patient_name or '').split()[1:]) or '',
                phone=conversation.patient_phone,
                date_of_birth=timezone.now().date() - timedelta(days=365 * 30),
                gender='O',
                is_active=True,
            )
        apt = Appointment.objects.create(
            patient=patient,
            doctor=conversation.selected_doctor,
            appointment_date=conversation.selected_date,
            appointment_time=conversation.selected_time,
            duration_minutes=30,
            appointment_type='consultation',
            payment_type='particular',
            status='scheduled',
            reason='Agendado via WhatsApp',
        )
        conversation.appointment = apt
        conversation.state = 'loop_desire_more'
        conversation.completed_at = timezone.now()
        conversation.save()
        _send(
            conversation.phone_number,
            f"✅ *Agendamento realizado com sucesso!*\n\n"
            f"Profissional: {conversation.selected_doctor.full_name}\n"
            f"Paciente: {patient.full_name}\n"
            f"Data: {format_date_br(conversation.selected_date)}\n"
            f"Horário: {conversation.selected_time.strftime('%H:%M')}\n\n"
            "Obrigado!"
        )
        _send_loop_desire_more(conversation)
    except Exception as e:
        _send(
            conversation.phone_number,
            f"❌ Erro ao registrar agendamento: {str(e)}. Tente novamente ou fale com o suporte."
        )
        conversation.state = 'schedule_confirm'
        conversation.save()


def _handle_faq_question(conversation, msg):
    entries = search_faq(msg)
    if not entries:
        _send(
            conversation.phone_number,
            "Não encontrei nada na base de conhecimento para sua pergunta. "
            "Você pode reformular ou ser transferido para um atendente. Deseja falar com um humano? (Sim / Não)"
        )
        conversation.context['faq_found'] = False
        conversation.state = 'faq_resolved'
        conversation.save()
        _send(conversation.phone_number, "A dúvida foi respondida?", [{'id': 'faq_sim', 'title': 'Sim'}, {'id': 'faq_nao', 'title': 'Não'}])
        return
    text = "📚 *Resposta da base de conhecimento:*\n\n"
    for e in entries[:2]:
        text += f"*{e.question}*\n{e.answer}\n\n"
    conversation.context['faq_found'] = True
    conversation.state = 'faq_resolved'
    conversation.save()
    _send(conversation.phone_number, text)
    _send(conversation.phone_number, "A dúvida foi respondida?", [{'id': 'faq_sim', 'title': 'Sim'}, {'id': 'faq_nao', 'title': 'Não'}])



def _handle_faq_resolved(conversation, msg_lower):
    if msg_lower in ('faq_sim', 'sim', '1'):
        conversation.state = 'loop_desire_more'
        conversation.save()
        _send_loop_desire_more(conversation)
        return
    if msg_lower in ('faq_nao', 'não', 'nao', '2'):
        _send(
            conversation.phone_number,
            "Você pode ser transferido para um atendente humano. "
            "Entre em contato pelo nosso canal de atendimento ou aguarde retorno. Obrigado!"
        )
        conversation.state = 'loop_desire_more'
        conversation.save()
        _send_loop_desire_more(conversation)
        return
    _send(conversation.phone_number, "Responda *Sim* ou *Não*: a dúvida foi respondida?")


def _send_loop_desire_more(conversation):
    """Envia 'Deseja algo mais?' com botões Sim e Não (para aparecerem no WhatsApp)."""
    _send(
        conversation.phone_number,
        "Deseja algo mais?",
        [{"id": "loop_sim", "title": "Sim"}, {"id": "loop_nao", "title": "Não"}]
    )


def _handle_loop_desire_more(conversation, msg_lower):
    if msg_lower in ('loop_sim', 'sim', '1'):
        conversation.state = 'main_menu'
        conversation.save()
        _send_main_menu(conversation)
        return
    if msg_lower in ('loop_nao', 'não', 'nao', '2'):
        conversation.state = 'ended'
        conversation.save()
        _send(
            conversation.phone_number,
            "Obrigado pelo contato! Até logo. 👋"
        )
        if WHATSAPP_CLINIC_MESSAGE and WHATSAPP_CLINIC_MESSAGE.strip():
            _send(conversation.phone_number, WHATSAPP_CLINIC_MESSAGE.strip())
        return
    _send_loop_desire_more(conversation)
