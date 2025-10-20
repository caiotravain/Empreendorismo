// Main JavaScript for SaaS Platform

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Tab switching functionality
    initializeTabs();
    
    // Form validation
    initializeFormValidation();
    
    // Dashboard interactions
    initializeDashboard();
    
    // Notification system
    initializeNotifications();
});

// Tab switching functionality
function initializeTabs() {
    const tabButtons = document.querySelectorAll('[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });
}

function switchTab(tabName) {
    // Check if trying to access other tabs without selecting a patient
    // Allow access to 'agenda', 'pacientes', 'indicadores', and 'finance' without patient selection
    // Only require patient selection for 'prontuarios' and 'prescricao' tabs
    if (tabName === 'prontuarios' || tabName === 'prescricao') {
        // Check if selectedPatient is available and not null
        if (typeof selectedPatient === 'undefined' || selectedPatient === null) {
            alert('Por favor, selecione um paciente na agenda primeiro.');
            return;
        }
    }
    
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.style.display = 'none';
        content.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.style.display = 'block';
        selectedTab.classList.add('active');
    }
    
    // Update button states
    const buttons = document.querySelectorAll('.btn-group .btn');
    buttons.forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-primary');
    });
    
    // Highlight active button by finding the button that calls this function
    const activeButton = document.querySelector(`[onclick*="switchTab('${tabName}')"]`);
    if (activeButton) {
        activeButton.classList.remove('btn-outline-primary');
        activeButton.classList.add('btn-primary');
    }
    
    // Load data for specific tabs
    if (tabName === 'finance') {
        if (typeof loadFinanceData === 'function') {
            loadFinanceData();
        }
    }
    
    // Load patients data when pacientes tab is shown
    if (tabName === 'pacientes') {
        // Patients tab is already included in the template
        // Apply filters when tab is shown
        if (typeof filterPatients === 'function') {
            setTimeout(filterPatients, 100);
        }
    }
    
    // Initialize FullCalendar when agenda tab is shown
    if (tabName === 'agenda') {
        if (typeof initializeFullCalendar === 'function') {
            setTimeout(initializeFullCalendar, 100);
        }
        // Refresh agenda stats when switching to agenda tab
        if (typeof refreshAgendaStats === 'function') {
            refreshAgendaStats();
        }
    }
    
    // Initialize prescription form when prescricao tab is shown
    if (tabName === 'prescricao') {
        if (typeof initializePrescriptionForm === 'function') {
            setTimeout(initializePrescriptionForm, 100);
        }
    }
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Dashboard functionality
function initializeDashboard() {
    // Stats counter animation
    animateCounters();
    
    // Chart placeholders (for future implementation)
    initializeCharts();
    
    // Quick action buttons
    initializeQuickActions();
}

// Animate counters on dashboard
function animateCounters() {
    const counters = document.querySelectorAll('.counter');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = parseInt(counter.getAttribute('data-target'));
                const duration = 2000; // 2 seconds
                const increment = target / (duration / 16); // 60fps
                let current = 0;
                
                const updateCounter = () => {
                    current += increment;
                    if (current < target) {
                        counter.textContent = Math.floor(current).toLocaleString();
                        requestAnimationFrame(updateCounter);
                    } else {
                        counter.textContent = target.toLocaleString();
                    }
                };
                
                updateCounter();
                observer.unobserve(counter);
            }
        });
    });
    
    counters.forEach(counter => observer.observe(counter));
}

// Initialize chart placeholders
function initializeCharts() {
    // This is a placeholder for future chart implementations
    // You can integrate Chart.js, D3.js, or any other charting library here
    console.log('Charts initialized - ready for chart library integration');
}

// Quick action buttons
function initializeQuickActions() {
    const quickActionButtons = document.querySelectorAll('.quick-action');
    
    quickActionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            handleQuickAction(action);
        });
    });
}

// Handle quick actions
function handleQuickAction(action) {
    switch(action) {
        case 'create-project':
            showModal('Create New Project', 'Project creation form will go here');
            break;
        case 'invite-member':
            showModal('Invite Team Member', 'Team member invitation form will go here');
            break;
        case 'generate-report':
            showModal('Generate Report', 'Report generation options will go here');
            break;
        case 'settings':
            window.location.href = '/dashboard/settings/';
            break;
        default:
            console.log('Unknown action:', action);
    }
}

// Modal system
function showModal(title, content) {
    // Create modal HTML
    const modalHTML = `
        <div class="modal fade" id="quickActionModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${content}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary">Save changes</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('quickActionModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('quickActionModal'));
    modal.show();
}

// Notification system
function initializeNotifications() {
    // Check for existing notifications
    const notifications = JSON.parse(localStorage.getItem('notifications') || '[]');
    
    notifications.forEach(notification => {
        showNotification(notification.message, notification.type);
    });
    
    // Clear notifications from storage
    localStorage.removeItem('notifications');
}

function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(new Date(date));
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Search functionality
function initializeSearch() {
    const searchInput = document.querySelector('#searchInput');
    if (searchInput) {
        const debouncedSearch = debounce(performSearch, 300);
        searchInput.addEventListener('input', debouncedSearch);
    }
}

function performSearch(query) {
    // Implement search functionality here
    console.log('Searching for:', query);
}


// Export functions for global use
window.SaaSPlatform = {
    switchTab,
    showNotification,
    formatCurrency,
    formatDate,
    showModal
};
