from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator


class Clinic(models.Model):
    """
    Clinic model - top-level entity that groups doctors and patients.
    Doctors and secretaries belong to a clinic; patients are shared within a clinic.
    """
    name = models.CharField(max_length=200, help_text="Clinic name")
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )],
        help_text="Clinic phone number"
    )
    email = models.EmailField(blank=True, null=True, help_text="Clinic email address")
    address = models.TextField(blank=True, null=True, help_text="Clinic address")
    is_active = models.BooleanField(default=True, help_text="Whether the clinic is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clinic"
        verbose_name_plural = "Clinics"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def active_doctors(self):
        return self.doctors.filter(is_active=True)

    @property
    def doctors_count(self):
        return self.doctors.filter(is_active=True).count()

    @property
    def patients_count(self):
        return self.patients.filter(is_active=True).count()

    def get_doctors(self):
        return self.doctors.all()

    def get_active_doctors(self):
        return self.doctors.filter(is_active=True)

    def get_clinic_admins(self):
        return self.doctors.filter(is_clinic_admin=True, is_active=True)


class Patient(models.Model):
    """
    Patient model to store patient information.
    Patients are shared within a clinic and not tied to a specific doctor.
    """
    # Link to Clinic (patients are shared within a clinic)
    clinic = models.ForeignKey(
        'Clinic',
        on_delete=models.CASCADE,
        related_name='patients',
        null=True,
        blank=True,
        help_text="Clinic this patient belongs to"
    )
    
    # Basic Information
    first_name = models.CharField(max_length=100, help_text="Patient's first name")
    last_name = models.CharField(max_length=100, help_text="Patient's last name")
    cpf = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        help_text="Patient's CPF (Brazilian tax ID)"
    )
    
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
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the patient is currently active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this patient record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this patient record was last updated")
    
    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['clinic']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['cpf']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        from datetime import date
        if not self.date_of_birth:
            return None
        
        # Handle both date objects and string dates
        if isinstance(self.date_of_birth, str):
            try:
                dob = date.fromisoformat(self.date_of_birth)
            except ValueError:
                return None
        else:
            dob = self.date_of_birth
            
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_loyalty_metrics(self):
        """
        Calculates and returns loyalty metrics for the patient:
        - last_visit: date of the last completed appointment
        - avg_interval: average days between consecutive completed appointments
        - total_completed: total number of completed appointments
        - loyalty_status: 'Novo', 'Ativo', 'Em Risco', 'Churn'
        """
        from datetime import date
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        
        completed_appointments = self.appointments.filter(status='completed').order_by('appointment_date')
        total_completed = completed_appointments.count()
        
        last_visit = None
        avg_interval = None
        
        if total_completed > 0:
            last_visit = completed_appointments.last().appointment_date
            
            if total_completed > 1:
                intervals = []
                prev_date = None
                for appt in completed_appointments:
                    if prev_date:
                        intervals.append((appt.appointment_date - prev_date).days)
                    prev_date = appt.appointment_date
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)

        # Get settings for churn
        settings = AppointmentSettings.objects.first()
        churn_months = settings.churn_threshold_months if settings else 12
        risk_months = settings.churn_risk_months if settings else 6
        
        today = timezone.now().date()
        
        # Determine Status
        status = 'Inativo' # Default if no appointments
        
        if total_completed == 0:
            # Check if created recently
            if self.created_at.date() >= today.replace(day=1):
                status = 'Novo'
            else:
                status = 'Inativo'
        else:
            # Check if first ever appointment was this month
            first_visit = completed_appointments.first().appointment_date
            if first_visit >= today.replace(day=1):
                status = 'Novo'
            else:
                months_since_last = relativedelta(today, last_visit).years * 12 + relativedelta(today, last_visit).months
                
                if months_since_last >= churn_months:
                    status = 'Churn'
                elif months_since_last >= risk_months:
                    status = 'Em Risco'
                else:
                    status = 'Ativo'
                    
        # No-show Rate
        all_appts = self.appointments.all()
        total_appts = all_appts.count()
        no_show_count = all_appts.filter(status='no_show').count()
        no_show_rate = (no_show_count / total_appts * 100) if total_appts > 0 else 0

        return {
            'last_visit': last_visit,
            'avg_interval': round(avg_interval, 1) if avg_interval is not None else None,
            'total_completed': total_completed,
            'status': status,
            'no_show_rate': round(no_show_rate, 1)
        }

    @property
    def age(self):
        from datetime import date
        if not self.date_of_birth:
            return None
        
        # Handle both date objects and string dates
        if isinstance(self.date_of_birth, str):
            try:
                from datetime import datetime
                birth_date = datetime.strptime(self.date_of_birth, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None
        else:
            birth_date = self.date_of_birth
        
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


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

    # Link to Clinic
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctors',
        help_text="Clinic this doctor belongs to"
    )

    # Whether this doctor also has clinic admin privileges
    is_clinic_admin = models.BooleanField(
        default=False,
        help_text="Whether this doctor also acts as a clinic administrator"
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
    
    # Custom expense categories defined by this doctor
    custom_expense_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom expense categories defined by this doctor"
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
    
    @property
    def active_secretaries_count(self):
        """Get the number of active secretaries for this doctor"""
        return self.secretaries.filter(is_active=True).count()
    
    @property
    def active_secretaries(self):
        """Get all active secretaries for this doctor"""
        return self.secretaries.filter(is_active=True)
    
    def get_secretaries(self):
        """Get all secretaries (active and inactive)"""
        return self.secretaries.all()

    def get_active_secretaries(self):
        """Get only active secretaries"""
        return self.secretaries.filter(is_active=True)

    @property
    def patients_count(self):
        """Get the number of active patients in this doctor's clinic"""
        if self.clinic:
            return self.clinic.patients.filter(is_active=True).count()
        return 0

    @property
    def active_patients(self):
        """Get all active patients in this doctor's clinic"""
        if self.clinic:
            return self.clinic.patients.filter(is_active=True)
        return Patient.objects.none()

    def get_patients(self):
        """Get all patients in this doctor's clinic"""
        if self.clinic:
            return self.clinic.patients.all()
        return Patient.objects.none()

    def get_active_patients(self):
        """Get only active patients in this doctor's clinic"""
        if self.clinic:
            return self.clinic.patients.filter(is_active=True)
        return Patient.objects.none()


class Secretary(models.Model):
    """
    Secretary model to store secretary information
    Each secretary belongs to a clinic and can work for multiple doctors within it.
    """
    # Link to Django User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='secretary_profile',
        help_text="Django User object for the secretary"
    )

    # Link to Clinic
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='secretaries',
        help_text="Clinic this secretary belongs to"
    )

    # Link to Doctors (many-to-many: a secretary can work for multiple doctors)
    doctors = models.ManyToManyField(
        Doctor,
        related_name='secretaries',
        blank=True,
        help_text="Doctors this secretary works for"
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
        help_text="Secretary's phone number"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the secretary is currently active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this secretary profile was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this secretary profile was last updated")
    
    class Meta:
        verbose_name = "Secretary"
        verbose_name_plural = "Secretaries"
        ordering = ['user__last_name', 'user__first_name']
        indexes = [
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        doctor_names = ', '.join(d.user.get_full_name() or d.user.username for d in self.doctors.all()[:3])
        if self.doctors.count() > 3:
            doctor_names += '...'
        return f"Secretary: {self.user.get_full_name() or self.user.username} - {doctor_names or 'No doctors'}"
    
    @property
    def full_name(self):
        return f"{self.user.get_full_name() or self.user.username}"
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def doctor_name(self):
        """Get the doctor's name"""
        return self.doctor.full_name


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
    
    # Payment type choices
    PAYMENT_TYPE_CHOICES = [
        ('convenio', 'Convênio'),
        ('particular', 'Particular'),
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
    
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='particular',
        help_text="Payment type for the appointment"
    )
    
    insurance_operator = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Insurance operator (convênio) when payment type is convenio"
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
    
    # Value/Price
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Value/price of the appointment"
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
                condition=models.Q(status__in=['scheduled', 'confirmed', 'in_progress', 'completed', 'no_show', 'rescheduled']),
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
        """Cancel the appointment and remove associated income records"""
        from django.utils import timezone
        
        # Remove any associated income records
        # Use the related_name to avoid circular import
        self.incomes.all().delete()
        
        # Check if reason contains "falta" (case-insensitive) to mark as no_show
        if reason and 'falta' in reason.lower():
            self.status = 'no_show'
        else:
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


class CalendarBlock(models.Model):
    """
    Block a period in the doctor's calendar (unavailable / off).
    Shown on the agenda and prevents new appointments in that period.
    """
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='calendar_blocks',
        help_text="Doctor whose calendar is blocked"
    )
    start = models.DateTimeField(help_text="Start of blocked period")
    end = models.DateTimeField(help_text="End of blocked period")
    reason = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Optional reason (e.g. Folga, Congresso)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Calendar Block"
        verbose_name_plural = "Calendar Blocks"
        ordering = ['start']
        indexes = [
            models.Index(fields=['doctor']),
            models.Index(fields=['start', 'end']),
        ]

    def __str__(self):
        return f"Bloqueio {self.start} - {self.end} ({self.doctor})"


class PrescriptionTemplate(models.Model):
    """
    Prescription template model for predefined prescription formats
    """
    name = models.CharField(
        max_length=200,
        help_text="Name of the prescription template"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the prescription template"
    )
    
    # Template content
    header_text = models.TextField(
        blank=True,
        null=True,
        help_text="Header text for the prescription"
    )
    
    footer_text = models.TextField(
        blank=True,
        null=True,
        help_text="Footer text for the prescription"
    )
    
    # Doctor who created this template
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='prescription_templates',
        help_text="Doctor who created this template"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Prescription Template"
        verbose_name_plural = "Prescription Templates"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Prescription(models.Model):
    """
    Prescription model to store medical prescriptions
    """
    # Status choices
    STATUS_CHOICES = [
        ('active', 'Ativa'),
        ('completed', 'Concluída'),
        ('cancelled', 'Cancelada'),
        ('expired', 'Expirada'),
    ]
    
    # Foreign Keys
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        help_text="Patient for this prescription"
    )
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        help_text="Doctor who prescribed this medication"
    )
    
    # Prescription Details
    prescription_date = models.DateField(
        default=timezone.now,
        help_text="Date when the prescription was created"
    )
    
    template = models.ForeignKey(
        PrescriptionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions',
        help_text="Prescription template used"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Current status of the prescription"
    )
    
    # Additional Information
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for the prescription"
    )
    
    # Delivery Information
    sent_by_email = models.BooleanField(
        default=False,
        help_text="Whether prescription was sent by email"
    )
    
    sent_by_whatsapp = models.BooleanField(
        default=False,
        help_text="Whether prescription was sent by WhatsApp"
    )
    
    printed = models.BooleanField(
        default=False,
        help_text="Whether prescription was printed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"
        ordering = ['-prescription_date', '-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['prescription_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Prescription for {self.patient.full_name} - {self.prescription_date}"
    
    @property
    def patient_name(self):
        return self.patient.full_name
    
    @property
    def doctor_name(self):
        return self.doctor.full_name


class PrescriptionItem(models.Model):
    """
    Individual medication item in a prescription
    """
    # Foreign Key
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Prescription this item belongs to"
    )
    
    # Medication Details
    medication_name = models.CharField(
        max_length=200,
        help_text="Name of the medication"
    )
    
    quantity = models.CharField(
        max_length=100,
        help_text="Quantity of the medication (e.g., '30 comprimidos', '1 frasco')"
    )
    
    dosage = models.TextField(
        help_text="Dosage instructions (e.g., '1 comprimido de 8/8 horas')"
    )
    
    # Additional Information
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for this medication"
    )
    
    # Order in prescription
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order of this item in the prescription"
    )
    
    class Meta:
        verbose_name = "Prescription Item"
        verbose_name_plural = "Prescription Items"
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['prescription']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"{self.medication_name} - {self.prescription.patient.full_name}"


