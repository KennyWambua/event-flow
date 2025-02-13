document.addEventListener('DOMContentLoaded', function() {
  const mobileMenuBtn = document.querySelector('.mobileMenuBtn');
  const menuIcon = document.querySelector('.mobileMenuBtn .material-icons');
  const navSection = document.querySelector('.navSection');
  const dropdowns = document.querySelectorAll('.dropdown');

  // Toggle mobile menu
  mobileMenuBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    navSection.classList.toggle('active');
    menuIcon.textContent = navSection.classList.contains('active') ? 'close' : 'menu';
  });

  // Handle dropdowns in mobile view
  dropdowns.forEach(dropdown => {
    const button = dropdown.querySelector('.dropdownTitle');
    const content = dropdown.querySelector('.dropdownContent');

    button.addEventListener('click', function(e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        e.stopPropagation();

        // Close other dropdowns
        dropdowns.forEach(other => {
          if (other !== dropdown) {
            other.classList.remove('active');
          }
        });

        dropdown.classList.toggle('active');
      }
    });
  });

  // Close menu when clicking outside
  document.addEventListener('click', function(e) {
    if (!navSection.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
      navSection.classList.remove('active');
      menuIcon.textContent = 'menu';
      dropdowns.forEach(dropdown => {
        dropdown.classList.remove('active');
      });
    }
  });

  // Close menu when window is resized above mobile breakpoint
  window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
      navSection.classList.remove('active');
      menuIcon.textContent = 'menu';
      dropdowns.forEach(dropdown => {
        dropdown.classList.remove('active');
      });
    }
  });

  // Flash Messages
  const flashMessages = document.querySelectorAll('.flash-message');
  
  flashMessages.forEach(message => {
    // Add click handler for close button
    const closeBtn = message.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        message.classList.add('fade-out');
        setTimeout(() => {
          message.remove();
        }, 300);
      });
    }

    // Auto dismiss after 5 seconds
    setTimeout(() => {
      if (message && message.isConnected) {
        message.classList.add('fade-out');
        setTimeout(() => {
          if (message && message.isConnected) {
            message.remove();
          }
        }, 300);
      }
    }, 5000);
  });
}); 