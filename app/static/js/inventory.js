/**
 * Inventory Management JavaScript
 * Mobile-first responsive inventory browsing and management
 */

class InventoryManager {
    constructor() {
        this.currentPage = 1;
        this.currentFilters = {};
        this.currentSort = { by: 'title', order: 'asc' };
        this.currentQuery = '';
        this.searchTimeout = null;
        this.filterOptions = {};

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadFilterOptions();
        this.loadInventory();
        this.loadQuickStats();
    }

    bindEvents() {
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        const searchForm = document.getElementById('searchForm');

        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.handleSearch(e.target.value);
            }, 300);
        });

        searchInput.addEventListener('focus', () => {
            this.showSearchSuggestions();
        });

        searchInput.addEventListener('blur', () => {
            // Delay hiding to allow clicking on suggestions
            setTimeout(() => this.hideSearchSuggestions(), 200);
        });

        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSearch(searchInput.value);
        });

        // Quick filters
        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                this.handleQuickFilter(e.target);
            });
        });

        // Advanced filters
        const advancedForm = document.getElementById('advancedFilterForm');
        advancedForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.applyAdvancedFilters();
        });

        document.getElementById('clearFilters').addEventListener('click', () => {
            this.clearAllFilters();
        });

        // Pagination will be bound dynamically
    }

    async loadFilterOptions() {
        try {
            const response = await fetch('/api/inventory?per_page=1');
            const data = await response.json();

            if (data.success) {
                this.filterOptions = data.data.filters;
                this.populateFilterDropdowns();
            }
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    }

    populateFilterDropdowns() {
        // Languages
        const languageSelect = document.getElementById('filterLanguage');
        languageSelect.innerHTML = '';
        this.filterOptions.languages.forEach(lang => {
            const option = document.createElement('option');
            option.value = lang.value;
            option.textContent = lang.label;
            languageSelect.appendChild(option);
        });

        // Departments
        const departmentSelect = document.getElementById('filterDepartment');
        departmentSelect.innerHTML = '';
        this.filterOptions.departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept.value;
            option.textContent = dept.label;
            departmentSelect.appendChild(option);
        });

        // Donor batches
        const batchSelect = document.getElementById('filterDonorBatch');
        batchSelect.innerHTML = '';
        this.filterOptions.donor_batches.forEach(batch => {
            const option = document.createElement('option');
            option.value = batch.value;
            option.textContent = batch.label;
            batchSelect.appendChild(option);
        });
    }

    async loadInventory() {
        this.showLoading();

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: 12,
                sort: this.currentSort.by,
                order: this.currentSort.order
            });

            if (this.currentQuery) {
                params.append('q', this.currentQuery);
            }

            // Add filters
            Object.entries(this.currentFilters).forEach(([key, value]) => {
                if (Array.isArray(value)) {
                    params.append(key, value.join(','));
                } else {
                    params.append(key, value);
                }
            });

            const response = await fetch(`/api/inventory?${params}`);
            const data = await response.json();

            if (data.success) {
                this.renderInventoryGrid(data.data.items);
                this.renderPagination(data.data.pagination);
                this.updateResultsCount(data.data.pagination.total);
                this.updateAppliedFilters();
            } else {
                this.showError('Failed to load inventory');
            }
        } catch (error) {
            console.error('Error loading inventory:', error);
            this.showError('Failed to load inventory');
        } finally {
            this.hideLoading();
        }
    }

    async loadQuickStats() {
        try {
            const response = await fetch('/api/inventory/analytics');
            const data = await response.json();

            if (data.success) {
                const stats = data.data.summary;
                document.getElementById('totalItems').textContent = stats.total_items;
                document.getElementById('availableItems').textContent = stats.available_items;
                document.getElementById('borrowedItems').textContent = stats.unavailable_items;
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    renderInventoryGrid(items) {
        const grid = document.getElementById('inventoryGrid');
        const noResults = document.getElementById('noResults');

        if (items.length === 0) {
            grid.innerHTML = '';
            noResults.classList.remove('d-none');
            return;
        }

        noResults.classList.add('d-none');

        grid.innerHTML = items.map(item => this.createItemCard(item)).join('');

        // Bind click events for item cards
        grid.querySelectorAll('.item-card').forEach(card => {
            card.addEventListener('click', () => {
                const itemId = card.dataset.itemId;
                this.showItemDetail(itemId);
            });
        });
    }

    createItemCard(item) {
        const availabilityBadge = item.is_available
            ? `<span class="badge bg-success availability-badge">Available (${item.available_quantity})</span>`
            : `<span class="badge bg-danger availability-badge">Unavailable</span>`;

        const itemTypeIcon = {
            'book': 'bi-book',
            'laptop': 'bi-laptop',
            'kit': 'bi-box'
        }[item.item_type] || 'bi-box';

        return `
            <div class="col-lg-4 col-md-6 col-sm-12 mb-4">
                <div class="card item-card h-100" data-item-id="${item.id}" style="cursor: pointer;">
                    ${availabilityBadge}
                    <div class="card-body">
                        <div class="d-flex align-items-start mb-2">
                            <i class="bi ${itemTypeIcon} text-primary me-2 fs-4"></i>
                            <div class="flex-grow-1">
                                <h6 class="card-title mb-1">${this.escapeHtml(item.title)}</h6>
                                ${item.authors ? `<p class="text-muted small mb-1">by ${this.escapeHtml(item.authors)}</p>` : ''}
                            </div>
                        </div>
                        
                        <div class="donor-info mb-2">
                            <i class="bi bi-person-heart"></i>
                            Donated by ${this.escapeHtml(item.donor.name)} (${item.donor.batch})
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                <i class="bi bi-calendar3"></i>
                                ${new Date(item.date_of_donation).toLocaleDateString()}
                            </small>
                            <span class="badge bg-light text-dark">${item.item_type}</span>
                        </div>
                        
                        ${item.language ? `<div class="mt-2"><small class="text-muted">Language: ${item.language}</small></div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    renderPagination(pagination) {
        const paginationEl = document.getElementById('pagination');

        if (pagination.pages <= 1) {
            paginationEl.innerHTML = '';
            return;
        }

        let html = '';

        // Previous button
        html += `
            <li class="page-item ${!pagination.has_prev ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${pagination.page - 1}">
                    <i class="bi bi-chevron-left"></i>
                </a>
            </li>
        `;

        // Page numbers
        const startPage = Math.max(1, pagination.page - 2);
        const endPage = Math.min(pagination.pages, pagination.page + 2);

        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `
                <li class="page-item ${i === pagination.page ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }

        if (endPage < pagination.pages) {
            if (endPage < pagination.pages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.pages}">${pagination.pages}</a></li>`;
        }

        // Next button
        html += `
            <li class="page-item ${!pagination.has_next ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${pagination.page + 1}">
                    <i class="bi bi-chevron-right"></i>
                </a>
            </li>
        `;

        paginationEl.innerHTML = html;

        // Bind pagination events
        paginationEl.querySelectorAll('a[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(e.target.closest('a').dataset.page);
                if (page && page !== this.currentPage) {
                    this.currentPage = page;
                    this.loadInventory();
                }
            });
        });
    }

    handleSearch(query) {
        this.currentQuery = query.trim();
        this.currentPage = 1;
        this.loadInventory();

        if (query.length >= 2) {
            this.loadSearchSuggestions(query);
        } else {
            this.hideSearchSuggestions();
        }
    }

    async loadSearchSuggestions(query) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.success) {
                this.renderSearchSuggestions(data.data.suggestions);
            }
        } catch (error) {
            console.error('Error loading suggestions:', error);
        }
    }

    renderSearchSuggestions(suggestions) {
        const suggestionsEl = document.getElementById('searchSuggestions');

        if (!suggestions.items.length && !suggestions.donors.length) {
            this.hideSearchSuggestions();
            return;
        }

        let html = '';

        suggestions.items.forEach(item => {
            html += `
                <div class="suggestion-item" data-suggestion="${this.escapeHtml(item.text)}">
                    <i class="bi bi-${item.type === 'title' ? 'book' : 'person'}"></i>
                    ${this.escapeHtml(item.text)}
                    <small class="text-muted">(${item.type})</small>
                </div>
            `;
        });

        suggestions.donors.forEach(donor => {
            html += `
                <div class="suggestion-item" data-suggestion="${this.escapeHtml(donor.text)}">
                    <i class="bi bi-person-heart"></i>
                    ${this.escapeHtml(donor.text)}
                    <small class="text-muted">(donor)</small>
                </div>
            `;
        });

        suggestionsEl.innerHTML = html;
        suggestionsEl.style.display = 'block';

        // Bind suggestion clicks
        suggestionsEl.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                const suggestion = item.dataset.suggestion;
                document.getElementById('searchInput').value = suggestion;
                this.handleSearch(suggestion);
                this.hideSearchSuggestions();
            });
        });
    }

    showSearchSuggestions() {
        const query = document.getElementById('searchInput').value;
        if (query.length >= 2) {
            this.loadSearchSuggestions(query);
        }
    }

    hideSearchSuggestions() {
        document.getElementById('searchSuggestions').style.display = 'none';
    }

    handleQuickFilter(chip) {
        // Remove active class from all chips
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');

        const filter = chip.dataset.filter;

        // Reset filters
        this.currentFilters = {};

        if (filter === 'available') {
            this.currentFilters.availability = 'available';
        } else if (filter !== 'all') {
            this.currentFilters.type = filter;
        }

        this.currentPage = 1;
        this.loadInventory();
    }

    applyAdvancedFilters() {
        const form = document.getElementById('advancedFilterForm');
        const formData = new FormData(form);

        this.currentFilters = {};

        // Get selected values from multi-selects
        const typeSelect = document.getElementById('filterType');
        const selectedTypes = Array.from(typeSelect.selectedOptions).map(opt => opt.value);
        if (selectedTypes.length > 0) {
            this.currentFilters.type = selectedTypes;
        }

        const languageSelect = document.getElementById('filterLanguage');
        const selectedLanguages = Array.from(languageSelect.selectedOptions).map(opt => opt.value);
        if (selectedLanguages.length > 0) {
            this.currentFilters.language = selectedLanguages;
        }

        const departmentSelect = document.getElementById('filterDepartment');
        const selectedDepartments = Array.from(departmentSelect.selectedOptions).map(opt => opt.value);
        if (selectedDepartments.length > 0) {
            this.currentFilters.department = selectedDepartments;
        }

        const batchSelect = document.getElementById('filterDonorBatch');
        const selectedBatches = Array.from(batchSelect.selectedOptions).map(opt => opt.value);
        if (selectedBatches.length > 0) {
            this.currentFilters.donor_batch = selectedBatches;
        }

        // Update sorting
        this.currentSort.by = document.getElementById('sortBy').value;
        this.currentSort.order = document.getElementById('sortOrder').value;

        this.currentPage = 1;
        this.loadInventory();

        // Collapse the advanced filters
        const collapse = new bootstrap.Collapse(document.getElementById('advancedFilters'));
        collapse.hide();
    }

    clearAllFilters() {
        // Reset form
        document.getElementById('advancedFilterForm').reset();

        // Reset filters and sorting
        this.currentFilters = {};
        this.currentSort = { by: 'title', order: 'asc' };
        this.currentPage = 1;

        // Reset quick filters
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        document.querySelector('.filter-chip[data-filter="all"]').classList.add('active');

        this.loadInventory();
    }

    updateResultsCount(total) {
        const resultsEl = document.getElementById('resultsCount');
        resultsEl.textContent = `${total} item${total !== 1 ? 's' : ''} found`;
    }

    updateAppliedFilters() {
        const appliedEl = document.getElementById('appliedFilters');
        const filterCount = Object.keys(this.currentFilters).length;

        if (filterCount > 0) {
            appliedEl.textContent = `(${filterCount} filter${filterCount !== 1 ? 's' : ''} applied)`;
        } else {
            appliedEl.textContent = '';
        }
    }

    async showItemDetail(itemId) {
        try {
            const response = await fetch(`/api/inventory/${itemId}`);
            const data = await response.json();

            if (data.success) {
                this.renderItemDetail(data.data.item);
                const modal = new bootstrap.Modal(document.getElementById('itemDetailModal'));
                modal.show();
            } else {
                this.showError('Failed to load item details');
            }
        } catch (error) {
            console.error('Error loading item details:', error);
            this.showError('Failed to load item details');
        }
    }

    renderItemDetail(item) {
        const content = document.getElementById('itemDetailContent');

        const itemTypeIcon = {
            'book': 'bi-book',
            'laptop': 'bi-laptop',
            'kit': 'bi-box'
        }[item.item_type] || 'bi-box';

        content.innerHTML = `
            <div class="row">
                <div class="col-md-8">
                    <div class="d-flex align-items-center mb-3">
                        <i class="bi ${itemTypeIcon} text-primary me-3 fs-1"></i>
                        <div>
                            <h4 class="mb-1">${this.escapeHtml(item.title)}</h4>
                            ${item.authors ? `<p class="text-muted mb-0">by ${this.escapeHtml(item.authors)}</p>` : ''}
                        </div>
                    </div>
                    
                    ${item.description ? `
                        <div class="mb-3">
                            <h6>Description</h6>
                            <p>${this.escapeHtml(item.description)}</p>
                        </div>
                    ` : ''}
                    
                    <div class="row">
                        <div class="col-sm-6 mb-2">
                            <strong>Type:</strong> ${item.item_type}
                        </div>
                        ${item.language ? `
                            <div class="col-sm-6 mb-2">
                                <strong>Language:</strong> ${item.language}
                            </div>
                        ` : ''}
                        ${item.sku_code ? `
                            <div class="col-sm-6 mb-2">
                                <strong>SKU:</strong> ${item.sku_code}
                            </div>
                        ` : ''}
                        ${item.published_date ? `
                            <div class="col-sm-6 mb-2">
                                <strong>Published:</strong> ${new Date(item.published_date).toLocaleDateString()}
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">Availability</h6>
                        </div>
                        <div class="card-body">
                            <div class="text-center mb-3">
                                <div class="h2 ${item.is_available ? 'text-success' : 'text-danger'}">
                                    ${item.available_quantity}/${item.total_quantity}
                                </div>
                                <small class="text-muted">Available / Total</small>
                            </div>
                            
                            ${item.is_available ? `
                                <button class="btn btn-primary w-100" onclick="requestCheckout(${item.id})">
                                    <i class="bi bi-bookmark-plus"></i> Request Checkout
                                </button>
                            ` : `
                                <button class="btn btn-outline-secondary w-100" onclick="joinWaitlist(${item.id})">
                                    <i class="bi bi-clock"></i> Join Waitlist
                                </button>
                            `}
                        </div>
                    </div>
                    
                    <div class="card mt-3">
                        <div class="card-header">
                            <h6 class="mb-0">Donor Information</h6>
                        </div>
                        <div class="card-body">
                            <p class="mb-1"><strong>${this.escapeHtml(item.donor.name)}</strong></p>
                            <p class="text-muted mb-1">${item.donor.branch} - ${item.donor.batch}</p>
                            <small class="text-muted">
                                Donated on ${new Date(item.date_of_donation).toLocaleDateString()}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    showLoading() {
        document.getElementById('loadingSpinner').style.display = 'block';
        document.getElementById('inventoryGrid').style.display = 'none';
        document.getElementById('noResults').classList.add('d-none');
    }

    hideLoading() {
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('inventoryGrid').style.display = 'flex';
    }

    showError(message) {
        // You can implement a toast notification system here
        console.error(message);
        alert(message); // Simple fallback
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global functions for item actions
function requestCheckout(itemId) {
    // This will be implemented in the transaction management phase
    alert('Checkout functionality will be available in the next phase');
}

function joinWaitlist(itemId) {
    // This will be implemented in the waitlist management phase
    alert('Waitlist functionality will be available in the next phase');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new InventoryManager();
});