class Expense(models.Model):
    """
    Expense model to track doctor's financial expenses
    """
    # Category choices
    CATEGORY_CHOICES = [
        ('office_supplies', 'Material de Escritório'),
        ('medical_supplies', 'Material Médico'),
        ('equipment', 'Equipamentos'),
        ('utilities', 'Utilidades'),
        ('rent', 'Aluguel'),
        ('insurance', 'Seguro'),
        ('marketing', 'Marketing'),
        ('professional_services', 'Serviços Profissionais'),
        ('travel', 'Viagens'),
        ('education', 'Educação'),
        ('other', 'Outros'),
    ]
    
    # Foreign Key
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='expenses',
        help_text="Doctor who made this expense"
    )
    
    # Expense Details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount of the expense"
    )
    
    description = models.CharField(
        max_length=200,
        help_text="Description of the expense"
    )
    
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        help_text="Category of the expense"
    )
    
    expense_date = models.DateField(
        default=timezone.now,
        help_text="Date when the expense was made"
    )
    
    # Additional Information
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the expense"
    )
    
    # Receipt/Invoice information
    receipt_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Receipt or invoice number"
    )
    
    vendor = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Vendor or supplier name"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['doctor']),
            models.Index(fields=['expense_date']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.description} - R$ {self.amount} ({self.expense_date})"
    
    @property
    def doctor_name(self):
        return self.doctor.full_name
    
    @property
    def formatted_amount(self):
        return f"R$ {self.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


