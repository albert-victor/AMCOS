// Mkuu wa Mkoa - Main Application JavaScript

document.addEventListener('DOMContentLoaded', function () {
    initPageModuleEnter();

    // Mobile sidebar toggle + backdrop
    const hamburger = document.getElementById('hamburger');
    const sidebar = document.getElementById('sidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
        document.body.classList.remove('sidebar-open');
    }

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.add('active');
        document.body.classList.add('sidebar-open');
    }

    if (hamburger && sidebar) {
        hamburger.addEventListener('click', function () {
            if (sidebar.classList.contains('open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', closeSidebar);
    }

    document.querySelectorAll('.sidebar .nav-item').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.innerWidth <= 768) closeSidebar();
        });
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 768) closeSidebar();
    });

    // Auth password visibility toggle
    document.querySelectorAll('.auth-toggle-pw').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var targetId = this.dataset.target;
            var input = targetId ? document.getElementById(targetId) : this.closest('.auth-input-wrap').querySelector('input');
            var icon = this.querySelector('i');
            if (!input) return;
            if (input.type === 'password') {
                input.type = 'text';
                if (icon) { icon.classList.remove('fa-eye'); icon.classList.add('fa-eye-slash'); }
            } else {
                input.type = 'password';
                if (icon) { icon.classList.remove('fa-eye-slash'); icon.classList.add('fa-eye'); }
            }
        });
    });

    // Dropdown menus (animated)
    function closeAllDropdowns() {
        document.querySelectorAll('.dropdown.is-open').forEach(function (wrap) {
            wrap.classList.remove('is-open');
            var menu = wrap.querySelector('.dropdown-menu');
            var toggle = wrap.querySelector('.dropdown-toggle');
            if (menu) menu.classList.remove('show');
            if (toggle) toggle.setAttribute('aria-expanded', 'false');
        });
    }

    document.querySelectorAll('.dropdown-toggle').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var wrap = this.closest('.dropdown');
            var menu = this.nextElementSibling;
            if (!menu || !wrap) return;
            var willOpen = !menu.classList.contains('show');
            closeAllDropdowns();
            if (willOpen) {
                wrap.classList.add('is-open');
                menu.classList.add('show');
                this.setAttribute('aria-expanded', 'true');
            }
        });
    });

    document.addEventListener('click', function () {
        closeAllDropdowns();
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeAllDropdowns();
    });

    // Auto-dismiss alerts
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Modal handlers
    document.querySelectorAll('[data-modal]').forEach(btn => {
        btn.addEventListener('click', function () {
            const modalId = this.dataset.modal;
            const modal = document.getElementById(modalId);
            if (modal) modal.classList.add('active');
        });
    });

    document.querySelectorAll('.modal-close, .modal-overlay').forEach(el => {
        el.addEventListener('click', function () {
            document.querySelectorAll('.modal-overlay.active').forEach(m => {
                m.classList.remove('active');
            });
        });
    });

    // Confirm actions
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', function (e) {
            if (!confirm(this.dataset.confirm || 'Are you sure?')) {
                e.preventDefault();
            }
        });
    });

    // Select all checkbox
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
        selectAll.addEventListener('change', function () {
            document.querySelectorAll('.select-item').forEach(cb => {
                cb.checked = this.checked;
            });
        });
    }

    // Dynamic search
    document.querySelectorAll('[data-search]').forEach(input => {
        input.addEventListener('keyup', function () {
            const query = this.value.toLowerCase();
            const target = document.querySelector(this.dataset.search);
            if (target) {
                target.querySelectorAll('tr').forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(query) ? '' : 'none';
                });
            }
        });
    });

    // Print functionality
    document.querySelectorAll('[data-print]').forEach(btn => {
        btn.addEventListener('click', function () {
            window.print();
        });
    });

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function () {
            const parent = this.parentElement;
            parent.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            const target = document.querySelector(this.dataset.tab);
            if (target) {
                const container = target.parentElement;
                container.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
                target.style.display = 'block';
            }
        });
    });

    // Format currency inputs
    document.querySelectorAll('[data-format="currency"]').forEach(input => {
        input.addEventListener('blur', function () {
            const val = parseFloat(this.value);
            if (!isNaN(val)) {
                this.value = val.toFixed(2);
            }
        });
    });

    // Phone number validation
    document.querySelectorAll('input[type="tel"]').forEach(input => {
        input.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9+]/g, '');
        });
    });

    // Password toggle
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', function () {
            const input = this.previousElementSibling;
            if (input && input.type === 'password') {
                input.type = 'text';
                this.textContent = 'Hide';
            } else if (input) {
                input.type = 'password';
                this.textContent = 'Show';
            }
        });
    });

    highlightActiveNav();
});

