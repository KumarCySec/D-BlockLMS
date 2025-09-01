/**
 * D-Block Library Management System
 * Main JavaScript file
 */

// Global app object
const LibraryApp = {
    // Configuration
    config: {
        apiBaseUrl: '/api',
        csrfToken: null,
        userId: null
    },
    
    // Initialize the application
    init() {
        this.setupCSRF();
        this.setupEventListeners();
        this.setupFormValidation();
        this.setupTooltips();
        console.log('Library Management System initialized');
    },
    
    // Setup CSRF token for AJAX requests
    setupCSRF() {
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (csrfToken) {
            this.config.csrfToken = csrfToken.getAttribute('content');
            
            // Set default headers for fetch requests
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (!options.headers) {
                    options.headers = {};
                }
                options.headers['X-CSRFToken'] = LibraryApp.config.csrfToken;
                return originalFetch(url, options);
            };
        }
    },
    
    // Setup global event listeners
    setupEventListeners() {
        // Handle form submissions with loading states
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form.tagName === 'FORM') {
                this.handleFormSubmit(form);
            }
        });
        
        // Handle AJAX links
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-ajax]')) {
                e.preventDefault();
                this.handleAjaxLink(e.target);
            }
        });
        
        // Auto-dismiss alerts after 5 seconds
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(alert => {
                if (alert.classList.contains('show')) {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            });
        }, 5000);
    },
    
    // Setup form validation
    setupFormValidation() {
        // Password confirmation validation
        const passwordFields = document.querySelectorAll('input[type="password"]');
        passwordFields.forEach(field => {
            if (field.name === 'confirm_password') {
                field.addEventListener('input', this.validatePasswordConfirmation);
            }
        });
        
        // Phone number formatting
        const phoneFields = document.querySelectorAll('input[type="tel"]');
        phoneFields.forEach(field => {
            field.addEventListener('input', this.formatPhoneNumber);
        });
        
        // Roll number formatting
        const rollFields = document.querySelectorAll('input[name="roll_number"]');
        rollFields.forEach(field => {
            field.addEventListener('input', this.formatRollNumber);
        });
    },
    
    // Setup Bootstrap tooltips
    setupTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },
    
    // Handle form submission with loading state
    handleFormSubmit(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
            
            // Re-enable after 10 seconds as fallback
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || 'Submit';
            }, 10000);
        }
    },
    
    // Handle AJAX links
    async handleAjaxLink(link) {
        const url = link.getAttribute('href');
        const method = link.getAttribute('data-method') || 'GET';
        
        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(data.message, 'success');
                // Reload page or update UI as needed
                if (link.getAttribute('data-reload') === 'true') {
                    setTimeout(() => location.reload(), 1000);
                }
            } else {
                this.showAlert(data.message, 'error');
            }
        } catch (error) {
            this.showAlert('An error occurred. Please try again.', 'error');
            console.error('AJAX error:', error);
        }
    },
    
    // Validate password confirmation
    validatePasswordConfirmation(e) {
        const confirmField = e.target;
        const passwordField = document.querySelector('input[name="password"]');
        
        if (passwordField && confirmField.value !== passwordField.value) {
            confirmField.setCustomValidity('Passwords do not match');
        } else {
            confirmField.setCustomValidity('');
        }
    },
    
    // Format phone number input
    formatPhoneNumber(e) {
        let value = e.target.value.replace(/\D/g, '');
        
        if (value.length >= 10) {
            value = value.substring(0, 10);
            // Format as XXX-XXX-XXXX
            value = value.replace(/(\d{3})(\d{3})(\d{4})/, '$1-$2-$3');
        }
        
        e.target.value = value;
    },
    
    // Format roll number input
    formatRollNumber(e) {
        let value = e.target.value.toUpperCase();
        // Remove invalid characters
        value = value.replace(/[^A-Z0-9-_]/g, '');
        e.target.value = value;
    },
    
    // Show alert message
    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container') || document.body;
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }
        }, 5000);
    },
    
    // API helper methods
    api: {
        async get(endpoint) {
            const response = await fetch(`${LibraryApp.config.apiBaseUrl}${endpoint}`);
            return response.json();
        },
        
        async post(endpoint, data) {
            const response = await fetch(`${LibraryApp.config.apiBaseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            return response.json();
        },
        
        async put(endpoint, data) {
            const response = await fetch(`${LibraryApp.config.apiBaseUrl}${endpoint}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            return response.json();
        },
        
        async delete(endpoint) {
            const response = await fetch(`${LibraryApp.config.apiBaseUrl}${endpoint}`, {
                method: 'DELETE'
            });
            return response.json();
        }
    },
    
    // Utility functions
    utils: {
        // Format date for display
        formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-IN', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },
        
        // Debounce function for search inputs
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // Copy text to clipboard
        async copyToClipboard(text) {
            try {
                await navigator.clipboard.writeText(text);
                LibraryApp.showAlert('Copied to clipboard', 'success');
            } catch (err) {
                console.error('Failed to copy: ', err);
                LibraryApp.showAlert('Failed to copy to clipboard', 'error');
            }
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    LibraryApp.init();
});

// Export for use in other scripts
window.LibraryApp = LibraryApp;