class Income(models.Model):
    """
    Income model to track doctor's financial income from appointments
    """
    # Category choices
    CATEGORY_CHOICES = [
        ('consultation', 'Consulta'),
        ('follow_up', 'Retorno'),
        ('checkup', 'Check-up'),
        ('emergency', 'Emergência'),
        ('procedure', 'Procedimento'),
        ('therapy', 'Terapia'),
        ('other', 'Outros'),
    ]
    
    # Foreign Keys
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='incomes',
        help_text="Doctor who received this income"
    )
    
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='incomes',
        blank=True,
        null=True,
        help_text="Appointment that generated this income"
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        related_name='incomes',
        blank=True,
        null=True,
        help_text="Patient related to this income"
    )
    
    # Income Details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount of the income"
    )
    
    description = models.CharField(
        max_length=200,
        help_text="Description of the income"
    )
    
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        help_text="Category of the income"
    )
    
    income_date = models.DateField(
        default=timezone.now,
        help_text="Date when the income was received"
    )
    
    # Additional Information
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the income"
    )
    
    # Payment information
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Dinheiro'),
        ('card', 'Cartão'),
        ('transfer', 'Transferência'),
        ('pix', 'PIX'),
        ('other', 'Outros'),
    ]
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True,
        help_text="Payment method"
    )

    PAYMENT_TYPE_CHOICES = [
        ('particular', 'Particular'),
        ('convenio', 'Convênio'),
    ]
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Whether payment is private (particular) or via health plan (convenio)"
    )

    is_free_return = models.BooleanField(
        default=False,
        help_text="Mark as a free return visit (retorno gratuito) — amount treated as R$ 0,00"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Income"
        verbose_name_plural = "Incomes"
        ordering = ['-income_date', '-created_at']
        indexes = [
            models.Index(fields=['doctor']),
            models.Index(fields=['income_date']),
            models.Index(fields=['category']),
            models.Index(fields=['patient']),
        ]
    
    def __str__(self):
        return f"{self.description} - R$ {self.amount} ({self.income_date})"
    
    @property
    def doctor_name(self):
        return self.doctor.full_name
    
    @property
    def patient_name(self):
        if self.patient:
            return self.patient.full_name
        return None
    
    @property
    def formatted_amount(self):
        return f"R$ {self.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


class Medication(models.Model):
    """
    Medication model to store medication information
    """
    name = models.CharField(max_length=200, help_text="Name of the medication")
    description = models.TextField(blank=True, null=True, help_text="Description of the medication")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Medication"
        verbose_name_plural = "Medications"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    @property
    def formatted_name(self):
        return self.name.upper()

    @property
    def formatted_description(self):
        return self.description.upper()


class WaitingListEntry(models.Model):
    """
    Waiting List Entry model to manage patients waiting for appointment slots
    """
    # Urgency level choices
    URGENCY_CHOICES = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
    ]
    
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('scheduled', 'Agendada'),
        ('archived', 'Arquivada'),
    ]
    
    # Link to Doctor (who manages this waitlist entry)
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='waiting_list_entries',
        help_text="Doctor who manages this waitlist entry"
    )
    
    # Link to Patient (optional - can be None if patient doesn't exist yet)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='waiting_list_entries',
        help_text="Patient record if exists in system (optional)"
    )
    
    # Patient Information (required if patient is None)
    patient_name = models.CharField(
        max_length=200,
        help_text="Patient's full name"
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
        help_text="Patient's phone number"
    )
    
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Patient's email address"
    )
    
    # Preferred Days/Times (flexible text field)
    preferred_days_times = models.TextField(
        blank=True,
        null=True,
        help_text="Preferred days and times for appointment (e.g., 'Monday mornings, Wednesday afternoons')"
    )
    
    # Urgency Level
    urgency_level = models.CharField(
        max_length=10,
        choices=URGENCY_CHOICES,
        default='medium',
        help_text="Urgency level of the appointment request"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the waitlist entry"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the patient or appointment request"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this entry was added to the waitlist"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this entry was last updated"
    )
    
    class Meta:
        verbose_name = "Waiting List Entry"
        verbose_name_plural = "Waiting List Entries"
        ordering = ['-urgency_level', 'created_at']  # High urgency first, then oldest first
        indexes = [
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['urgency_level', 'created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        urgency_display = self.get_urgency_level_display()
        return f"{self.patient_name} - {urgency_display} - {self.get_status_display()}"
    
    @property
    def contact_info(self):
        """Get formatted contact information"""
        contact_parts = []
        if self.phone:
            contact_parts.append(f"Tel: {self.phone}")
        if self.email:
            contact_parts.append(f"Email: {self.email}")
        return " | ".join(contact_parts) if contact_parts else "Sem contato"
    
    @property
    def is_active(self):
        """Check if entry is active (pending status)"""
        return self.status == 'pending'
    
    def get_urgency_priority(self):
        """Get numeric priority for sorting (higher = more urgent)"""
        priority_map = {'high': 3, 'medium': 2, 'low': 1}
        return priority_map.get(self.urgency_level, 0)


class AppointmentSettings(models.Model):
    """
    Settings model to store configurable appointment values.
    Uses singleton pattern - only one instance should exist.
    """
    # Duration options (in minutes)
    duration_options = models.JSONField(
        default=list,
        help_text="Available duration options in minutes (e.g., [15, 30, 45, 60, 90, 120])"
    )
    
    # Appointment type choices (list of display names only)
    type_choices = models.JSONField(
        default=list,
        help_text="Available appointment types as display names"
    )
    
    # Status choices (list of display names only)
    status_choices = models.JSONField(
        default=list,
        help_text="Available appointment statuses as display names"
    )
    
    # Status colors (dictionary mapping status display names to hex colors)
    status_colors = models.JSONField(
        default=dict,
        help_text="Color mapping for each status (e.g., {'Agendada': '#007bff', 'Confirmada': '#28a745'})"
    )
    
    # Location/place options (list of strings)
    location_options = models.JSONField(
        default=list,
        help_text="Available location/place options"
    )
    
    # Insurance operators (list of display names)
    insurance_operators = models.JSONField(
        default=list,
        help_text="Available insurance operators (convênios) as display names"
    )
    
    # Cancellation reasons (list of display names)
    cancellation_reasons = models.JSONField(
        default=list,
        help_text="Available cancellation reasons as display names"
    )

    # Churn Settings
    churn_threshold_months = models.PositiveIntegerField(
        default=12,
        help_text="Number of months without a visit to consider a patient as 'Churn'"
    )
    
    churn_risk_months = models.PositiveIntegerField(
        default=6,
        help_text="Number of months without a visit to consider a patient 'At Risk'"
    )
    
    # Price per convenio: dict mapping operator name to price string (e.g. {"Unimed": "150.00", "Amil": "120.00"})
    convenio_prices = models.JSONField(
        default=dict,
        help_text="Price per insurance operator: {operator_name: price_string}"
    )
    
    # Working hours
    work_start_time = models.CharField(
        max_length=5, default='08:00',
        help_text="Work start time in HH:MM format"
    )
    work_end_time = models.CharField(
        max_length=5, default='18:00',
        help_text="Work end time in HH:MM format"
    )
    # FullCalendar day convention: 0=Sunday, 1=Monday, ..., 6=Saturday
    work_days = models.JSONField(
        default=list,
        help_text="Working days list using FullCalendar convention (0=Sun,1=Mon,2=Tue,3=Wed,4=Thu,5=Fri,6=Sat)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Appointment Settings"
        verbose_name_plural = "Appointment Settings"
    
    def __str__(self):
        return "Appointment Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'duration_options': [15, 30, 45, 60, 90, 120],
                'type_choices': [
                    'Consulta',
                    'Retorno',
                    'Check-up',
                    'Emergência',
                    'Procedimento',
                    'Terapia',
                    'Outro',
                ],
                'status_choices': [
                    'Agendada',
                    'Confirmada',
                    'Em Andamento',
                    'Concluída',
                    'Cancelada',
                    'Não Compareceu',
                    'Reagendada',
                ],
                'status_colors': {
                    'Agendada': '#ad0202',
                    'Confirmada': '#007bff',
                    'Em Andamento': '#ffc107',
                    'Concluída': '#28a745',
                    'Cancelada': '#dc3545',
                    'Não Compareceu': '#6c757d',
                    'Reagendada': '#17a2b8',
                },
                'location_options': [],
                'insurance_operators': [
                    'Unimed',
                    'Amil',
                    'Bradesco Saúde',
                    'SulAmérica',
                    'NotreDame Intermédica',
                    'Hapvida',
                    'Outro',
                ],
                'cancellation_reasons': [
                    'Paciente solicitou cancelamento',
                    'Paciente não compareceu',
                    'Emergência médica',
                    'Problemas pessoais do paciente',
                    'Reagendamento solicitado',
                    'Problemas técnicos',
                    'Outro motivo',
                ],
                'convenio_prices': {},
            }
        )
        return settings
    
    def get_duration_options(self):
        """Get duration options with formatted labels"""
        return [
            {
                'value': minutes,
                'label': self._format_duration(minutes)
            }
            for minutes in self.duration_options
        ]
    
    def _format_duration(self, minutes):
        """Format duration in minutes to readable string"""
        if minutes < 60:
            return f"{minutes} minutos"
        elif minutes == 60:
            return "1 hora"
        else:
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours} horas"
            else:
                return f"{hours}h {mins}min"


