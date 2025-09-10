/**
 * Fine Management JavaScript
 * Handles fine display, filtering, and interactions
 */

class FineManager {
    constructor() {
        this.finesData = [];
        this.filteredFines = [];
        this.currentSort = 'date_desc';
        this.currentFilters = {
            status: 'all',
            itemType: 'all'
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadFines();
        this.setupAutoRefresh();
    }
    
    bindEvents() {
        // Filter and sort event listeners
        document.getElementById('statusFilter')?.addEventListener('change', () => this.filterFines());
        document.getElementById('itemTypeFilter')?.addEventListener('change', () => this.filterFines());
        document.getElementById('sortBy')?.addEventListener('change', () => this.sortFines());
        
        // Refresh button
        document.querySelector('[onclick="refreshFines()"]')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.loadFines();
        });
    }
    
    async loadFines() {
        try {
            this.showLoading(true);
            this.hideError();
            
            const response = await fetch('/api/fines/my');
            const data = await response.json();
            
            if (data.success) {
                this.finesData = data.data.fine_records || [];
                this.updateSummary(data.data);
                this.displayFines();
                this.toggleSections();
            } else {
                this.showError(data.message || 'Failed to load fines');
            }
        } catch (error) {
            console.error('Error loading fines:', error);
            this.showError('Network error occurred while loading fines');
        } finally {
            this.showLoading(false);
        }
    }
    
    filterFines() {
        const statusFilter = document.getElementById('statusFilter')?.value || 'all';
        const itemTypeFilter = document.getElementById('itemTypeFilter')?.value || 'all';
        
        this.currentFilters = { status: statusFilter, itemType: itemTypeFilter };
        
        this.filteredFines = this.finesData.filter(fine => {
            const statusMatch = statusFilter === 'all' || fine.status === statusFilter;
            const typeMatch = itemTypeFilter === 'all' || fine.item_type === itemTypeFilter;
            return statusMatch && typeMatch;
        });
        
        this.sortFines();
    }
    
    sortFines() {
        const sortBy = document.getElementById('sortBy')?.value || 'date_desc';
        this.currentSort = sortBy;
        
        this.filteredFines.sort((a, b) => {
            switch (sortBy) {
                case 'date_asc':
                    return new Date(a.created_at) - new Date(b.created_at);
                case 'date_desc':
                    return new Date(b.created_at) - new Date(a.created_at);
                case 'amount_asc':
                    return a.amount - b.amount;
                case 'amount_desc':
                    return b.amount - a.amount;
                case 'status':
                    return a.status.localeCompare(b.status);
                default:
                    return 0;
            }
        });
        
        this.renderFines();
    }
    
    displayFines() {
        this.filteredFines = [...this.finesData];
        this.sortFines();
    }
    
    renderFines() {
        const container = document.getElementById('finesContainer');
        if (!container) return;
        
        if (this.filteredFines.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-check-circle text-success" style="font-size: 3rem;"></i>
                    <h5 class="mt-3">No Fines Found</h5>
                    <p class="text-muted">You have no fines matching the current filters.</p>
                </div>
            `;
            return;
        }
        
        const finesHtml = this.filteredFines.map(fine => this.renderFineCard(fine)).join('');
        container.innerHTML = finesHtml;
    }
    
    renderFineCard(fine) {
        const statusBadge = this.getStatusBadge(fine.status);
        const itemTypeIcon = this.getItemTypeIcon(fine.item_type);
        const formattedDate = new Date(fine.created_at).toLocaleDateString();
        const formattedAmount = fine.amount.toFixed(2);
        
        return `
            <div class="card mb-3 fine-card" data-fine-id="${fine.id}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <i class="bi ${itemTypeIcon} text-primary" style="font-size: 1.5rem;"></i>
                        </div>
                        <div class="col">
                            <h6 class="card-title mb-1">
                                ${fine.item_title}
                                ${statusBadge}
                            </h6>
                            <p class="card-text text-muted mb-1">
                                <small>
                                    <i class="bi bi-calendar3"></i> ${formattedDate}
                                    <span class="mx-2">•</span>
                                    <i class="bi bi-tag"></i> ${fine.item_type}
                                </small>
                            </p>
                            ${fine.reason ? `<p class="card-text mb-2"><small class="text-muted">${fine.reason}</small></p>` : ''}
                        </div>
                        <div class="col-auto text-end">
                            <div class="h5 mb-1 text-danger">₹${formattedAmount}</div>
                            ${fine.status === 'pending' ? this.renderFineActions(fine) : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderFineActions(fine) {
        return `
            <div class="btn-group-vertical btn-group-sm">
                <button class="btn btn-outline-success btn-sm" onclick="fineManager.payFine(${fine.id})">
                    <i class="bi bi-credit-card"></i> Pay
                </button>
                <button class="btn btn-outline-info btn-sm" onclick="fineManager.requestWaiver(${fine.id})">
                    <i class="bi bi-question-circle"></i> Request Waiver
                </button>
            </div>
        `;
    }
    
    getStatusBadge(status) {
        const badges = {
            'pending': '<span class="badge bg-warning">Pending</span>',
            'paid': '<span class="badge bg-success">Paid</span>',
            'waived': '<span class="badge bg-info">Waived</span>',
            'waiver_requested': '<span class="badge bg-secondary">Waiver Requested</span>'
        };
        return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
    }
    
    getItemTypeIcon(itemType) {
        const icons = {
            'book': 'bi-book',
            'laptop': 'bi-laptop',
            'kit': 'bi-box'
        };
        return icons[itemType] || 'bi-question-circle';
    }
    
    updateSummary(data) {
        const summaryContainer = document.getElementById('finesSummary');
        if (!summaryContainer) return;
        
        const summary = data.summary || {};
        
        summaryContainer.innerHTML = `
            <div class="row g-3">
                <div class="col-6 col-md-3">
                    <div class="card bg-danger text-white">
                        <div class="card-body text-center">
                            <h4 class="mb-1">₹${(summary.total_amount || 0).toFixed(2)}</h4>
                            <small>Total Fines</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-warning text-dark">
                        <div class="card-body text-center">
                            <h4 class="mb-1">₹${(summary.pending_amount || 0).toFixed(2)}</h4>
                            <small>Pending</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body text-center">
                            <h4 class="mb-1">₹${(summary.paid_amount || 0).toFixed(2)}</h4>
                            <small>Paid</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body text-center">
                            <h4 class="mb-1">₹${(summary.waived_amount || 0).toFixed(2)}</h4>
                            <small>Waived</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    toggleSections() {
        const hasFines = this.finesData.length > 0;
        const noFinesMessage = document.getElementById('noFinesMessage');
        const finesSection = document.getElementById('finesSection');
        
        if (noFinesMessage) {
            noFinesMessage.style.display = hasFines ? 'none' : 'block';
        }
        if (finesSection) {
            finesSection.style.display = hasFines ? 'block' : 'none';
        }
    }
    
    async payFine(fineId) {
        if (!confirm('Are you sure you want to mark this fine as paid?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/fines/${fineId}/pay`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Fine marked as paid successfully');
                this.loadFines();
            } else {
                this.showError(data.message || 'Failed to pay fine');
            }
        } catch (error) {
            console.error('Error paying fine:', error);
            this.showError('Network error occurred');
        }
    }
    
    async requestWaiver(fineId) {
        const reason = prompt('Please provide a reason for the waiver request:');
        if (!reason || reason.trim() === '') {
            return;
        }
        
        try {
            const response = await fetch(`/api/fines/${fineId}/request-waiver`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ reason: reason.trim() })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Waiver request submitted successfully');
                this.loadFines();
            } else {
                this.showError(data.message || 'Failed to submit waiver request');
            }
        } catch (error) {
            console.error('Error requesting waiver:', error);
            this.showError('Network error occurred');
        }
    }
    
    setupAutoRefresh() {
        // Refresh fines every 5 minutes
        setInterval(() => {
            this.loadFines();
        }, 300000);
    }
    
    showLoading(show) {
        const loader = document.getElementById('loadingSpinner');
        if (loader) {
            loader.style.display = show ? 'block' : 'none';
        }
    }
    
    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        if (errorDiv) {
            errorDiv.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <i class="bi bi-exclamation-triangle"></i> ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            errorDiv.style.display = 'block';
        }
    }
    
    hideError() {
        const errorDiv = document.getElementById('errorMessage');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }
    
    showSuccess(message) {
        const errorDiv = document.getElementById('errorMessage');
        if (errorDiv) {
            errorDiv.innerHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <i class="bi bi-check-circle"></i> ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            errorDiv.style.display = 'block';
            
            // Auto-hide success message after 3 seconds
            setTimeout(() => {
                const alert = errorDiv.querySelector('.alert');
                if (alert) {
                    alert.classList.remove('show');
                    setTimeout(() => this.hideError(), 150);
                }
            }, 3000);
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        return token || '';
    }
}

// Initialize fine manager when DOM is loaded
let fineManager;

document.addEventListener('DOMContentLoaded', function() {
    fineManager = new FineManager();
});

// Legacy function support for onclick handlers
function refreshFines() {
    if (fineManager) {
        fineManager.loadFines();
    }
} 