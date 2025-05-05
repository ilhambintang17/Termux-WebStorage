// Custom JavaScript for Termux NAS

document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Add active class to current nav item
    var currentLocation = window.location.pathname;
    var navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(function(link) {
        var linkPath = link.getAttribute('href');
        if (linkPath && currentLocation.startsWith(linkPath) && linkPath !== '/') {
            link.classList.add('active');
        }
    });
    
    // Handle file selection in file browser
    var fileItems = document.querySelectorAll('.file-item');
    fileItems.forEach(function(item) {
        item.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || 
                e.target.parentElement.tagName === 'A' || e.target.parentElement.tagName === 'BUTTON') {
                e.stopPropagation();
                return;
            }
            
            var url = item.getAttribute('data-url');
            if (url) {
                window.location.href = url;
            }
        });
    });
    
    // Handle theme switching
    var themeLinks = document.querySelectorAll('[data-theme]');
    themeLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            var theme = this.getAttribute('data-theme');
            document.documentElement.setAttribute('data-bs-theme', theme);
            
            // Save theme preference via AJAX
            fetch('/auth/theme/' + theme, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        });
    });
    
    // Handle copy to clipboard
    var copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            var textToCopy = this.getAttribute('data-copy');
            var tempInput = document.createElement('input');
            tempInput.value = textToCopy;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            
            // Show copied feedback
            var originalText = this.innerHTML;
            this.innerHTML = '<i class="bi bi-check"></i> Copied!';
            setTimeout(function() {
                button.innerHTML = originalText;
            }, 2000);
        });
    });
    
    // Handle mobile navigation
    var navbarToggler = document.querySelector('.navbar-toggler');
    var navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        document.addEventListener('click', function(e) {
            if (navbarCollapse.classList.contains('show') && 
                !navbarCollapse.contains(e.target) && 
                !navbarToggler.contains(e.target)) {
                navbarToggler.click();
            }
        });
    }
    
    // Handle file preview loading
    var previewContainer = document.querySelector('.preview-container');
    if (previewContainer) {
        previewContainer.classList.add('fade-in');
    }
    
    // Handle responsive tables
    var tables = document.querySelectorAll('table');
    tables.forEach(function(table) {
        if (!table.parentElement.classList.contains('table-responsive')) {
            var wrapper = document.createElement('div');
            wrapper.classList.add('table-responsive');
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
});
