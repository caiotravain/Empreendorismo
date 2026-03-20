"""
Utility functions for user role management and permissions
"""
from django.contrib.auth.models import User
from dashboard.models import Doctor, Secretary


def get_user_role(user):
    """
    Determine the primary role of a user.
    Returns: 'clinic_admin', 'doctor', 'secretary', or None

    A user with is_clinic_admin=True on their Doctor profile is a clinic admin.
    A clinic admin is also a doctor — both flags can be True simultaneously.
    """
    if not user or not user.is_authenticated:
        return None

    doctor_profile = getattr(user, 'doctor_profile', None)
    if doctor_profile:
        if doctor_profile.is_clinic_admin:
            return 'clinic_admin'
        return 'doctor'

    if hasattr(user, 'secretary_profile'):
        return 'secretary'

    # Legacy support: Django superuser/staff treated as clinic admin
    if user.is_superuser or user.is_staff:
        return 'clinic_admin'

    return None


def is_clinic_admin(user):
    """Return True if the user is a clinic admin (doctor with is_clinic_admin=True)."""
    if not user or not user.is_authenticated:
        return False
    doctor_profile = getattr(user, 'doctor_profile', None)
    if doctor_profile and doctor_profile.is_clinic_admin:
        return True
    return user.is_superuser or user.is_staff


def get_doctor_for_user(user):
    """
    Get the Doctor object for a user.
    - Clinic admins: return their own doctor_profile (they are also doctors)
    - Doctors: return their doctor profile
    - Secretaries: return first active doctor they work for
    """
    if not user or not user.is_authenticated:
        return None

    role = get_user_role(user)

    if role in ('clinic_admin', 'doctor'):
        return getattr(user, 'doctor_profile', None)
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        if secretary_profile and secretary_profile.doctors.exists():
            return secretary_profile.doctors.filter(is_active=True).first()
        return None

    return None


def get_clinic_for_user(user):
    """
    Get the Clinic object for a user.
    Returns the clinic of the user's doctor or secretary profile.
    """
    if not user or not user.is_authenticated:
        return None

    doctor_profile = getattr(user, 'doctor_profile', None)
    if doctor_profile:
        return doctor_profile.clinic

    secretary_profile = getattr(user, 'secretary_profile', None)
    if secretary_profile:
        return secretary_profile.clinic

    return None


def get_secretaries_for_doctor(doctor):
    """Get all active secretaries for a specific doctor."""
    if not doctor:
        return Secretary.objects.none()
    return Secretary.objects.filter(doctors=doctor, is_active=True)


def can_access_doctor(user, target_doctor):
    """
    Check if a user can access a specific doctor's data.
    - Clinic admins can access all doctors in the same clinic
    - Doctors can access only their own data
    - Secretaries can access their assigned doctors
    """
    if not user or not user.is_authenticated or not target_doctor:
        return False

    role = get_user_role(user)

    if role == 'clinic_admin':
        doctor_profile = getattr(user, 'doctor_profile', None)
        if doctor_profile and doctor_profile.clinic:
            return target_doctor.clinic_id == doctor_profile.clinic_id
        return False
    elif role == 'doctor':
        doctor_profile = getattr(user, 'doctor_profile', None)
        return doctor_profile and doctor_profile.id == target_doctor.id
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        return secretary_profile and secretary_profile.doctors.filter(id=target_doctor.id).exists()

    return False


def get_accessible_doctors(user):
    """
    Get the list of doctors a user can access.
    - Clinic admins: all active doctors in their clinic
    - Doctors: only themselves
    - Secretaries: their assigned doctors
    """
    role = get_user_role(user)

    if role == 'clinic_admin':
        doctor_profile = getattr(user, 'doctor_profile', None)
        if doctor_profile and doctor_profile.clinic:
            return doctor_profile.clinic.doctors.filter(is_active=True)
        return Doctor.objects.none()
    elif role == 'doctor':
        doctor_profile = getattr(user, 'doctor_profile', None)
        if doctor_profile:
            return Doctor.objects.filter(id=doctor_profile.id, is_active=True)
        return Doctor.objects.none()
    elif role == 'secretary':
        secretary_profile = getattr(user, 'secretary_profile', None)
        if secretary_profile:
            return secretary_profile.doctors.filter(is_active=True)
        return Doctor.objects.none()

    return Doctor.objects.none()


def has_access_to_patient(user, patient):
    """
    Check if a user has access to a specific patient.
    Patients are shared within a clinic, so anyone in the same clinic can access them.
    """
    if not user or not user.is_authenticated or not patient:
        return False

    user_clinic = get_clinic_for_user(user)
    if not user_clinic or not patient.clinic:
        return False

    return user_clinic.id == patient.clinic_id


def get_accessible_patients(user):
    """
    Get the list of patients a user can access.
    All users in the same clinic share access to all clinic patients.
    """
    from dashboard.models import Patient

    user_clinic = get_clinic_for_user(user)
    if user_clinic:
        return Patient.objects.filter(clinic=user_clinic)

    return Patient.objects.none()