class ConsultationRecord(models.Model):
    """
    Structured consultation record created when a doctor starts an appointment.
    Stores vital signs, anamnesis, physical exam, diagnosis and treatment plan.
    The linked MedicalRecord is created/updated on save/complete.
    """
    appointment = models.OneToOneField(
        'Appointment',
        on_delete=models.CASCADE,
        related_name='consultation_record',
        help_text="Appointment this consultation belongs to"
    )
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.CASCADE,
        related_name='consultation_records',
        help_text="Patient being consulted"
    )
    doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.CASCADE,
        related_name='consultation_records',
        help_text="Doctor conducting the consultation"
    )

    # ── Vital Signs ──────────────────────────────────────────────────────────
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True, help_text="Systolic pressure (mmHg)")
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True, help_text="Diastolic pressure (mmHg)")
    heart_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Heart rate (bpm)")
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Respiratory rate (rpm)")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Temperature (°C)")
    oxygen_saturation = models.PositiveIntegerField(null=True, blank=True, help_text="SpO₂ (%)")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight (kg)")
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height (cm)")

    # ── Anamnesis ────────────────────────────────────────────────────────────
    chief_complaint = models.TextField(blank=True, null=True, help_text="Queixa Principal")
    hda = models.TextField(blank=True, null=True, help_text="História da Doença Atual (HDA)")
    past_history = models.TextField(blank=True, null=True, help_text="Antecedentes pessoais e familiares")
    allergies = models.TextField(blank=True, null=True, help_text="Alergias e reações adversas")
    current_medications = models.TextField(blank=True, null=True, help_text="Medicamentos em uso")
    systems_review = models.TextField(blank=True, null=True, help_text="Revisão de sistemas")

    # ── Physical Exam ────────────────────────────────────────────────────────
    physical_exam = models.TextField(blank=True, null=True, help_text="Exame Físico")

    # ── Diagnosis ────────────────────────────────────────────────────────────
    diagnostic_hypothesis = models.TextField(blank=True, null=True, help_text="Hipótese Diagnóstica")
    cid10_code = models.CharField(max_length=10, blank=True, null=True, help_text="Código CID-10")
    cid10_description = models.CharField(max_length=300, blank=True, null=True, help_text="Descrição CID-10")

    # ── Treatment Plan ───────────────────────────────────────────────────────
    conduct = models.TextField(blank=True, null=True, help_text="Conduta e Plano Terapêutico")
    exam_requests = models.TextField(blank=True, null=True, help_text="Solicitação de Exames e Procedimentos")
    return_instructions = models.TextField(blank=True, null=True, help_text="Orientações de retorno")

    # ── AI / Transcription ───────────────────────────────────────────────────
    transcription = models.TextField(blank=True, null=True, help_text="Real-time transcription from Whisper Server")

    # ── Lifecycle ────────────────────────────────────────────────────────────
    started_at = models.DateTimeField(auto_now_add=True, help_text="When the consultation was started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the consultation was concluded")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consultation Record"
        verbose_name_plural = "Consultation Records"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
        ]

    def __str__(self):
        return f"Consulta: {self.patient.full_name} — {self.appointment.appointment_date}"

    @property
    def bmi(self):
        """Calculate BMI if weight and height are available."""
        if self.weight and self.height and self.height > 0:
            h_m = float(self.height) / 100
            return round(float(self.weight) / (h_m ** 2), 1)
        return None

    def build_medical_record_content(self):
        """Generate structured text for MedicalRecord from this consultation."""
        parts = []
        if self.chief_complaint:
            parts.append(f"QUEIXA PRINCIPAL:\n{self.chief_complaint}")
        if self.hda:
            parts.append(f"HISTÓRIA DA DOENÇA ATUAL:\n{self.hda}")
        if self.allergies:
            parts.append(f"ALERGIAS:\n{self.allergies}")
        if self.current_medications:
            parts.append(f"MEDICAMENTOS EM USO:\n{self.current_medications}")
        if self.past_history:
            parts.append(f"ANTECEDENTES:\n{self.past_history}")
        if self.systems_review:
            parts.append(f"REVISÃO DE SISTEMAS:\n{self.systems_review}")

        vitals = []
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            vitals.append(f"PA: {self.blood_pressure_systolic}/{self.blood_pressure_diastolic} mmHg")
        if self.heart_rate:
            vitals.append(f"FC: {self.heart_rate} bpm")
        if self.respiratory_rate:
            vitals.append(f"FR: {self.respiratory_rate} rpm")
        if self.temperature:
            vitals.append(f"Temp: {self.temperature}°C")
        if self.oxygen_saturation:
            vitals.append(f"SpO₂: {self.oxygen_saturation}%")
        if self.weight:
            vitals.append(f"Peso: {self.weight} kg")
        if self.height:
            vitals.append(f"Altura: {self.height} cm")
        if self.bmi:
            vitals.append(f"IMC: {self.bmi}")
        if vitals:
            parts.append("SINAIS VITAIS:\n" + " | ".join(vitals))

        if self.physical_exam:
            parts.append(f"EXAME FÍSICO:\n{self.physical_exam}")
        if self.diagnostic_hypothesis:
            diag = self.diagnostic_hypothesis
            if self.cid10_code:
                diag += f" (CID-10: {self.cid10_code}"
                if self.cid10_description:
                    diag += f" — {self.cid10_description}"
                diag += ")"
            parts.append(f"HIPÓTESE DIAGNÓSTICA:\n{diag}")
        if self.conduct:
            parts.append(f"CONDUTA:\n{self.conduct}")
        if self.exam_requests:
            parts.append(f"SOLICITAÇÃO DE EXAMES:\n{self.exam_requests}")
        if self.return_instructions:
            parts.append(f"ORIENTAÇÕES DE RETORNO:\n{self.return_instructions}")
        return "\n\n".join(parts)


