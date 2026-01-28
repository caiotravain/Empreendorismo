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
from .models import Doctor, Appointment, Patient

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
