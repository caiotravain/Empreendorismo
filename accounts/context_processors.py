"""
Context processors for user role and permissions
"""


def user_role(request):
    """
    Add user role information to template context.
    is_admin is True when the user is a clinic admin (doctor with is_clinic_admin=True).
    is_doctor is True for any user with a doctor profile (including clinic admins).
    """
    from .utils import get_user_role, get_doctor_for_user, get_accessible_doctors, get_clinic_for_user

    if not request.user or not request.user.is_authenticated:
        return {
            'user_role': None,
            'user_doctor': None,
            'user_clinic': None,
            'accessible_doctors': [],
            'selected_doctor_id': None,
            'is_admin': False,
            'is_doctor': False,
            'is_secretary': False,
        }

    role = get_user_role(request.user)
    doctor = get_doctor_for_user(request.user)
    accessible_doctors = list(get_accessible_doctors(request.user))
    user_clinic = get_clinic_for_user(request.user)

    # Get selected doctor ID from session (for clinic admins)
    selected_doctor_id = request.session.get('selected_doctor_id') if hasattr(request, 'session') else None

    return {
        'user_role': role,
        'user_doctor': doctor,
        'user_clinic': user_clinic,
        'accessible_doctors': accessible_doctors,
        'selected_doctor_id': selected_doctor_id,
        'is_admin': role == 'clinic_admin',
        'is_doctor': role in ('doctor', 'clinic_admin'),
        'is_secretary': role == 'secretary',
    }
