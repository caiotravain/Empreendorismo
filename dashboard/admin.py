from django.contrib import admin
from .models import Admin, Patient, Doctor, Secretary, MedicalRecord, Appointment, Expense, Income, WaitingListEntry


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'doctor',
        'email', 
        'phone', 
        'date_of_birth',
        'age',
        'gender',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'doctor',
        'gender', 
        'is_active',
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
        ('Doctor Assignment', {
            'fields': ('doctor',)
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address', 'city', 'state', 'zip_code')
        }),
        ('Medical Information', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'medical_insurance')
        }),
        ('Status', {
            'fields': ('is_active',)
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
        ('Administration', {
            'fields': ('admin',)
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


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'email',
        'phone',
        'doctors_count',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'is_active',
        'created_at'
    ]
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'user__username',
        'phone'
    ]
    readonly_fields = ['created_at', 'updated_at', 'doctors_count']
    date_hierarchy = 'created_at'
    ordering = ['user__last_name', 'user__first_name']
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'doctors_count'),
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
        """Mark selected appointments as cancelled and remove associated income records"""
        income_deleted_count = 0
        for appointment in queryset:
            # Count and delete associated income records
            associated_incomes = appointment.incomes.all()
            income_deleted_count += associated_incomes.count()
            associated_incomes.delete()
        
        updated = queryset.update(status='cancelled')
        message = f'{updated} appointments marked as cancelled'
        if income_deleted_count > 0:
            message += f' and {income_deleted_count} income records removed'
        self.message_user(request, message)
    mark_as_cancelled.short_description = "Mark selected appointments as cancelled"
    
    def send_reminders(self, request, queryset):
        """Send reminders for selected appointments"""
        # This would integrate with your email/notification system
        updated = queryset.update(reminder_sent=True)
        self.message_user(request, f'Reminders sent for {updated} appointments.')
    send_reminders.short_description = "Send reminders for selected appointments"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'description',
        'doctor',
        'amount',
        'category',
        'expense_date',
        'vendor',
        'receipt_number',
        'created_at'
    ]
    list_filter = [
        'category',
        'expense_date',
        'doctor',
        'created_at',
        'vendor'
    ]
    search_fields = [
        'description',
        'doctor__user__first_name',
        'doctor__user__last_name',
        'doctor__medical_license',
        'vendor',
        'receipt_number',
        'notes'
    ]
    readonly_fields = ['created_at', 'updated_at', 'formatted_amount']
    date_hierarchy = 'expense_date'
    ordering = ['-expense_date', '-created_at']
    
    fieldsets = (
        ('Expense Information', {
            'fields': ('doctor', 'description', 'amount', 'formatted_amount', 'category', 'expense_date')
        }),
        ('Vendor Information', {
            'fields': ('vendor', 'receipt_number'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_expenses']
    
    def export_expenses(self, request, queryset):
        """Export selected expenses to CSV"""
        # This would implement CSV export functionality
        self.message_user(request, f'Export functionality for {queryset.count()} expenses would be implemented here.')
    export_expenses.short_description = "Export selected expenses to CSV"


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = [
        'description', 
        'amount', 
        'category', 
        'income_date', 
        'doctor_name', 
        'payment_method',
        'created_at'
    ]
    list_filter = [
        'category', 
        'income_date', 
        'payment_method',
        'created_at',
        'doctor'
    ]
    search_fields = [
        'description', 
        'notes', 
        'doctor__first_name', 
        'doctor__last_name'
    ]
    date_hierarchy = 'income_date'
    ordering = ['-income_date', '-created_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('doctor', 'description', 'amount', 'category')
        }),
        ('Data e Pagamento', {
            'fields': ('income_date', 'payment_method')
        }),
        ('Informações Adicionais', {
            'fields': ('notes', 'appointment'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_incomes']
    
    def export_incomes(self, request, queryset):
        """Export selected incomes to CSV"""
        # This would implement CSV export functionality
        self.message_user(request, f'Export functionality for {queryset.count()} incomes would be implemented here.')
    export_incomes.short_description = "Export selected incomes to CSV"


@admin.register(Secretary)
class SecretaryAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'email',
        'phone',
        'doctor',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'doctor',
        'is_active',
        'created_at'
    ]
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'user__username',
        'phone',
        'doctor__user__first_name',
        'doctor__user__last_name',
        'doctor__medical_license'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['user__last_name', 'user__first_name']
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Work Assignment', {
            'fields': ('doctor',)
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


@admin.register(WaitingListEntry)
class WaitingListEntryAdmin(admin.ModelAdmin):
    list_display = [
        'patient_name',
        'doctor',
        'urgency_level',
        'status',
        'phone',
        'email',
        'created_at'
    ]
    list_filter = [
        'doctor',
        'urgency_level',
        'status',
        'created_at'
    ]
    search_fields = [
        'patient_name',
        'phone',
        'email',
        'notes',
        'patient__first_name',
        'patient__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'contact_info', 'is_active']
    date_hierarchy = 'created_at'
    ordering = ['-urgency_level', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('doctor', 'patient', 'patient_name')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'contact_info')
        }),
        ('Appointment Preferences', {
            'fields': ('preferred_days_times',)
        }),
        ('Priority & Status', {
            'fields': ('urgency_level', 'status', 'is_active')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_scheduled', 'mark_as_archived', 'mark_as_pending']
    
    def mark_as_scheduled(self, request, queryset):
        """Mark selected entries as scheduled"""
        updated = queryset.update(status='scheduled')
        self.message_user(request, f'{updated} entries marked as scheduled.')
    mark_as_scheduled.short_description = "Mark selected entries as scheduled"
    
    def mark_as_archived(self, request, queryset):
        """Mark selected entries as archived"""
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} entries marked as archived.')
    mark_as_archived.short_description = "Mark selected entries as archived"
    
    def mark_as_pending(self, request, queryset):
        """Mark selected entries as pending"""
        updated = queryset.update(status='pending')
        self.message_user(request, f'{updated} entries marked as pending.')
    mark_as_pending.short_description = "Mark selected entries as pending"
