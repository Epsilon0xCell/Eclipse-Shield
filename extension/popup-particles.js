// Particle trail for the popup, moved out of popup.html.
// Manifest V3 extension pages cannot run inline scripts, so the
// inline block that used to live in popup.html silently never ran
// when the page was loaded as an extension page.
        // Add particle system
        function createParticle(x, y) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            document.body.appendChild(particle);

            // Randomize particle properties
            const size = Math.random() * 8 + 4;
            const destinationX = x + (Math.random() - 0.5) * 50;
            const destinationY = y + (Math.random() - 0.5) * 50;
            const rotation = Math.random() * 520;
            const delay = Math.random() * 200;

            // Set particle styles
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            particle.style.left = `${x}px`;
            particle.style.top = `${y}px`;
            particle.style.transform = `translate(-50%, -50%)`;
            particle.style.animation = `particle-fade 1s ease-out ${delay}ms`;

            // Remove particle after animation
            setTimeout(() => particle.remove(), 1000 + delay);
        }

        // Add mousemove listener for particle creation
        let throttleTimer;
        document.addEventListener('mousemove', (e) => {
            if (!throttleTimer) {
                throttleTimer = setTimeout(() => {
                    createParticle(e.clientX, e.clientY);
                    throttleTimer = null;
                }, 50); // Adjust this value to control particle density
            }
        });

        // Prevent default form submission
        document.addEventListener('submit', (e) => {
            e.preventDefault();
        });
