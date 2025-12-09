// FullCalendar Integration
let calendar;
let calendarInitialized = false;

// Initialize FullCalendar when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if agenda tab is already active
    const agendaTab = document.getElementById('agenda-tab');
    if (agendaTab && agendaTab.classList.contains('active')) {
        setTimeout(initializeFullCalendar, 100);
    }
});

function initializeFullCalendar() {
    if (calendarInitialized) {
        return;
    }
    
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        return;
    }
    
    calendarInitialized = true;

    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        locale: 'pt-br',
        timeZone: 'local', // Use local timezone - ensures ISO strings are interpreted in local time
        // This makes the time slots and events align perfectly
        firstDay: 1, // Monday
        weekends: false, // Hide weekends
        nowIndicator: true,
        editable: true,
        selectable: true,
        selectMirror: true,
        dayMaxEvents: true,
        height: 550,
        slotMinTime: '06:00:00',
        slotMaxTime: '20:00:00',
        slotDuration: '00:15:00',
        slotLabelFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        },
        allDaySlot: false, // Remove all-day row
        businessHours: {
            daysOfWeek: [1, 2, 3, 4, 5], // Monday - Friday
            startTime: '08:00',
            endTime: '18:00',
        },
        buttonText: {
            today: 'Hoje',
            month: 'Mês',
            week: 'Semana',
        },
        events: function(info, successCallback, failureCallback) {
            // Load appointments for the current view
            loadAppointmentsForCalendar(info.start, info.end, successCallback, failureCallback);
        },
        eventContent: function(arg) {
            // Custom event content to show dollar symbol for particular appointments
            const paymentType = arg.event.extendedProps.paymentType;
            const patientName = arg.event.title;
            
            if (paymentType === 'Particular') {
                return {
                    html: `${patientName} <span class="particular-dollar">$</span>`
                };
            } else {
                return {
                    html: patientName
                };
            }
        },
        eventDidMount: function(info) {
            // Add appointment type as description below the event
            const appointmentType = info.event.extendedProps.appointmentType;
            const status = info.event.extendedProps.status;
            
            // Add status data attribute for CSS targeting
            info.el.setAttribute('data-status', status);
            
            // Map appointment types to Portuguese
            const typeMap = {
                'consultation': 'Consulta',
                'follow_up': 'Retorno',
                'checkup': 'Check-up',
                'emergency': 'Emergência',
                'procedure': 'Procedimento',
                'therapy': 'Terapia',
                'other': 'Outro'
            };
            
            const typeDisplay = typeMap[appointmentType] || appointmentType;
            
            // Add the appointment type as a small description below the event
            const description = document.createElement('div');
            description.className = 'fc-event-description';
            description.textContent = typeDisplay;
            
            info.el.appendChild(description);
        },
        eventClick: function(info) {
            // Handle event click - show appointment details
            showAppointmentDetailsFromCalendar(info.event);
        },
        select: function(info) {
            // Handle date/time selection for new appointments
            showNewAppointmentModalForTime(info.start, info.end);
        },
        eventDrop: function(info) {
            // Check for conflicts before allowing the drop
            const newStart = info.event.start;
            const newEnd = info.event.end;
            const appointmentId = info.event.id;
            
            // Get all other events on the same day
            const events = calendar.getEvents();
            const conflictingEvents = events.filter(event => {
                return event.id !== appointmentId && 
                       event.start.toDateString() === newStart.toDateString() &&
                       ((newStart < event.end && newEnd > event.start));
            });
            
            if (conflictingEvents.length > 0) {
                // Revert the event to its original position
                info.revert();
                return;
            }
            
            // If no conflicts, proceed with the update
            updateAppointmentTime(info.event);
        },
        eventResize: function(info) {
            // Check for conflicts before allowing the resize
            const newStart = info.event.start;
            const newEnd = info.event.end;
            const appointmentId = info.event.id;
            
            // Get all other events on the same day
            const events = calendar.getEvents();
            const conflictingEvents = events.filter(event => {
                return event.id !== appointmentId && 
                       event.start.toDateString() === newStart.toDateString() &&
                       ((newStart < event.end && newEnd > event.start));
            });
            
            if (conflictingEvents.length > 0) {
                // Revert the event to its original size
                info.revert();
                return;
            }
            
            // If no conflicts, proceed with the update
            updateAppointmentDuration(info.event);
        }
    });

    calendar.render();
}

