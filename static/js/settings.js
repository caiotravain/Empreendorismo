// Settings JavaScript for Appointment Configuration

let appointmentSettings = null;

// Load settings when settings tab is shown
function loadSettings() {
    fetch('/dashboard/api/appointment-settings/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                appointmentSettings = data.settings;
                // Normalize old format to new format if needed
                if (appointmentSettings.type_choices && appointmentSettings.type_choices.length > 0) {
                    if (Array.isArray(appointmentSettings.type_choices[0]) && appointmentSettings.type_choices[0].length >= 2) {
                        // Old format: convert to new format
                        appointmentSettings.type_choices = appointmentSettings.type_choices.map(c => c[1]);
                    }
                }
                if (appointmentSettings.status_choices && appointmentSettings.status_choices.length > 0) {
                    if (Array.isArray(appointmentSettings.status_choices[0]) && appointmentSettings.status_choices[0].length >= 2) {
                        // Old format: convert to new format
                        appointmentSettings.status_choices = appointmentSettings.status_choices.map(c => c[1]);
                    }
                }
                // Initialize status_colors if not present
                if (!appointmentSettings.status_colors) {
                    appointmentSettings.status_colors = {};
                }
                // Initialize insurance_operators if not present
                if (!appointmentSettings.insurance_operators) {
                    appointmentSettings.insurance_operators = [];
                }
                // Initialize cancellation_reasons if not present
                if (!appointmentSettings.cancellation_reasons) {
                    appointmentSettings.cancellation_reasons = [];
                }
                renderSettings();
                // Also update appointment modal with these settings
                updateAppointmentModalWithSettings();
                // Refresh calendar if it exists to apply new colors
                if (typeof calendar !== 'undefined' && calendar) {
                    calendar.refetchEvents();
                }
            } else {
                showNotification('Erro ao carregar configurações: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading settings:', error);
            showNotification('Erro ao carregar configurações', 'error');
        });
}

// Render settings in the settings tab
function renderSettings() {
    if (!appointmentSettings) return;
    
    // Render duration options
    renderDurationOptions();
    
    // Render type choices
    renderTypeChoices();
    
    // Render status choices
    renderStatusChoices();
    
    // Render location options
    renderLocationOptions();
    
    // Render insurance operators
    renderInsuranceOperators();
    
    // Render cancellation reasons
    renderCancellationReasons();
}