def patient_file_upload_to(instance, filename):
    """
    Dynamic upload path: clinic_<id>/patient_<id>/<original_filename>
    Works for both local filesystem and cloud storage.
    """
    import os
    from django.utils.text import slugify
    clinic_id = instance.patient.clinic_id or 0
    patient_id = instance.patient_id or 0
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name) or 'file'
    return f'clinic_{clinic_id}/patient_{patient_id}/{safe_name}{ext.lower()}'


class PatientFile(models.Model):
    """
    Files attached to a patient (images, PDFs, or other documents).
    Stores who uploaded the file (doctor) and supports both local and cloud storage.
    """
    FILE_TYPE_CHOICES = [
        ('image', 'Imagem'),
        ('pdf', 'PDF'),
        ('other', 'Outro'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='files',
        help_text="Patient this file belongs to"
    )

    uploaded_by = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_patient_files',
        help_text="Doctor who uploaded this file"
    )

    file = models.FileField(
        upload_to=patient_file_upload_to,
        help_text="The uploaded file (image or PDF)"
    )

    original_name = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded by the user"
    )

    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        default='other',
        help_text="Detected file type"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description or notes about this file"
    )

    created_at = models.DateTimeField(auto_now_add=True, help_text="When the file was uploaded")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patient File"
        verbose_name_plural = "Patient Files"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['file_type']),
        ]

    def __str__(self):
        return f"{self.original_name} — {self.patient.full_name}"

    @property
    def uploaded_by_name(self):
        if self.uploaded_by:
            return self.uploaded_by.full_name
        return "Desconhecido"

    @classmethod
    def detect_file_type(cls, filename):
        """Return 'image', 'pdf', or 'other' based on filename extension."""
        import os
        ext = os.path.splitext(filename)[1].lower()
        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'):
            return 'image'
        if ext == '.pdf':
            return 'pdf'
        return 'other'


