from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('prontuarios/', views.prontuarios, name='prontuarios'),
    path('add-medical-record/', views.add_medical_record, name='add_medical_record'),
    path('prescricao/', views.prescricao, name='prescricao'),
    path('patients/', views.patients, name='patients'),
    path('indicadores/', views.indicadores, name='indicadores'),
    path('finance/', views.finance, name='finance'),
    path('settings/', views.settings, name='settings'),
    
    # API endpoints for appointment modal
    path('api/patients/', views.api_patients, name='api_patients'),
    path('api/patients/<int:patient_id>/', views.api_patient_detail, name='api_patient_detail'),
    path('api/doctors/', views.api_doctors, name='api_doctors'),
    path('api/appointments/', views.api_appointments, name='api_appointments'),
    path('api/patients/create/', views.api_create_patient, name='api_create_patient'),
    path('api/week-appointments/', views.api_week_appointments, name='api_week_appointments'),
    path('api/appointments/cancel/', views.api_cancel_appointment, name='api_cancel_appointment'),
    path('api/appointments/confirm-attendance/', views.api_confirm_attendance, name='api_confirm_attendance'),
    path('api/appointments/sync-income/', views.api_sync_appointment_income, name='api_sync_appointment_income'),
    path('api/appointments/update/', views.api_update_appointment, name='api_update_appointment'),
    path('api/next-appointment/', views.api_next_appointment, name='api_next_appointment'),
    path('api/agenda-stats/', views.api_agenda_stats, name='api_agenda_stats'),
    
    # API endpoints for prescriptions
    path('api/prescriptions/', views.api_prescriptions, name='api_prescriptions'),
    path('api/prescriptions/create/', views.api_create_prescription, name='api_create_prescription'),
    path('api/prescriptions/send-email/', views.api_send_prescription_email, name='api_send_prescription_email'),
    path('api/prescriptions/send-whatsapp/', views.api_send_prescription_whatsapp, name='api_send_prescription_whatsapp'),
    path('api/prescriptions/print/', views.api_print_prescription, name='api_print_prescription'),
    
    # API endpoints for expenses
    path('api/expenses/', views.api_expenses, name='api_expenses'),
    path('api/expenses/create/', views.api_create_expense, name='api_create_expense'),
    path('api/expenses/totals/', views.api_expense_totals, name='api_expense_totals'),
    path('api/expenses/delete/<int:expense_id>/', views.api_delete_expense, name='api_delete_expense'),
    
    # API endpoints for incomes
    path('api/incomes/', views.api_incomes, name='api_incomes'),
    path('api/incomes/create/', views.api_create_income, name='api_create_income'),
    path('api/incomes/delete/<int:income_id>/', views.api_delete_income, name='api_delete_income'),
    
    # API endpoints for patients
    path('api/patients/update/', views.api_update_patient, name='api_update_patient'),
    path('api/patients/deactivate/<int:patient_id>/', views.api_deactivate_patient, name='api_deactivate_patient'),
    path('api/patients/activate/<int:patient_id>/', views.api_activate_patient, name='api_activate_patient'),
    
    # API endpoint for admin doctor selection
    path('select-doctor/', views.select_doctor, name='select_doctor'),
]
