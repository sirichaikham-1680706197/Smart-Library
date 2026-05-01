// ══════════════════════════════════════════════════════════
// Smart Digital Library — Main JavaScript
// ══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initAnimations();
    initAutoAlerts();
    initSearchFilter();
});

// ── Scroll Animations ─────────────────────────────────────
function initAnimations() {
    const cards = document.querySelectorAll('.item-card, .stat-card, .glass-card');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                entry.target.style.animationDelay = `${index * 0.08}s`;
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    cards.forEach(card => observer.observe(card));
}

// ── Auto-dismiss Alerts ───────────────────────────────────
function initAutoAlerts() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s, transform 0.5s';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 500);
        }, 4000);
    });
}

// ── Live Search Filter ────────────────────────────────────
function initSearchFilter() {
    const liveSearch = document.getElementById('liveSearch');
    if (!liveSearch) return;
    liveSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const cards = document.querySelectorAll('[data-searchable]');
        cards.forEach(card => {
            const text = card.getAttribute('data-searchable').toLowerCase();
            card.closest('.col').style.display = text.includes(query) ? '' : 'none';
        });
    });
}

// ── Confirm Dialogs ───────────────────────────────────────
function confirmAction(msg) {
    return confirm(msg || 'คุณแน่ใจหรือไม่?');
}
