from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('prontuarios/', views.prontuarios, name='prontuarios'),
    path('add-medical-record/', views.add_medical_record, name='add_medical_record'),
    path('exames/', views.exames, name='exames'),
    path('prescricao/', views.prescricao, name='prescricao'),
    path('indicadores/', views.indicadores, name='indicadores'),
    path('settings/', views.settings, name='settings'),
    
    # API endpoints for appointment modal
    path('api/patients/', views.api_patients, name='api_patients'),
    path('api/doctors/', views.api_doctors, name='api_doctors'),
    path('api/appointments/', views.api_appointments, name='api_appointments'),
    path('api/patients/create/', views.api_create_patient, name='api_create_patient'),
    path('api/week-appointments/', views.api_week_appointments, name='api_week_appointments'),
    path('api/appointments/cancel/', views.api_cancel_appointment, name='api_cancel_appointment'),
    path('api/appointments/confirm-attendance/', views.api_confirm_attendance, name='api_confirm_attendance'),
    path('api/next-appointment/', views.api_next_appointment, name='api_next_appointment'),
    
    # API endpoints for prescriptions
    path('api/prescriptions/', views.api_prescriptions, name='api_prescriptions'),
    path('api/prescriptions/create/', views.api_create_prescription, name='api_create_prescription'),
    path('api/prescriptions/send-email/', views.api_send_prescription_email, name='api_send_prescription_email'),
    path('api/prescriptions/send-whatsapp/', views.api_send_prescription_whatsapp, name='api_send_prescription_whatsapp'),
    path('api/prescriptions/print/', views.api_print_prescription, name='api_print_prescription'),
]