/**
 * Fade-up pop animation when a dashboard module page loads (all roles).
 */
function initPageModuleEnter() {
    var view = document.getElementById('pageModuleView');
    if (!view) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        view.classList.add('page-module-view--enter');
        return;
    }
    view.classList.remove('page-module-view--enter');
    void view.offsetWidth;
    requestAnimationFrame(function () {
        view.classList.add('page-module-view--enter');
    });
}

/**
 * Mark the best-matching sidebar link as active (persists until another page load).
 * Uses longest path prefix so /members/5/ highlights Members, not Dashboard.
 */
function highlightActiveNav() {
    var sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    var currentPath = normalizeNavPath(window.location.pathname);
    var currentSearch = window.location.search || '';
    var links = sidebar.querySelectorAll('a.nav-item[href]');
    var bestLink = null;
    var bestScore = -1;

    links.forEach(function (link) {
        var href = link.getAttribute('href');
        if (!href || href === '#') return;

        var parsed;
        try {
            parsed = new URL(href, window.location.origin);
        } catch (e) {
            return;
        }

        var linkPath = normalizeNavPath(parsed.pathname);
        var linkSearch = parsed.search || '';
        var score = scoreNavMatch(linkPath, linkSearch, currentPath, currentSearch);

        if (score > bestScore) {
            bestScore = score;
            bestLink = link;
        }
    });

    links.forEach(function (link) {
        link.classList.remove('active');
        link.removeAttribute('aria-current');
    });

    if (bestLink && bestScore > 0) {
        bestLink.classList.add('active');
        bestLink.setAttribute('aria-current', 'page');
        var menu = sidebar.querySelector('.nav-menu');
        if (menu && typeof bestLink.scrollIntoView === 'function') {
            bestLink.scrollIntoView({ block: 'nearest', behavior: 'instant' in window ? 'instant' : 'auto' });
        }
    }
}

function normalizeNavPath(path) {
    if (!path) return '/';
    var p = path.split('?')[0];
    if (p.length > 1 && p.endsWith('/')) p = p.slice(0, -1);
    return p || '/';
}

function scoreNavMatch(linkPath, linkSearch, currentPath, currentSearch) {
    // Links with ?query only match that exact filtered list page
    if (linkSearch) {
        if (linkPath === currentPath && linkSearch === currentSearch) {
            return 10000 + linkPath.length;
        }
        return 0;
    }

    if (linkPath === currentPath) {
        return 9000 + linkPath.length;
    }

    // Dashboard: exact only (not /dashboard/super-admin/)
    if (linkPath === '/dashboard') {
        return 0;
    }

    // Child routes: /members/12/ under /members
    if (currentPath.indexOf(linkPath + '/') === 0) {
        return linkPath.length;
    }

    return 0;
}

/** One language from html[lang] — matches server {% t %} / KISW–ENG toggle */
function uiMsg(sw, en) {
    var lang = (document.documentElement.lang || 'en').toLowerCase();
    return lang === 'en' ? (en || sw) : sw;
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('sw-TZ', {
        style: 'currency',
        currency: 'TZS'
    }).format(amount);
}

function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('sw-TZ', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateStr) {
    return new Date(dateStr).toLocaleString('sw-TZ', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