// Render duration options
function renderDurationOptions() {
    const container = document.getElementById('duration-options-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    appointmentSettings.duration_options.forEach((minutes, index) => {
        const div = document.createElement('div');
        div.className = 'settings-input-group';
        div.innerHTML = `
            <input type="number" class="form-control" value="${minutes}" min="1" step="1" 
                   onchange="updateDurationOption(${index}, this.value)" placeholder="Duração em minutos">
            <span class="input-badge">minutos</span>
            <button type="button" class="delete-btn" onclick="removeDurationOption(${index})" title="Remover">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

// Render type choices (now just display names)
function renderTypeChoices() {
    const container = document.getElementById('type-options-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Normalize: handle both old format [value, label] and new format (string)
    const normalizedChoices = appointmentSettings.type_choices.map(choice => {
        if (Array.isArray(choice) && choice.length >= 2) {
            return choice[1]; // Use label from old format
        }
        return String(choice); // New format or already string
    });
    
    normalizedChoices.forEach((displayName, index) => {
        const div = document.createElement('div');
        div.className = 'settings-input-group';
        div.innerHTML = `
            <input type="text" class="form-control" value="${displayName}" 
                   placeholder="Nome do tipo (ex: Consulta)" 
                   onchange="updateTypeChoice(${index}, this.value)">
            <button type="button" class="delete-btn" onclick="removeTypeChoice(${index})" title="Remover">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
    
    // Update the settings object to use normalized format
    appointmentSettings.type_choices = normalizedChoices;
}

// Render status choices (now just display names with colors)
function renderStatusChoices() {
    const container = document.getElementById('status-options-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Initialize status_colors if it doesn't exist
    if (!appointmentSettings.status_colors) {
        appointmentSettings.status_colors = {};
    }
    
    // Normalize: handle both old format [value, label] and new format (string)
    const normalizedChoices = appointmentSettings.status_choices.map(choice => {
        if (Array.isArray(choice) && choice.length >= 2) {
            return choice[1]; // Use label from old format
        }
        return String(choice); // New format or already string
    });
    
    normalizedChoices.forEach((displayName, index) => {
        // Get color for this status, or use default
        const defaultColors = {
            'Agendada': '#ad0202',
            'Confirmada': '#007bff',
            'Em Andamento': '#ffc107',
            'Concluída': '#28a745',
            'Cancelada': '#dc3545',
            'Não Compareceu': '#6c757d',
            'Reagendada': '#17a2b8',
        };
        const currentColor = appointmentSettings.status_colors[displayName] || defaultColors[displayName] || '#6c757d';
        
        const div = document.createElement('div');
        div.className = 'settings-input-group status-input-group';
        div.innerHTML = `
            <input type="text" class="form-control" value="${displayName}" 
                   placeholder="Nome do status (ex: Agendada)" 
                   onchange="updateStatusChoice(${index}, this.value)">
            <div class="color-picker-wrapper">
                <input type="color" class="form-control form-control-color" 
                       value="${currentColor}" 
                       title="Cor do status na agenda"
                       onchange="updateStatusColor('${displayName}', this.value)">
                <span class="color-preview" style="background-color: ${currentColor};"></span>
            </div>
            <button type="button" class="delete-btn" onclick="removeStatusChoice(${index})" title="Remover">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
    
    // Update the settings object to use normalized format
    appointmentSettings.status_choices = normalizedChoices;
}

// Render location options
function renderLocationOptions() {
    const container = document.getElementById('location-options-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    appointmentSettings.location_options.forEach((location, index) => {
        const div = document.createElement('div');
        div.className = 'settings-input-group';
        div.innerHTML = `
            <input type="text" class="form-control" value="${location}" 
                   placeholder="Nome do local" 
                   onchange="updateLocationOption(${index}, this.value)">
            <button type="button" class="delete-btn" onclick="removeLocationOption(${index})" title="Remover">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

// Render insurance operators
function renderInsuranceOperators() {
    const container = document.getElementById('insurance-operators-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Initialize insurance_operators if it doesn't exist
    if (!appointmentSettings.insurance_operators) {
        appointmentSettings.insurance_operators = [];
    }
    
    appointmentSettings.insurance_operators.forEach((operator, index) => {
        const div = document.createElement('div');
        div.className = 'settings-input-group';
        div.innerHTML = `
            <input type="text" class="form-control" value="${operator}" 
                   placeholder="Nome do convênio (ex: Unimed)" 
                   onchange="updateInsuranceOperator(${index}, this.value)">
            <button type="button" class="delete-btn" onclick="removeInsuranceOperator(${index})" title="Remover">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

// Add insurance operator
function addInsuranceOperator() {
    if (!appointmentSettings) return;
    if (!appointmentSettings.insurance_operators) {
        appointmentSettings.insurance_operators = [];
    }
    appointmentSettings.insurance_operators.push('Novo Convênio');
    renderInsuranceOperators();
}

// Remove insurance operator
function removeInsuranceOperator(index) {
    if (!appointmentSettings) return;
    appointmentSettings.insurance_operators.splice(index, 1);
    renderInsuranceOperators();
}

// Update insurance operator
function updateInsuranceOperator(index, value) {
    if (!appointmentSettings) return;
    appointmentSettings.insurance_operators[index] = value;
}

// Render cancellation reasons
function renderCancellationReasons() {
    const container = document.getElementById('cancellation-reasons-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Initialize cancellation_reasons if it doesn't exist
    if (!appointmentSettings.cancellation_reasons) {
        appointmentSettings.cancellation_reasons = [];
    }
    
    appointmentSettings.cancellation_reasons.forEach((reason, index) => {
        const div = document.createElement('div');
        div.className = 'settings-input-group';
        div.innerHTML = `
            <input type="text" class="form-control" value="${reason}" 
                   placeholder="Motivo de cancelamento (ex: Paciente solicitou cancelamento)" 
                   onchange="updateCancellationReason(${index}, this.value)">
            <button type="button" class="delete-btn" onclick="removeCancellationReason(${index})" title="Remover">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

// Add cancellation reason
function addCancellationReason() {
    if (!appointmentSettings) return;
    if (!appointmentSettings.cancellation_reasons) {
        appointmentSettings.cancellation_reasons = [];
    }
    appointmentSettings.cancellation_reasons.push('Novo Motivo');
    renderCancellationReasons();
}

// Remove cancellation reason
function removeCancellationReason(index) {
    if (!appointmentSettings) return;
    appointmentSettings.cancellation_reasons.splice(index, 1);
    renderCancellationReasons();
}

// Update cancellation reason
function updateCancellationReason(index, value) {
    if (!appointmentSettings) return;
    appointmentSettings.cancellation_reasons[index] = value;
}

// Add duration option
function addDurationOption() {
    if (!appointmentSettings) return;
    appointmentSettings.duration_options.push(30);
    renderDurationOptions();
}

// Remove duration option
function removeDurationOption(index) {
    if (!appointmentSettings) return;
    appointmentSettings.duration_options.splice(index, 1);
    renderDurationOptions();
}

// Update duration option
function updateDurationOption(index, value) {
    if (!appointmentSettings) return;
    const minutes = parseInt(value);
    if (!isNaN(minutes) && minutes > 0) {
        appointmentSettings.duration_options[index] = minutes;
        // Sort and remove duplicates
        appointmentSettings.duration_options = [...new Set(appointmentSettings.duration_options)].sort((a, b) => a - b);
        renderDurationOptions();
    }
}

// Add type choice
function addTypeOption() {
    if (!appointmentSettings) return;
    appointmentSettings.type_choices.push('Novo Tipo');
    renderTypeChoices();
}

// Remove type choice
function removeTypeChoice(index) {
    if (!appointmentSettings) return;
    appointmentSettings.type_choices.splice(index, 1);
    renderTypeChoices();
}

// Update type choice
function updateTypeChoice(index, value) {
    if (!appointmentSettings) return;
    appointmentSettings.type_choices[index] = value;
}

// Add status choice
function addStatusOption() {
    if (!appointmentSettings) return;
    if (!appointmentSettings.status_colors) {
        appointmentSettings.status_colors = {};
    }
    const newStatus = 'Novo Status';
    appointmentSettings.status_choices.push(newStatus);
    appointmentSettings.status_colors[newStatus] = '#6c757d'; // Default gray color
    renderStatusChoices();
}

// Remove status choice
function removeStatusChoice(index) {
    if (!appointmentSettings) return;
    appointmentSettings.status_choices.splice(index, 1);
    renderStatusChoices();
}

// Update status choice
function updateStatusChoice(index, value) {
    if (!appointmentSettings) return;
    const oldName = appointmentSettings.status_choices[index];
    const newName = value;
    
    // If status name changed, update the color mapping
    if (oldName !== newName && appointmentSettings.status_colors && appointmentSettings.status_colors[oldName]) {
        appointmentSettings.status_colors[newName] = appointmentSettings.status_colors[oldName];
        delete appointmentSettings.status_colors[oldName];
    }
    
    appointmentSettings.status_choices[index] = newName;
    // Re-render to update color picker references
    renderStatusChoices();
}

// Update status color
function updateStatusColor(statusName, color) {
    if (!appointmentSettings) return;
    if (!appointmentSettings.status_colors) {
        appointmentSettings.status_colors = {};
    }
    appointmentSettings.status_colors[statusName] = color;
    
    // Update the color preview in the UI
    const container = document.getElementById('status-options-container');
    if (container) {
        const statusGroups = container.querySelectorAll('.status-input-group');
        statusGroups.forEach(group => {
            const nameInput = group.querySelector('input[type="text"]');
            if (nameInput && nameInput.value === statusName) {
                const preview = group.querySelector('.color-preview');
                if (preview) {
                    preview.style.backgroundColor = color;
                }
            }
        });
    }
}

// Add location option
function addLocationOption() {
    if (!appointmentSettings) return;
    appointmentSettings.location_options.push('');
    renderLocationOptions();
}

// Remove location option
function removeLocationOption(index) {
    if (!appointmentSettings) return;
    appointmentSettings.location_options.splice(index, 1);
    renderLocationOptions();
}

// Update location option
function updateLocationOption(index, value) {
    if (!appointmentSettings) return;
    appointmentSettings.location_options[index] = value;
}

// Save settings
function saveSettings() {
    if (!appointmentSettings) return;
    
    // Validate duration options
    const validDurations = appointmentSettings.duration_options.filter(d => d > 0);
    if (validDurations.length === 0) {
        showNotification('Adicione pelo menos uma opção de duração', 'error');
        return;
    }
    
    // Validate type choices (now just display names)
    const validTypes = appointmentSettings.type_choices.filter(t => {
        if (Array.isArray(t)) {
            return t.length >= 2 && t[1] && t[1].trim();
        }
        return t && String(t).trim();
    });
    if (validTypes.length === 0) {
        showNotification('Adicione pelo menos um tipo de consulta', 'error');
        return;
    }
    
    // Validate status choices (now just display names)
    const validStatuses = appointmentSettings.status_choices.filter(s => {
        if (Array.isArray(s)) {
            return s.length >= 2 && s[1] && s[1].trim();
        }
        return s && String(s).trim();
    });
    if (validStatuses.length === 0) {
        showNotification('Adicione pelo menos um status', 'error');
        return;
    }
    
    // Normalize type and status choices to just display names
    const normalizedTypes = validTypes.map(t => {
        if (Array.isArray(t) && t.length >= 2) {
            return t[1].trim(); // Use label from old format
        }
        return String(t).trim(); // New format
    });
    
    const normalizedStatuses = validStatuses.map(s => {
        if (Array.isArray(s) && s.length >= 2) {
            return s[1].trim(); // Use label from old format
        }
        return String(s).trim(); // New format
    });
    
    // Validate insurance operators
    const validOperators = (appointmentSettings.insurance_operators || []).filter(o => {
        return o && String(o).trim();
    });
    
    // Validate cancellation reasons
    const validCancellationReasons = (appointmentSettings.cancellation_reasons || []).filter(r => {
        return r && String(r).trim();
    });
    
    // Prepare data
    const data = {
        duration_options: validDurations,
        type_choices: normalizedTypes,
        status_choices: normalizedStatuses,
        status_colors: appointmentSettings.status_colors || {},
        location_options: appointmentSettings.location_options.filter(l => l.trim()),
        insurance_operators: validOperators.map(o => String(o).trim()),
        cancellation_reasons: validCancellationReasons.map(r => String(r).trim())
    };
    
    // Send to server
    fetch('/dashboard/api/appointment-settings/save/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Configurações salvas com sucesso!', 'success');
            // Reload settings to get updated data
            loadSettings();
            // Update appointment modal
            updateAppointmentModalWithSettings();
        } else {
            showNotification('Erro ao salvar: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        showNotification('Erro ao salvar configurações', 'error');
    });
}

// Reset settings to defaults
function resetSettings() {
    if (confirm('Tem certeza que deseja restaurar as configurações padrão? Isso irá sobrescrever todas as alterações não salvas.')) {
        appointmentSettings = {
            duration_options: [15, 30, 45, 60, 90, 120],
            type_choices: [
                'Consulta',
                'Retorno',
                'Check-up',
                'Emergência',
                'Procedimento',
                'Terapia',
                'Outro',
            ],
            status_choices: [
                'Agendada',
                'Confirmada',
                'Em Andamento',
                'Concluída',
                'Cancelada',
                'Não Compareceu',
                'Reagendada',
            ],
            status_colors: {
                'Agendada': '#ad0202',
                'Confirmada': '#007bff',
                'Em Andamento': '#ffc107',
                'Concluída': '#28a745',
                'Cancelada': '#dc3545',
                'Não Compareceu': '#6c757d',
                'Reagendada': '#17a2b8',
            },
            location_options: [],
            insurance_operators: [
                'Unimed',
                'Amil',
                'Bradesco Saúde',
                'SulAmérica',
                'NotreDame Intermédica',
                'Hapvida',
                'Outro',
            ],
            cancellation_reasons: [
                'Paciente solicitou cancelamento',
                'Paciente não compareceu',
                'Emergência médica',
                'Problemas pessoais do paciente',
                'Reagendamento solicitado',
                'Problemas técnicos',
                'Outro motivo',
            ]
        };
        renderSettings();
    }
}

// Update appointment modal with current settings
function updateAppointmentModalWithSettings() {
    if (!appointmentSettings) return;
    
    // Update duration select
    const durationSelect = document.getElementById('appointment-duration');
    if (durationSelect) {
        durationSelect.innerHTML = '';
        appointmentSettings.duration_options.forEach(minutes => {
            const option = document.createElement('option');
            option.value = minutes;
            option.textContent = formatDuration(minutes);
            if (minutes === 30) {
                option.selected = true;
            }
            durationSelect.appendChild(option);
        });
    }
    
    // Update type select (now using display names directly)
    const typeSelect = document.getElementById('appointment-type');
    if (typeSelect) {
        typeSelect.innerHTML = '';
        // Normalize: handle both old format [value, label] and new format (string)
        const normalizedTypes = appointmentSettings.type_choices.map(choice => {
            if (Array.isArray(choice) && choice.length >= 2) {
                return choice[1]; // Use label from old format
            }
            return String(choice); // New format
        });
        
        normalizedTypes.forEach((displayName, index) => {
            const option = document.createElement('option');
            option.value = displayName; // Use display name as value
            option.textContent = displayName;
            if (index === 0) {
                option.selected = true;
            }
            typeSelect.appendChild(option);
        });
    }
    
    // Update status select (now using display names directly)
    const statusSelect = document.getElementById('appointment-status');
    if (statusSelect) {
        statusSelect.innerHTML = '';
        // Normalize: handle both old format [value, label] and new format (string)
        const normalizedStatuses = appointmentSettings.status_choices.map(choice => {
            if (Array.isArray(choice) && choice.length >= 2) {
                return choice[1]; // Use label from old format
            }
            return String(choice); // New format
        });
        
        normalizedStatuses.forEach((displayName, index) => {
            const option = document.createElement('option');
            option.value = displayName; // Use display name as value
            option.textContent = displayName;
            if (index === 0) {
                option.selected = true;
            }
            statusSelect.appendChild(option);
        });
    }
    
    // Update insurance operator select
    const insuranceOperatorSelect = document.getElementById('appointment-insurance-operator');
    if (insuranceOperatorSelect && appointmentSettings.insurance_operators) {
        insuranceOperatorSelect.innerHTML = '<option value="">Selecione o convênio</option>';
        appointmentSettings.insurance_operators.forEach(operator => {
            const option = document.createElement('option');
            option.value = operator;
            option.textContent = operator;
            insuranceOperatorSelect.appendChild(option);
        });
    }
    
    // Update location input (convert to select if locations are configured)
    const locationInput = document.getElementById('appointment-location');
    if (locationInput && appointmentSettings.location_options.length > 0) {
        // Replace input with select
        const parent = locationInput.parentElement;
        const select = document.createElement('select');
        select.className = 'form-select';
        select.id = 'appointment-location';
        select.name = 'location';
        
        // Add empty option
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'Selecione um local...';
        select.appendChild(emptyOption);
        
        // Add location options
        appointmentSettings.location_options.forEach(location => {
            const option = document.createElement('option');
            option.value = location;
            option.textContent = location;
            select.appendChild(option);
        });
        
        parent.replaceChild(select, locationInput);
    } else if (locationInput && appointmentSettings.location_options.length === 0) {
        // Ensure it's an input if no locations configured
        if (locationInput.tagName !== 'INPUT') {
            const parent = locationInput.parentElement;
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-control';
            input.id = 'appointment-location';
            input.name = 'location';
            input.placeholder = 'Ex: Sala 1, Consultório A';
            parent.replaceChild(input, locationInput);
        }
    }
}

// Format duration in minutes to readable string
function formatDuration(minutes) {
    if (minutes < 60) {
        return `${minutes} minutos`;
    } else if (minutes === 60) {
        return "1 hora";
    } else {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        if (mins === 0) {
            return `${hours} horas`;
        } else {
            return `${hours}h ${mins}min`;
        }
    }
}

// Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Initialize settings form and load settings on page load
document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveSettings();
        });
    }
    
    // Load settings on page load so they're available for the appointment modal
    // Small delay to ensure other scripts are loaded
    setTimeout(function() {
        if (typeof loadSettings === 'function') {
            loadSettings();
        }
    }, 500);
});

