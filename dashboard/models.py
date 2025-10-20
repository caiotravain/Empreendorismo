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
        ]
    
    def __str__(self):
        return f"{self.description} - R$ {self.amount} ({self.income_date})"
    
    @property
    def doctor_name(self):
        return self.doctor.full_name
    
    @property
    def formatted_amount(self):
        return f"R$ {self.amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')