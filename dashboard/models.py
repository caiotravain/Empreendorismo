from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator


class Patient(models.Model):
    """
    Patient model to store patient information
    """
    # Link to Doctor (who manages this patient)
    doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.CASCADE,
        related_name='patients',
        null=True,
        blank=True,
        help_text="Doctor who manages this patient"
    )
    
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
            models.Index(fields=['doctor']),
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


class Admin(models.Model):
    """
    Admin model to store admin information
    Admins can manage multiple doctors
    """
    # Link to Django User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        help_text="Django User object for the admin"
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
        help_text="Admin's phone number"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the admin is currently active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this admin profile was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this admin profile was last updated")
    
    class Meta:
        verbose_name = "Admin"
        verbose_name_plural = "Admins"
        ordering = ['user__last_name', 'user__first_name']
        indexes = [
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Admin: {self.user.get_full_name() or self.user.username}"
    
    @property
    def full_name(self):
        return f"{self.user.get_full_name() or self.user.username}"
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def doctors_count(self):
        """Get the number of doctors managed by this admin"""
        return self.doctors.filter(is_active=True).count()
    
    @property
    def active_doctors(self):
        """Get all active doctors managed by this admin"""
        return self.doctors.filter(is_active=True)
    
    def get_doctors(self):
        """Get all doctors (active and inactive) managed by this admin"""
        return self.doctors.all()
    
    def get_active_doctors(self):
        """Get only active doctors"""
        return self.doctors.filter(is_active=True)


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
    
    # Link to Admin (who manages this doctor)
    admin = models.ForeignKey(
        Admin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctors',
        help_text="Admin who manages this doctor"
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
            models.Index(fields=['admin']),
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
        """Get the number of patients for this doctor"""
        return self.patients.filter(is_active=True).count()
    
    @property
    def active_patients(self):
        """Get all active patients for this doctor"""
        return self.patients.filter(is_active=True)
    
    def get_patients(self):
        """Get all patients for this doctor"""
        return self.patients.all()
    
    def get_active_patients(self):
        """Get only active patients"""
        return self.patients.filter(is_active=True)


class Secretary(models.Model):
    """
    Secretary model to store secretary information
    Each secretary works for one doctor
    """
    # Link to Django User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='secretary_profile',
        help_text="Django User object for the secretary"
    )
    
    # Link to Doctor
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='secretaries',
        help_text="Doctor this secretary works for"
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
            models.Index(fields=['doctor']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Secretary: {self.user.get_full_name() or self.user.username} - Dr. {self.doctor.user.get_full_name()}"
    
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


class WhatsAppConversation(models.Model):
    """
    Model to track WhatsApp conversation state for appointment booking
    """
    STATE_CHOICES = [
        ('initial', 'Inicial'),
        ('selecting_doctor', 'Selecionando Médico'),
        ('selecting_date', 'Selecionando Data'),
        ('selecting_time', 'Selecionando Horário'),
        ('collecting_patient_info', 'Coletando Informações do Paciente'),
        ('completed', 'Concluída'),
        ('cancelled', 'Cancelada'),
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
    
    # Created appointment
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_conversation',
        help_text="Created appointment"
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
        """Reset conversation to initial state"""
        self.state = 'initial'
        self.selected_doctor = None
        self.selected_date = None
        self.selected_time = None
        self.patient_name = None
        self.patient_phone = None
        self.appointment = None
        self.save()