function loadAppointmentsForCalendar(start, end, successCallback, failureCallback) {
    // Get both start and end dates to support month view
    const startDate = start.toISOString().split('T')[0];
    const endDate = end.toISOString().split('T')[0];
    
    // Use start and end parameters to support both week and month views
    fetch(`/dashboard/api/week-appointments/?start=${startDate}&end=${endDate}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const events = data.appointments.map(appointment => {
                    // Create Date objects that represent the exact time shown in the left column
                    // The time slots show local time, so we create dates in local time
                    const startDate = createDateFromComponents(appointment.appointment_date, appointment.appointment_time);
                    const endDate = addMinutesToDate(startDate, appointment.duration_minutes);
                    
                    return {
                        id: appointment.id,
                        title: appointment.patient_name,
                        start: startDate, // Date object in local time - matches left column times
                        end: endDate, // Date object in local time
                        backgroundColor: getEventColor(appointment.status),
                        borderColor: getEventColor(appointment.status),
                        extendedProps: {
                            patientId: appointment.patient_id,
                            patientName: appointment.patient_name,
                            doctorName: appointment.doctor_name,
                            appointmentType: appointment.appointment_type,
                            paymentType: appointment.payment_type,
                            status: appointment.status,
                            value: appointment.value,
                            reason: appointment.reason,
                            notes: appointment.notes,
                            location: appointment.location
                        }
                    };
                });
                successCallback(events);
            } else {
                failureCallback(data.error);
            }
        })
        .catch(error => {
            failureCallback(error);
        });
}

/**
 * Create a Date object from date and time components
 * This creates the date in the browser's local timezone
 * The time will match exactly what's shown in the left column time slots
 */
function createDateFromComponents(dateStr, timeStr) {
    // Parse date: YYYY-MM-DD
    const [year, month, day] = dateStr.split('-').map(Number);
    
    // Parse time: HH:MM
    const [hours, minutes] = timeStr.split(':').map(Number);
    
    // Create Date object using local time components
    // new Date(year, month, day, hours, minutes) creates date in local timezone
    // This matches the time slots which also show local time
    return new Date(year, month - 1, day, hours || 0, minutes || 0, 0, 0);
}

/**
 * Add minutes to a Date object
 */
function addMinutesToDate(date, minutes) {
    return new Date(date.getTime() + (minutes * 60000));
}

function getEventColor(status) {
    const colors = {
        'scheduled': 'rgb(173 2 2)',    // Custom blue for non-confirmed
        'confirmed': '#007bff',     // Primary blue
        'in_progress': '#ffc107',   // Warning yellow
        'completed': '#28a745',     // Success green
        'cancelled': '#dc3545',     // Danger red
        'no_show': '#6c757d'        // Secondary gray
    };
    return colors[status] || '#6c757d';
}

function showAppointmentDetailsFromCalendar(event) {
    const props = event.extendedProps;
    
    // Populate the appointment details modal
    const patientNameElement = document.getElementById('modal-patient-name');
    if (props.paymentType === 'Particular') {
        patientNameElement.innerHTML = `${props.patientName} <span class="badge bg-warning text-dark ms-1">$</span>`;
    } else {
        patientNameElement.textContent = props.patientName;
    }
    document.getElementById('modal-doctor-name').textContent = props.doctorName;
    document.getElementById('modal-appointment-date').textContent = event.start.toLocaleDateString('pt-BR');
    document.getElementById('modal-appointment-time').textContent = event.start.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
    document.getElementById('modal-appointment-duration').textContent = Math.round((event.end - event.start) / (1000 * 60)) + ' minutos';
    document.getElementById('modal-appointment-type').textContent = props.appointmentType;
    document.getElementById('modal-payment-type').textContent = props.paymentType || '-';
    document.getElementById('modal-appointment-value').textContent = props.value ? `R$ ${props.value}` : '-';
    document.getElementById('modal-appointment-location').textContent = props.location || 'Consultório';
    document.getElementById('modal-appointment-reason').textContent = props.reason || 'Consulta médica';
    document.getElementById('modal-appointment-notes').textContent = props.notes || 'Nenhuma observação';
    
    // Update status badge
    const statusBadge = document.getElementById('modal-status-badge');
    statusBadge.textContent = getStatusDisplay(props.status);
    statusBadge.className = 'badge ' + getStatusBadgeClass(props.status);
    
    // Show/hide action buttons based on status
    const confirmBtn = document.getElementById('confirm-attendance-btn');
    const completeBtn = document.getElementById('complete-appointment-btn');
    const cancelBtn = document.getElementById('cancel-appointment-btn');
    
    // Reset button visibility
    confirmBtn.style.display = 'none';
    completeBtn.style.display = 'none';
    cancelBtn.style.display = 'none';
    
    // Show appropriate buttons based on status
    if (props.status === 'scheduled') {
        confirmBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'inline-block';
    } else if (props.status === 'confirmed') {
        completeBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'inline-block';
    } else if (props.status === 'completed') {
        // No action buttons for completed appointments
    } else if (props.status === 'cancelled') {
        // No action buttons for cancelled appointments
    }
    
    // Set up button click handlers
    confirmBtn.onclick = () => confirmAppointmentAttendance(event.id);
    completeBtn.onclick = () => completeAppointment(event.id);
    cancelBtn.onclick = () => cancelAppointment(event.id);
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('appointmentDetailsModal'));
    modal.show();
}

function getStatusDisplay(status) {
    const statusMap = {
        'scheduled': 'Agendada',
        'confirmed': 'Confirmada',
        'in_progress': 'Em Andamento',
        'completed': 'Concluída',
        'cancelled': 'Cancelada',
        'no_show': 'Não Compareceu'
    };
    return statusMap[status] || status;
}

function getStatusBadgeClass(status) {
    const badgeClasses = {
        'scheduled': 'bg-info',
        'confirmed': 'bg-primary',
        'in_progress': 'bg-warning',
        'completed': 'bg-success',
        'cancelled': 'bg-danger',
        'no_show': 'bg-secondary'
    };
    return badgeClasses[status] || 'bg-secondary';
}

function confirmAppointmentAttendance(appointmentId) {
    fetch('/dashboard/api/appointments/confirm-attendance/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
            modal.hide();
            refreshCalendar();
            // Refresh agenda stats after confirming attendance
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao confirmar presença: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showNotification('Erro ao confirmar presença', 'error');
    });
}

function completeAppointment(appointmentId) {
    fetch('/dashboard/api/appointments/complete/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
            modal.hide();
            refreshCalendar();
            // Refresh agenda stats after completing appointment
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao concluir consulta: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showNotification('Erro ao concluir consulta', 'error');
    });
}

function cancelAppointment(appointmentId) {
    const cancellationReason = prompt('Digite o motivo do cancelamento:');
    if (cancellationReason === null) {
        return; // User cancelled
    }
    
    fetch('/dashboard/api/appointments/cancel/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}&cancellation_reason=${encodeURIComponent(cancellationReason || 'Cancelado pelo usuário')}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('appointmentDetailsModal'));
            modal.hide();
            refreshCalendar();
            // Refresh agenda stats after cancelling appointment
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao cancelar consulta: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showNotification('Erro ao cancelar consulta', 'error');
    });
}

function showNewAppointmentModalForTime(start, end) {
    // Pre-fill the appointment modal with selected time
    const startDateObj = new Date(start);
    const startDate = startDateObj.getFullYear() + '-' + 
                     String(startDateObj.getMonth() + 1).padStart(2, '0') + '-' + 
                     String(startDateObj.getDate()).padStart(2, '0');
    const startTime = String(startDateObj.getHours()).padStart(2, '0') + ':' + 
                     String(startDateObj.getMinutes()).padStart(2, '0');
    
    // Set the date and time in the form
    document.getElementById('appointment_date').value = startDate;
    document.getElementById('appointment_time').value = startTime;
    
    // Calculate duration and set it
    const duration = Math.round((end - start) / (1000 * 60)); // in minutes
    document.getElementById('duration_minutes').value = duration;
    
    // Show the modal
    showNewAppointmentModal();
}

function updateAppointmentTime(event) {
    const appointmentId = event.id;
    
    // Get the local date and time properly
    const startDate = new Date(event.start);
    const newDate = startDate.getFullYear() + '-' + 
                   String(startDate.getMonth() + 1).padStart(2, '0') + '-' + 
                   String(startDate.getDate()).padStart(2, '0');
    const newTime = String(startDate.getHours()).padStart(2, '0') + ':' + 
                   String(startDate.getMinutes()).padStart(2, '0');
    
    // Send update to server
    fetch('/dashboard/api/appointments/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}&appointment_date=${newDate}&appointment_time=${newTime}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Consulta atualizada com sucesso!', 'success');
            // Refresh agenda stats after updating appointment
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao atualizar consulta: ' + data.error, 'error');
            // Revert the event position
            event.revert();
        }
    })
    .catch(error => {
        showNotification('Erro ao atualizar consulta', 'error');
        event.revert();
    });
}

function updateAppointmentDuration(event) {
    const appointmentId = event.id;
    const duration = Math.round((event.end - event.start) / (1000 * 60)); // in minutes
    
    // Send update to server
    fetch('/dashboard/api/appointments/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `appointment_id=${appointmentId}&duration_minutes=${duration}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Duração da consulta atualizada com sucesso!', 'success');
            // Refresh agenda stats after updating appointment duration
            if (typeof refreshAgendaStats === 'function') {
                refreshAgendaStats();
            }
        } else {
            showNotification('Erro ao atualizar duração: ' + data.error, 'error');
            // Revert the event
            event.revert();
        }
    })
    .catch(error => {
        showNotification('Erro ao atualizar duração', 'error');
        event.revert();
    });
}

function refreshCalendar() {
    if (calendar) {
        calendar.refetchEvents();
    }
}

// Override the existing showNewAppointmentModal to refresh calendar after creation
const originalShowNewAppointmentModal = showNewAppointmentModal;
showNewAppointmentModal = function() {
    originalShowNewAppointmentModal();
    
    // Add event listener to refresh calendar when modal is closed
    const appointmentModal = document.getElementById('appointmentModal');
    if (appointmentModal) {
        appointmentModal.addEventListener('hidden.bs.modal', function() {
            refreshCalendar();
        });
    }
};