class FAQEntry(models.Model):
    """
    Base de conhecimento para dúvidas frequentes (FAQ) no chatbot WhatsApp.
    """
    question = models.CharField(max_length=500, help_text="Pergunta ou título")
    answer = models.TextField(help_text="Resposta da base de conhecimento")
    keywords = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Palavras-chave separadas por vírgula para busca"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Ordem de exibição")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "Base de Conhecimento (FAQ)"
        ordering = ['order', 'question']

    def __str__(self):
        return self.question[:50]


class WhatsAppConversation(models.Model):
    """
    Model to track WhatsApp conversation state for appointment booking and FAQ.
    State machine: channel_choice -> main_menu -> (schedule | faq) -> loop_desire_more -> end
    """
    STATE_CHOICES = [
        ('initial', 'Inicial'),
        ('channel_choice', 'Escolha de Canal (Texto/Ligação)'),
        ('patient_cpf', 'Identificação por CPF'),
        ('patient_register_name', 'Cadastro do paciente - nome'),
        ('patient_register_phone', 'Cadastro do paciente - telefone'),
        ('patient_register_gender', 'Cadastro do paciente - sexo'),
        ('patient_register_birth', 'Cadastro do paciente - data nascimento'),
        ('schedule_payment_type', 'Tipo de pagamento (particular/seguro)'),
        ('schedule_select_insurance', 'Seleção de convênio/seguro'),
        ('schedule_confirm_final', 'Confirmação final do agendamento'),
        ('consult_cpf', 'Consultar/Desmarcar - CPF'),
        ('consult_list', 'Consultar/Desmarcar - lista'),
        ('consult_cancel_select', 'Consultar/Desmarcar - escolher qual desmarcar'),
        ('consult_cancel_confirm', 'Consultar/Desmarcar - confirmar desmarque'),
        ('main_menu', 'Menu Principal'),
        ('schedule_alert', 'Alerta LGPD Agendamento'),
        ('schedule_search_type', 'Tipo de Busca Agendamento'),
        ('schedule_search_name', 'Busca por Nome'),
        ('schedule_search_specialty', 'Busca por Especialidade'),
        ('schedule_search_date', 'Busca por Data/Unidade'),
        ('schedule_select_doctor', 'Escolha do Profissional (lista numerada)'),
        ('schedule_select_date', 'Informar melhor data'),
        ('schedule_list', 'Seleção de Horário/Profissional'),
        ('schedule_confirm', 'Confirmação Agendamento'),
        ('schedule_collecting_patient', 'Dados do Paciente'),
        ('selecting_doctor', 'Selecionando Médico'),
        ('selecting_date', 'Selecionando Data'),
        ('selecting_time', 'Selecionando Horário'),
        ('collecting_patient_info', 'Coletando Informações do Paciente'),
        ('faq_question', 'Dúvida/FAQ'),
        ('faq_resolved', 'Dúvida Resolvida?'),
        ('loop_desire_more', 'Deseja algo mais?'),
        ('completed', 'Concluída'),
        ('cancelled', 'Cancelada'),
        ('ended', 'Encerrada'),
    ]
    
    # WhatsApp user info
    phone_number = models.CharField(
        max_length=20,
        help_text="WhatsApp phone number"
    )
    
    # Conversation state
    state = models.CharField(
        max_length=30,
        choices=STATE_CHOICES,
        default='initial',
        help_text="Current conversation state"
    )
    
    # Selected values
    selected_doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_conversations',
        help_text="Selected doctor"
    )
    
    selected_date = models.DateField(
        null=True,
        blank=True,
        help_text="Selected appointment date"
    )
    
    selected_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Selected appointment time"
    )
    
    # Patient info being collected
    patient_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Patient name from conversation"
    )
    
    patient_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Patient phone number"
    )
    
    # Paciente identificado no início (por CPF) ou criado no cadastro via chat
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_conversations',
        help_text="Patient identified by CPF or registered at chat start"
    )
    
    # Created appointment
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_conversation',
        help_text="Created appointment"
    )
    
    # Contexto da máquina de estados (busca, lista de opções, FAQ, etc.)
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dados do fluxo: search_type, search_results, selected_slot, faq_answer, etc."
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When conversation started")
    updated_at = models.DateTimeField(auto_now=True, help_text="When conversation was last updated")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When conversation was completed")
    
    class Meta:
        verbose_name = "WhatsApp Conversation"
        verbose_name_plural = "WhatsApp Conversations"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['state']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"WhatsApp: {self.phone_number} - {self.get_state_display()}"
    
    def reset(self):
        """Reset conversation to initial state (channel choice)"""
        self.state = 'channel_choice'
        self.selected_doctor = None
        self.selected_date = None
        self.selected_time = None
        self.patient_name = None
        self.patient_phone = None
        self.patient = None
        self.appointment = None
        self.context = {}
        self.save()