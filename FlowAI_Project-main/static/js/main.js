document.addEventListener('DOMContentLoaded', () => {
    // Animate hero stat counters when they scroll into view
    const counters = document.querySelectorAll('[data-count-to]');
    if (counters.length) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                const el = entry.target;
                const target = parseFloat(el.dataset.countTo);
                const suffix = el.dataset.suffix || '';
                const duration = 1400;
                const start = performance.now();

                function tick(now) {
                    const progress = Math.min((now - start) / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    const value = Math.floor(eased * target);
                    el.textContent = value.toLocaleString() + suffix;
                    if (progress < 1) requestAnimationFrame(tick);
                }
                requestAnimationFrame(tick);
                observer.unobserve(el);
            });
        }, { threshold: 0.4 });

        counters.forEach((el) => observer.observe(el));
    }

    // Subtle navbar shadow after scrolling
    const nav = document.querySelector('.navbar-glass');
    if (nav) {
        window.addEventListener('scroll', () => {
            nav.style.boxShadow = window.scrollY > 12
                ? '0 8px 24px rgba(0,0,0,0.35)'
                : 'none';
        });
    }
});
