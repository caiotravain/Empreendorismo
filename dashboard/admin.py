from django.contrib import admin
from .models import Patient, Doctor, MedicalRecord, Appointment


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 
        'email', 
        'phone', 
        'date_of_birth',
        'age',
        'gender',
        'created_at'
    ]
    list_filter = [
        'gender', 
        'created_at', 
        'city',
        'state'
    ]
    search_fields = [
        'first_name', 
        'last_name', 
        'email',
        'phone',
        'medical_insurance'
    ]
    readonly_fields = ['created_at', 'updated_at', 'age']
    date_hierarchy = 'created_at'
    ordering = ['last_name', 'first_name']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address', 'city', 'state', 'zip_code')
        }),
        ('Medical Information', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'medical_insurance')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 
        'medical_license', 
        'specialization', 
        'years_of_experience',
        'hospital_affiliation',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'specialization', 
        'is_active', 
        'created_at',
        'years_of_experience'
    ]
    search_fields = [
        'user__first_name', 
        'user__last_name', 
        'user__email',
        'medical_license',
        'specialization',
        'hospital_affiliation'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['user__last_name', 'user__first_name']
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Professional Information', {
            'fields': ('medical_license', 'specialization', 'years_of_experience', 'hospital_affiliation')
        }),
        ('Contact Information', {
            'fields': ('phone',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = [
        'patient_name', 
        'doctor_name', 
        'datetime', 
        'created_at',
        'content_preview'
    ]
    list_filter = [
        'datetime', 
        'created_at', 
        'patient', 
        'doctor',
        'doctor__specialization'
    ]
    search_fields = [
        'patient__first_name', 
        'patient__last_name', 
        'doctor__user__first_name',
        'doctor__user__last_name',
        'doctor__medical_license',
        'content'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'datetime'
    ordering = ['-datetime']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('datetime', 'patient', 'doctor')
        }),
        ('Medical Record Content', {
            'fields': ('content',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_preview(self, obj):
        """Show a preview of the content"""
        if len(obj.content) > 100:
            return obj.content[:100] + "..."
        return obj.content
    content_preview.short_description = "Content Preview"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'patient',
        'doctor',
        'appointment_date',
        'appointment_time',
        'duration_minutes',
        'appointment_type',
        'status',
        'location',
        'is_today',
        'is_upcoming'
    ]
    list_filter = [
        'appointment_date',
        'appointment_type',
        'status',
        'doctor',
        'patient',
        'reminder_sent',
        'created_at'
    ]
    search_fields = [
        'patient__first_name',
        'patient__last_name',
        'doctor__user__first_name',
        'doctor__user__last_name',
        'doctor__medical_license',
        'reason',
        'notes',
        'location'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'appointment_datetime',
        'end_time',
        'is_past',
        'is_today',
        'is_upcoming'
    ]
    date_hierarchy = 'appointment_date'
    ordering = ['appointment_date', 'appointment_time']
    
    fieldsets = (
        ('Appointment Details', {
            'fields': (
                'patient',
                'doctor',
                'appointment_date',
                'appointment_time',
                'duration_minutes',
                'appointment_type',
                'status',
                'location'
            )
        }),
        ('Additional Information', {
            'fields': ('reason', 'notes'),
            'classes': ('collapse',)
        }),
        ('Reminder Settings', {
            'fields': ('reminder_sent', 'reminder_date'),
            'classes': ('collapse',)
        }),
        ('Cancellation Information', {
            'fields': ('cancelled_at', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Computed Fields', {
            'fields': (
                'appointment_datetime',
                'end_time',
                'is_past',
                'is_today',
                'is_upcoming'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_cancelled', 'send_reminders']
    
    def mark_as_completed(self, request, queryset):
        """Mark selected appointments as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} appointments marked as completed.')
    mark_as_completed.short_description = "Mark selected appointments as completed"
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected appointments as cancelled"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} appointments marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected appointments as cancelled"
    
    def send_reminders(self, request, queryset):
        """Send reminders for selected appointments"""
        # This would integrate with your email/notification system
        updated = queryset.update(reminder_sent=True)
        self.message_user(request, f'Reminders sent for {updated} appointments.')
    send_reminders.short_description = "Send reminders for selected appointments"
