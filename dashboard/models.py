from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator


class Patient(models.Model):
    """
    Patient model to store patient information
    """
    # Basic Information
    first_name = models.CharField(max_length=100, help_text="Patient's first name")
    last_name = models.CharField(max_length=100, help_text="Patient's last name")
    
    # Contact Information
    email = models.EmailField(blank=True, null=True, help_text="Patient's email address")
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )],
        help_text="Patient's phone number"
    )
    
    # Personal Information
    date_of_birth = models.DateField(help_text="Patient's date of birth")
    gender = models.CharField(
        max_length=10,
        choices=[
            ('M', 'Male'),
            ('F', 'Female'),
            ('O', 'Other'),
        ],
        help_text="Patient's gender"
    )
    
    # Address
    address = models.TextField(blank=True, null=True, help_text="Patient's address")
    city = models.CharField(max_length=100, blank=True, null=True, help_text="Patient's city")
    state = models.CharField(max_length=100, blank=True, null=True, help_text="Patient's state")
    zip_code = models.CharField(max_length=20, blank=True, null=True, help_text="Patient's ZIP code")
    
    # Medical Information
    emergency_contact_name = models.CharField(max_length=200, blank=True, null=True, help_text="Emergency contact name")
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Emergency contact phone")
    medical_insurance = models.CharField(max_length=200, blank=True, null=True, help_text="Medical insurance information")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this patient record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this patient record was last updated")
    
    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


class Doctor(models.Model):
    """
    Doctor model to store doctor information
    """
    # Link to Django User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        help_text="Django User object for the doctor"
    )
    
    # Professional Information
    medical_license = models.CharField(
        max_length=50,
        unique=True,
        help_text="Doctor's medical license number"
    )
    specialization = models.CharField(
        max_length=100,
        help_text="Doctor's medical specialization"
    )
    
    # Contact Information
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )],
        help_text="Doctor's phone number"
    )
    
    # Professional Details
    years_of_experience = models.PositiveIntegerField(
        default=0,
        help_text="Years of medical experience"
    )
    hospital_affiliation = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Hospital or clinic affiliation"
    )
    
    # Availability
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the doctor is currently active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this doctor profile was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this doctor profile was last updated")
    
    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        ordering = ['user__last_name', 'user__first_name']
        indexes = [
            models.Index(fields=['medical_license']),
            models.Index(fields=['specialization']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"
    
    @property
    def full_name(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"
    
    @property
    def email(self):
        return self.user.email


class MedicalRecord(models.Model):
    """
    Medical Record (Prontuário) model to store patient medical records
    """
    # Primary fields
    datetime = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when the medical record was created"
    )
    
    # Foreign Keys
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_records',
        null=True,
        blank=True,
        help_text="Patient this medical record belongs to"
    )
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='medical_records',
        null=True,
        blank=True,
        help_text="Doctor who created this medical record"
    )
    

    
    content = models.TextField(
        help_text="Medical record content and notes"
    )
    
    # Additional useful fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was first created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )
    
    class Meta:
        verbose_name = "Medical Record"
        verbose_name_plural = "Medical Records"
        ordering = ['-datetime', '-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['datetime']),
        ]
    
    def __str__(self):
        if self.patient:
            return f"Medical Record for {self.patient.full_name} - {self.datetime.strftime('%Y-%m-%d %H:%M')}"
        else:
            return f"Medical Record - {self.datetime.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def patient_name(self):
        """Get patient name"""
        if self.patient:
            return self.patient.full_name
        return "Unknown Patient"
    
    @property
    def doctor_name(self):
        """Get doctor name"""
        if self.doctor:
            return self.doctor.full_name
        return "Unknown Doctor"


class Appointment(models.Model):
    """
    Appointment model to manage medical appointments
    """
    # Status choices
    STATUS_CHOICES = [
        ('scheduled', 'Agendada'),
        ('confirmed', 'Confirmada'),
        ('in_progress', 'Em Andamento'),
        ('completed', 'Concluída'),
        ('cancelled', 'Cancelada'),
        ('no_show', 'Não Compareceu'),
        ('rescheduled', 'Reagendada'),
    ]
    
    # Appointment type choices
    TYPE_CHOICES = [
        ('consultation', 'Consulta'),
        ('follow_up', 'Retorno'),
        ('checkup', 'Check-up'),
        ('emergency', 'Emergência'),
        ('procedure', 'Procedimento'),
        ('therapy', 'Terapia'),
        ('other', 'Outro'),
    ]
    
    # Foreign Keys
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments',
        help_text="Patient for this appointment"
    )
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='appointments',
        help_text="Doctor for this appointment"
    )
    
    # Appointment Details
    appointment_date = models.DateField(
        help_text="Date of the appointment"
    )
    
    appointment_time = models.TimeField(
        help_text="Time of the appointment"
    )
    
    duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Duration of the appointment in minutes"
    )
    
    appointment_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='consultation',
        help_text="Type of appointment"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        help_text="Current status of the appointment"
    )
    
    # Additional Information
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for the appointment"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the appointment"
    )
    
    # Location
    location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Location of the appointment (room, clinic, etc.)"
    )
    
    # Reminder settings
    reminder_sent = models.BooleanField(
        default=False,
        help_text="Whether a reminder has been sent"
    )
    
    reminder_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the reminder was sent"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this appointment was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this appointment was last updated"
    )
    
    # Cancellation information
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the appointment was cancelled"
    )
    
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for cancellation"
    )
    
    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ['appointment_date', 'appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['status']),
            models.Index(fields=['appointment_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'appointment_time'],
                name='unique_doctor_appointment_time'
            )
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.doctor.full_name} - {self.appointment_date} {self.appointment_time}"
    
    @property
    def appointment_datetime(self):
        """Get combined appointment date and time"""
        from datetime import datetime
        return datetime.combine(self.appointment_date, self.appointment_time)
    
    @property
    def end_time(self):
        """Calculate appointment end time"""
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(self.appointment_date, self.appointment_time)
        end_datetime = start_datetime + timedelta(minutes=self.duration_minutes)
        return end_datetime.time()
    
    @property
    def is_past(self):
        """Check if appointment is in the past"""
        from datetime import datetime
        now = datetime.now()
        appointment_datetime = datetime.combine(self.appointment_date, self.appointment_time)
        return appointment_datetime < now
    
    @property
    def is_today(self):
        """Check if appointment is today"""
        from datetime import date
        return self.appointment_date == date.today()
    
    @property
    def is_upcoming(self):
        """Check if appointment is in the future"""
        from datetime import datetime
        now = datetime.now()
        appointment_datetime = datetime.combine(self.appointment_date, self.appointment_time)
        return appointment_datetime > now
    
    def cancel(self, reason=None):
        """Cancel the appointment"""
        from django.utils import timezone
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        if reason:
            self.cancellation_reason = reason
        self.save()
    
    def complete(self):
        """Mark appointment as completed"""
        self.status = 'completed'
        self.save()
    
    def reschedule(self, new_date, new_time):
        """Reschedule the appointment"""
        self.appointment_date = new_date
        self.appointment_time = new_time
        self.status = 'rescheduled'
        self.save()
