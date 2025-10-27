"""
Utility functions for user role management and permissions
"""
from django.contrib.auth.models import User
from dashboard.models import Admin, Doctor, Secretary


def get_user_role(user):
    """
    Determine the role of a user
    Returns: 'admin', 'doctor', 'secretary', or None
    """
    if not user or not user.is_authenticated:
        return None
    
    # Check if user is an admin (has admin_profile)
    if hasattr(user, 'admin_profile'):
        return 'admin'
    
    # Check if user is a doctor
    if hasattr(user, 'doctor_profile'):
        return 'doctor'
    
    # Check if user is a secretary
    if hasattr(user, 'secretary_profile'):
        return 'secretary'
    
    # Legacy support: Check if user is admin (superuser or staff)
    if user.is_superuser or user.is_staff:
        return 'admin'
    
    return None


def get_doctor_for_user(user):
    """
    Get the doctor object for a user
    - If user is admin: returns None (admin can see all their doctors through admin.doctors)
    - If user is doctor: returns their doctor profile
    - If user is secretary: returns their assigned doctor
    """
    if not user or not user.is_authenticated:
        return None
    
    role = get_user_role(user)
    
    if role == 'admin':
        return None  # Admin uses admin.doctors to access their doctors
    elif role == 'doctor':
        return getattr(user, 'doctor_profile', None)
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        if secretary_profile and secretary_profile.doctor:
            return secretary_profile.doctor
        return None
    
    return None


def get_admin_for_user(user):
    """
    Get the admin object for a user
    - If user is admin: returns their admin profile
    - Otherwise: returns None
    """
    if not user or not user.is_authenticated:
        return None
    
    role = get_user_role(user)
    
    if role == 'admin':
        return getattr(user, 'admin_profile', None)
    
    return None


def get_secretaries_for_doctor(doctor):
    """
    Get all secretaries for a specific doctor
    """
    if not doctor:
        return Secretary.objects.none()
    
    return Secretary.objects.filter(doctor=doctor, is_active=True)


def can_access_doctor(user, target_doctor):
    """
    Check if a user can access a specific doctor's data
    - Admins can access doctors they manage (admin.doctors)
    - Doctors can access only their own data
    - Secretaries can access their assigned doctor's data
    """
    if not user or not user.is_authenticated or not target_doctor:
        return False
    
    role = get_user_role(user)
    
    if role == 'admin':
        admin_profile = getattr(user, 'admin_profile', None)
        if admin_profile:
            return admin_profile.doctors.filter(id=target_doctor.id).exists()
        return False
    elif role == 'doctor':
        doctor_profile = getattr(user, 'doctor_profile', None)
        return doctor_profile and doctor_profile.id == target_doctor.id
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        return secretary_profile and secretary_profile.doctor.id == target_doctor.id
    
    return False


def get_accessible_doctors(user):
    """
    Get the list of doctors a user can access
    - Admins: all doctors they manage (admin.doctors)
    - Doctors: only themselves
    - Secretaries: only their assigned doctor
    """
    role = get_user_role(user)
    
    if role == 'admin':
        admin_profile = getattr(user, 'admin_profile', None)
        if admin_profile:
            return admin_profile.doctors.filter(is_active=True)
        return Doctor.objects.none()
    elif role == 'doctor':
        doctor_profile = getattr(user, 'doctor_profile', None)
        if doctor_profile:
            return Doctor.objects.filter(id=doctor_profile.id, is_active=True)
        return Doctor.objects.none()
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        if secretary_profile and secretary_profile.doctor:
            return Doctor.objects.filter(id=secretary_profile.doctor.id, is_active=True)
        return Doctor.objects.none()
    
    return Doctor.objects.none()


def has_access_to_patient(user, patient):
    """
    Check if a user has access to a specific patient
    - Admins can access patients of doctors they manage
    - Doctors can access only their own patients
    - Secretaries can access patients of their assigned doctor
    """
    if not user or not user.is_authenticated or not patient:
        return False
    
    role = get_user_role(user)
    
    if role == 'admin':
        admin_profile = getattr(user, 'admin_profile', None)
        if admin_profile:
            # Check if the patient's doctor is managed by this admin
            return admin_profile.doctors.filter(id=patient.doctor.id).exists()
        return False
    elif role == 'doctor':
        doctor_profile = getattr(user, 'doctor_profile', None)
        return doctor_profile and patient.doctor.id == doctor_profile.id
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        return secretary_profile and patient.doctor.id == secretary_profile.doctor.id
    
    return False


def get_accessible_patients(user):
    """
    Get the list of patients a user can access
    - Admins: patients of doctors they manage
    - Doctors: only their own patients
    - Secretaries: patients of their assigned doctor
    """
    from dashboard.models import Patient
    
    role = get_user_role(user)
    
    if role == 'admin':
        admin_profile = getattr(user, 'admin_profile', None)
        if admin_profile:
            # Get patients of all doctors managed by this admin
            return Patient.objects.filter(doctor__in=admin_profile.doctors.all())
        return Patient.objects.none()
    elif role == 'doctor':
        doctor_profile = getattr(user, 'doctor_profile', None)
        if doctor_profile:
            return Patient.objects.filter(doctor=doctor_profile)
        return Patient.objects.none()
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        if secretary_profile and secretary_profile.doctor:
            return Patient.objects.filter(doctor=secretary_profile.doctor)
        return Patient.objects.none()
    
    return Patient.objects.none()

