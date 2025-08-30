// Community Mangrove Watch - JavaScript Application
(function() {
    'use strict';

    // Application configuration
    const CONFIG = {
        GEOLOCATION_TIMEOUT: 10000,
        GEOLOCATION_MAX_AGE: 300000,
        AUTO_SAVE_INTERVAL: 30000,
        MAX_FILE_SIZE: 16 * 1024 * 1024, // 16MB
        ALLOWED_FILE_TYPES: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
    };

    // Utility functions
    const Utils = {
        // Format date to readable string
        formatDate: function(date) {
            return new Date(date).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        // Debounce function for performance
        debounce: function(func, wait) {
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

        // Show toast notification
        showToast: function(message, type = 'info') {
            const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
            const toast = this.createToastElement(message, type);
            toastContainer.appendChild(toast);
            
            // Show toast
            setTimeout(() => toast.classList.add('show'), 100);
            
            // Auto remove
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 5000);
        },

        createToastContainer: function() {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1050';
            document.body.appendChild(container);
            return container;
        },

        createToastElement: function(message, type) {
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white bg-${type} border-0`;
            toast.setAttribute('role', 'alert');
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            return toast;
        },

        // Local storage helpers
        saveToLocalStorage: function(key, data) {
            try {
                localStorage.setItem(key, JSON.stringify(data));
            } catch (e) {
                console.warn('Could not save to localStorage:', e);
            }
        },

        loadFromLocalStorage: function(key) {
            try {
                const data = localStorage.getItem(key);
                return data ? JSON.parse(data) : null;
            } catch (e) {
                console.warn('Could not load from localStorage:', e);
                return null;
            }
        },

        // Validate file
        validateFile: function(file) {
            const errors = [];
            
            if (!CONFIG.ALLOWED_FILE_TYPES.includes(file.type)) {
                errors.push('Please select a valid image file (JPEG, PNG, or GIF)');
            }
            
            if (file.size > CONFIG.MAX_FILE_SIZE) {
                errors.push('File size must be less than 16MB');
            }
            
            return errors;
        }
    };

    // Geolocation manager
    const GeolocationManager = {
        getCurrentPosition: function() {
            return new Promise((resolve, reject) => {
                if (!navigator.geolocation) {
                    reject(new Error('Geolocation is not supported by this browser'));
                    return;
                }

                const options = {
                    enableHighAccuracy: true,
                    timeout: CONFIG.GEOLOCATION_TIMEOUT,
                    maximumAge: CONFIG.GEOLOCATION_MAX_AGE
                };

                navigator.geolocation.getCurrentPosition(resolve, reject, options);
            });
        },

        watchPosition: function(callback) {
            if (!navigator.geolocation) return null;

            const options = {
                enableHighAccuracy: true,
                timeout: CONFIG.GEOLOCATION_TIMEOUT,
                maximumAge: CONFIG.GEOLOCATION_MAX_AGE
            };

            return navigator.geolocation.watchPosition(callback, (error) => {
                console.warn('Geolocation watch error:', error);
            }, options);
        }
    };

    // Report form manager
    const ReportFormManager = {
        init: function() {
            const reportForm = document.getElementById('reportForm');
            if (!reportForm) return;

            this.setupFormHandlers();
            this.setupAutoSave();
            this.loadDraftData();
        },

        setupFormHandlers: function() {
            // Photo upload handling
            const photoInput = document.getElementById('photo');
            if (photoInput) {
                photoInput.addEventListener('change', this.handlePhotoUpload.bind(this));
            }

            // Location button
            const locationBtn = document.getElementById('getLocationBtn');
            if (locationBtn) {
                locationBtn.addEventListener('click', this.handleLocationRequest.bind(this));
            }

            // Form submission
            const form = document.getElementById('reportForm');
            if (form) {
                form.addEventListener('submit', this.handleFormSubmit.bind(this));
            }

            // Auto-expand textareas
            const textareas = document.querySelectorAll('textarea');
            textareas.forEach(textarea => {
                textarea.addEventListener('input', this.autoResizeTextarea);
            });
        },

        handlePhotoUpload: function(event) {
            const file = event.target.files[0];
            const preview = document.getElementById('photoPreview');
            
            if (!file) {
                preview.innerHTML = '';
                return;
            }

            const errors = Utils.validateFile(file);
            if (errors.length > 0) {
                Utils.showToast(errors.join('. '), 'danger');
                event.target.value = '';
                preview.innerHTML = '';
                return;
            }

            // Show loading state
            preview.innerHTML = '<div class="text-center p-3"><i class="fas fa-spinner fa-spin"></i> Processing image...</div>';

            // Create image preview
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.className = 'photo-preview img-thumbnail mt-2';
                img.alt = 'Photo preview';
                
                // Add image info
                const info = document.createElement('div');
                info.className = 'small text-muted mt-1';
                info.innerHTML = `
                    <i class="fas fa-info-circle"></i> 
                    ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)
                `;
                
                preview.innerHTML = '';
                preview.appendChild(img);
                preview.appendChild(info);
                
                Utils.showToast('Photo uploaded successfully!', 'success');
            };
            
            reader.onerror = function() {
                preview.innerHTML = '';
                Utils.showToast('Error reading file. Please try again.', 'danger');
            };
            
            reader.readAsDataURL(file);
        },

        handleLocationRequest: function(event) {
            const btn = event.target;
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Getting Location...';
            btn.disabled = true;

            GeolocationManager.getCurrentPosition()
                .then((position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    const accuracy = position.coords.accuracy;

                    // Update form fields
                    document.getElementById('latitude').value = lat.toFixed(6);
                    document.getElementById('longitude').value = lng.toFixed(6);

                    // Show location info
                    this.showLocationInfo(lat, lng, accuracy);

                    btn.innerHTML = '<i class="fas fa-check text-success me-1"></i>Location Captured';
                    btn.classList.add('btn-outline-success');
                    btn.classList.remove('btn-outline-primary');
                    
                    Utils.showToast('Location captured successfully!', 'success');
                })
                .catch((error) => {
                    let errorMsg = 'Unable to get location. ';
                    
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            errorMsg += 'Location access was denied. Please enable location services and try again.';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMsg += 'Location information is unavailable.';
                            break;
                        case error.TIMEOUT:
                            errorMsg += 'Location request timed out.';
                            break;
                        default:
                            errorMsg += error.message || 'An unknown error occurred.';
                            break;
                    }
                    
                    Utils.showToast(errorMsg, 'danger');
                    btn.innerHTML = originalText;
                })
                .finally(() => {
                    btn.disabled = false;
                });
        },

        showLocationInfo: function(lat, lng, accuracy) {
            const locationInfo = document.getElementById('locationInfo');
            const locationDetails = document.getElementById('locationDetails');
            
            if (locationInfo && locationDetails) {
                locationDetails.innerHTML = `
                    <strong>Coordinates:</strong> ${lat.toFixed(6)}, ${lng.toFixed(6)}<br>
                    <strong>Accuracy:</strong> ±${accuracy.toFixed(0)} meters<br>
                    <small class="text-muted">Captured at ${Utils.formatDate(new Date())}</small>
                `;
                locationInfo.style.display = 'block';
                locationInfo.classList.add('animate__animated', 'animate__fadeIn');
            }
        },

        handleFormSubmit: function(event) {
            if (!this.validateForm()) {
                event.preventDefault();
                return;
            }

            // Show loading state
            const submitBtn = event.target.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting Report...';
                submitBtn.disabled = true;
            }

            // Clear draft data on successful submission
            Utils.saveToLocalStorage('reportDraft', null);
        },

        validateForm: function() {
            const required = ['title', 'description', 'incident_type', 'incident_date'];
            let isValid = true;
            const errors = [];

            // Clear previous validation states
            document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            document.querySelectorAll('.invalid-feedback').forEach(el => el.remove());

            required.forEach(fieldName => {
                const field = document.getElementById(fieldName);
                if (field && !field.value.trim()) {
                    field.classList.add('is-invalid');
                    this.addFieldError(field, 'This field is required');
                    errors.push(`${fieldName.replace('_', ' ')} is required`);
                    isValid = false;
                }
            });

            // Validate description length
            const description = document.getElementById('description');
            if (description && description.value.trim().length < 20) {
                description.classList.add('is-invalid');
                this.addFieldError(description, 'Please provide a more detailed description (at least 20 characters)');
                errors.push('Description must be at least 20 characters');
                isValid = false;
            }

            // Validate incident date
            const incidentDate = document.getElementById('incident_date');
            if (incidentDate && incidentDate.value) {
                const selectedDate = new Date(incidentDate.value);
                const today = new Date();
                today.setHours(23, 59, 59, 999); // End of today
                
                if (selectedDate > today) {
                    incidentDate.classList.add('is-invalid');
                    this.addFieldError(incidentDate, 'Incident date cannot be in the future');
                    errors.push('Incident date cannot be in the future');
                    isValid = false;
                }
            }

            if (!isValid) {
                Utils.showToast('Please correct the errors in the form', 'danger');
                // Scroll to first error
                const firstError = document.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }

            return isValid;
        },

        addFieldError: function(field, message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.textContent = message;
            field.parentNode.appendChild(errorDiv);
        },

        autoResizeTextarea: function(event) {
            const textarea = event.target;
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        },

        setupAutoSave: function() {
            const form = document.getElementById('reportForm');
            if (!form) return;

            const saveFormData = Utils.debounce(() => {
                const formData = new FormData(form);
                const data = {};
                
                for (let [key, value] of formData.entries()) {
                    if (key !== 'photo') { // Don't save file data
                        data[key] = value;
                    }
                }
                
                Utils.saveToLocalStorage('reportDraft', data);
            }, 2000);

            // Save on input changes
            form.addEventListener('input', saveFormData);
            form.addEventListener('change', saveFormData);
        },

        loadDraftData: function() {
            const draftData = Utils.loadFromLocalStorage('reportDraft');
            if (!draftData) return;

            // Ask user if they want to restore draft
            if (confirm('We found a saved draft of your report. Would you like to restore it?')) {
                Object.keys(draftData).forEach(key => {
                    const field = document.getElementById(key);
                    if (field && draftData[key]) {
                        field.value = draftData[key];
                    }
                });
                
                Utils.showToast('Draft restored successfully!', 'info');
            }
        }
    };

    // Dashboard manager
    const DashboardManager = {
        init: function() {
            if (!document.querySelector('.dashboard-container')) return;
            
            this.setupFilters();
            this.setupAutoRefresh();
            this.setupReportCards();
        },

        setupFilters: function() {
            const filterButtons = document.querySelectorAll('input[name="reportFilter"]');
            if (!filterButtons.length) return;

            filterButtons.forEach(button => {
                button.addEventListener('change', this.handleFilterChange.bind(this));
            });
        },

        handleFilterChange: function(event) {
            const filter = event.target.id.replace('filter', '').toLowerCase();
            const reportItems = document.querySelectorAll('.report-item');
            
            reportItems.forEach(item => {
                const status = item.dataset.status;
                const shouldShow = filter === 'all' || status === filter;
                
                item.style.display = shouldShow ? 'block' : 'none';
                
                // Add animation
                if (shouldShow) {
                    item.style.animation = 'fadeIn 0.3s ease-out';
                }
            });

            // Update filter count
            const visibleCount = document.querySelectorAll('.report-item:not([style*="display: none"])').length;
            const filterLabel = event.target.nextElementSibling;
            if (filterLabel) {
                filterLabel.setAttribute('data-count', visibleCount);
            }
        },

        setupAutoRefresh: function() {
            // Only for authority users
            const isAuthority = document.body.dataset.userType === 'authority';
            if (!isAuthority) return;

            let refreshInterval;
            let isPageVisible = !document.hidden;

            // Setup visibility change handler
            document.addEventListener('visibilitychange', () => {
                isPageVisible = !document.hidden;
                
                if (isPageVisible && !refreshInterval) {
                    refreshInterval = setInterval(this.refreshData.bind(this), 30000);
                } else if (!isPageVisible && refreshInterval) {
                    clearInterval(refreshInterval);
                    refreshInterval = null;
                }
            });

            // Start refresh if page is visible
            if (isPageVisible) {
                refreshInterval = setInterval(this.refreshData.bind(this), 30000);
            }
        },

        refreshData: function() {
            // Simple refresh - could be enhanced with AJAX in the future
            if (!document.hidden) {
                location.reload();
            }
        },

        setupReportCards: function() {
            const reportCards = document.querySelectorAll('.report-card');
            
            reportCards.forEach(card => {
                // Add click handler for mobile
                if (window.innerWidth <= 768) {
                    card.addEventListener('click', function() {
                        this.classList.toggle('expanded');
                    });
                }
                
                // Add lazy loading for images if any
                const images = card.querySelectorAll('img[data-src]');
                images.forEach(img => {
                    const observer = new IntersectionObserver((entries) => {
                        entries.forEach(entry => {
                            if (entry.isIntersecting) {
                                img.src = img.dataset.src;
                                img.removeAttribute('data-src');
                                observer.unobserve(img);
                            }
                        });
                    });
                    observer.observe(img);
                });
            });
        }
    };

    // Navigation enhancement
    const NavigationManager = {
        init: function() {
            this.setupMobileMenu();
            this.setupScrollBehavior();
            this.highlightActiveNavItem();
        },

        setupMobileMenu: function() {
            const navToggler = document.querySelector('.navbar-toggler');
            const navMenu = document.querySelector('.navbar-collapse');
            
            if (!navToggler || !navMenu) return;

            // Close menu when clicking outside
            document.addEventListener('click', (event) => {
                const isClickInsideNav = navMenu.contains(event.target) || navToggler.contains(event.target);
                
                if (!isClickInsideNav && navMenu.classList.contains('show')) {
                    navToggler.click();
                }
            });

            // Close menu when clicking nav links
            const navLinks = navMenu.querySelectorAll('.nav-link');
            navLinks.forEach(link => {
                link.addEventListener('click', () => {
                    if (navMenu.classList.contains('show')) {
                        navToggler.click();
                    }
                });
            });
        },

        setupScrollBehavior: function() {
            const navbar = document.querySelector('.navbar');
            if (!navbar) return;

            let lastScrollTop = 0;
            
            window.addEventListener('scroll', Utils.debounce(() => {
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                
                if (scrollTop > lastScrollTop && scrollTop > 100) {
                    // Scrolling down
                    navbar.style.transform = 'translateY(-100%)';
                } else {
                    // Scrolling up
                    navbar.style.transform = 'translateY(0)';
                }
                
                lastScrollTop = scrollTop;
            }, 10));
        },

        highlightActiveNavItem: function() {
            const currentPath = window.location.pathname;
            const navLinks = document.querySelectorAll('.nav-link');
            
            navLinks.forEach(link => {
                const linkPath = new URL(link.href).pathname;
                if (linkPath === currentPath) {
                    link.classList.add('active');
                }
            });
        }
    };

    // Performance monitoring
    const PerformanceMonitor = {
        init: function() {
            this.monitorPageLoad();
            this.monitorUserInteractions();
        },

        monitorPageLoad: function() {
            window.addEventListener('load', () => {
                if ('performance' in window) {
                    const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
                    console.log(`Page load time: ${loadTime}ms`);
                    
                    // Log slow page loads
                    if (loadTime > 3000) {
                        console.warn('Slow page load detected');
                    }
                }
            });
        },

        monitorUserInteractions: function() {
            // Monitor long tasks
            if ('PerformanceObserver' in window) {
                const observer = new PerformanceObserver((list) => {
                    list.getEntries().forEach((entry) => {
                        if (entry.duration > 50) {
                            console.warn('Long task detected:', entry);
                        }
                    });
                });
                
                try {
                    observer.observe({entryTypes: ['longtask']});
                } catch (e) {
                    // Longtask not supported
                }
            }
        }
    };

    // Initialize application
    function initApp() {
        // Core initialization
        NavigationManager.init();
        ReportFormManager.init();
        DashboardManager.init();
        PerformanceMonitor.init();

        // Enhanced form interactions
        initFormEnhancements();
        
        // Setup accessibility features
        initAccessibilityFeatures();
        
        console.log('Community Mangrove Watch app initialized');
    }

    function initFormEnhancements() {
        // Enhanced form validation feedback
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    if (this.hasAttribute('required') && !this.value.trim()) {
                        this.classList.add('is-invalid');
                    } else {
                        this.classList.remove('is-invalid');
                    }
                });
            });
        });

        // Password strength indicator
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        passwordInputs.forEach(input => {
            if (input.id === 'password') {
                input.addEventListener('input', function() {
                    const strength = calculatePasswordStrength(this.value);
                    showPasswordStrength(this, strength);
                });
            }
        });
    }

    function calculatePasswordStrength(password) {
        let score = 0;
        if (password.length >= 8) score++;
        if (/[a-z]/.test(password)) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/[0-9]/.test(password)) score++;
        if (/[^A-Za-z0-9]/.test(password)) score++;
        return score;
    }

    function showPasswordStrength(input, strength) {
        let existingIndicator = input.parentNode.querySelector('.password-strength');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        if (input.value.length === 0) return;

        const indicator = document.createElement('div');
        indicator.className = 'password-strength small mt-1';
        
        const strengthTexts = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
        const strengthColors = ['danger', 'danger', 'warning', 'info', 'success'];
        
        indicator.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="text-${strengthColors[strength - 1] || 'danger'}">
                    ${strengthTexts[strength - 1] || 'Very Weak'}
                </span>
                <div class="progress flex-grow-1 ms-2" style="height: 4px;">
                    <div class="progress-bar bg-${strengthColors[strength - 1] || 'danger'}" 
                         style="width: ${(strength / 5) * 100}%"></div>
                </div>
            </div>
        `;
        
        input.parentNode.appendChild(indicator);
    }

    function initAccessibilityFeatures() {
        // Keyboard navigation enhancement
        document.addEventListener('keydown', function(e) {
            // Skip to main content with Alt+M
            if (e.altKey && e.key === 'm') {
                e.preventDefault();
                const main = document.querySelector('main');
                if (main) {
                    main.focus();
                    main.scrollIntoView();
                }
            }
        });

        // High contrast mode detection
        if (window.matchMedia && window.matchMedia('(prefers-contrast: high)').matches) {
            document.body.classList.add('high-contrast');
        }

        // Reduced motion detection
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.body.classList.add('reduced-motion');
        }
    }

    // Start the application when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApp);
    } else {
        initApp();
    }

    // Expose utilities globally for use in templates
    window.MangroveWatch = {
        Utils,
        GeolocationManager,
        showToast: Utils.showToast
    };

})();
