document.addEventListener('DOMContentLoaded', () => {
    
    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Optional: Add a simple glow pulse to the Hero Image on load
    const heroImg = document.querySelector('.hero-image img');
    if(heroImg) {
        heroImg.style.opacity = '0';
        heroImg.style.transition = 'opacity 1.5s ease-in-out';
        setTimeout(() => {
            heroImg.style.opacity = '1';
        }, 200);
    }
});