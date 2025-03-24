document.addEventListener('DOMContentLoaded', function () {
  const mobileMenuBtn = document.querySelector('.mobileMenuBtn');
  const menuIcon = document.querySelector('.mobileMenuBtn .material-icons');
  const navSection = document.querySelector('.navSection');
  const dropdowns = document.querySelectorAll('.dropdown');
  const userMenu = document.querySelector('.user-menu');
  const userMenuTrigger = userMenu?.querySelector('.user-menu-trigger');
  const userMenuDropdown = userMenu?.querySelector('.user-menu-dropdown');
  const navbar = document.querySelector('.navbar');
  let userMenuTimeout;

  // Initialize menu icon
  if (menuIcon && !menuIcon.textContent) {
    menuIcon.textContent = 'menu';
  }

  // Show navbar in mobile view
  if (navbar) {
    navbar.style.display = 'block';
  }

  // Toggle mobile menu
  mobileMenuBtn?.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    
    const isActive = navSection.classList.contains('active');
    
    // Close all menus first
    navSection.classList.remove('active');
    userMenu?.classList.remove('active');
    dropdowns.forEach(dropdown => dropdown.classList.remove('active'));
    
    // Then toggle nav menu if it wasn't active
    if (!isActive) {
      navSection.classList.add('active');
      menuIcon.textContent = 'close';
      document.body.style.overflow = 'hidden';
    } else {
      menuIcon.textContent = 'menu';
      document.body.style.overflow = '';
    }
  });

  // Handle dropdowns in mobile view
  dropdowns.forEach(dropdown => {
    const dropdownTitle = dropdown.querySelector('.dropdownTitle');
    const dropdownContent = dropdown.querySelector('.dropdownContent');

    dropdownTitle?.addEventListener('click', function (e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        e.stopPropagation();
        
        // Close other dropdowns
        dropdowns.forEach(otherDropdown => {
          if (otherDropdown !== dropdown) {
            otherDropdown.classList.remove('active');
          }
        });

        dropdown.classList.toggle('active');
      }
    });

    // Prevent click propagation on dropdown content
    dropdownContent?.addEventListener('click', function (e) {
      if (window.innerWidth <= 768) {
        e.stopPropagation();
      }
    });
  });

  // Handle user menu
  if (userMenuTrigger && userMenu) {
    userMenuTrigger.addEventListener('click', function (e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        e.stopPropagation();
        
        // Close nav menu if open
        navSection.classList.remove('active');
        menuIcon.textContent = 'menu';
        document.body.style.overflow = '';
        
        // Toggle user menu and update aria-expanded
        const isActive = userMenu.classList.toggle('active');
        userMenuTrigger.setAttribute('aria-expanded', isActive ? 'true' : 'false');
        
        // Toggle body scroll based on user menu state
        document.body.style.overflow = isActive ? 'hidden' : '';
      }
    });
  
    // Add hover functionality for desktop
    if (window.innerWidth > 768) {
      userMenuTrigger.addEventListener('mouseenter', function() {
        clearTimeout(userMenuTimeout);
        userMenu.classList.add('active');
        userMenuTrigger.setAttribute('aria-expanded', 'true');
      });

      userMenuTrigger.addEventListener('mouseleave', function(e) {
        // Check if the mouse is moving to the dropdown
        const dropdownBox = userMenuDropdown.getBoundingClientRect();
        if (!(e.clientX >= dropdownBox.left && 
              e.clientX <= dropdownBox.right && 
              e.clientY >= dropdownBox.top && 
              e.clientY <= dropdownBox.bottom)) {
          userMenuTimeout = setTimeout(() => {
            console.log('Checking if should close menu');
            // Only close if mouse is not over dropdown
            if (!userMenuDropdown.matches(':hover')) {
              console.log('Closing menu - Mouse not over dropdown');
              userMenu.classList.remove('active');
              userMenuTrigger.setAttribute('aria-expanded', 'false');
            } else {
            }
          }, 3000);
        } else {
        }
      });

      // Keep menu open when hovering over dropdown
      userMenuDropdown.addEventListener('mouseenter', function() {
        clearTimeout(userMenuTimeout);
      });

      userMenuDropdown.addEventListener('mouseleave', function(e) {
        // Check if the mouse is moving back to trigger
        const triggerBox = userMenuTrigger.getBoundingClientRect();
        if (!(e.clientX >= triggerBox.left && 
              e.clientX <= triggerBox.right && 
              e.clientY >= triggerBox.top && 
              e.clientY <= triggerBox.bottom)) {
          userMenuTimeout = setTimeout(() => {
            userMenu.classList.remove('active');
            userMenuTrigger.setAttribute('aria-expanded', 'false');
          }, 3000);
        } else {
        }
      });
    }

    // Prevent user menu dropdown clicks from closing the menu on mobile
    userMenuDropdown?.addEventListener('click', function (e) {
      if (window.innerWidth <= 768) {
        e.stopPropagation();
      }
    });
  }
  

  // Close menus when clicking outside
  document.addEventListener('click', function (e) {
    const isClickInsideNav = navSection?.contains(e.target);
    const isClickOnMenuBtn = mobileMenuBtn?.contains(e.target);
    const isClickInsideUserMenu = userMenu?.contains(e.target);
    
    // Close navigation menu if clicked outside
    if (!isClickInsideNav && !isClickOnMenuBtn && navSection?.classList.contains('active')) {
      navSection.classList.remove('active');
      menuIcon.textContent = 'menu';
      document.body.style.overflow = '';
      dropdowns.forEach(dropdown => dropdown.classList.remove('active'));
    }

    // Close user menu if clicked outside (with delay on desktop)
    if (!isClickInsideUserMenu && userMenu?.classList.contains('active')) {
      if (window.innerWidth <= 768) {
        userMenu.classList.remove('active');
        document.body.style.overflow = '';
      } else {
        console.log('Click outside menu - Starting 3s timeout');
        clearTimeout(userMenuTimeout);
        userMenuTimeout = setTimeout(() => {
          console.log('Timeout complete - Closing menu after click outside');
          userMenu.classList.remove('active');
          userMenuTrigger.setAttribute('aria-expanded', 'false');
        }, 3000); // Increased to 3 seconds
      }
    }
  });

  // Handle window resize
  let resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      const width = window.innerWidth;
      
      // Reset all states when transitioning between mobile and desktop
      navSection.classList.remove('active');
      menuIcon.textContent = 'menu';
      document.body.style.overflow = '';
      userMenu?.classList.remove('active');
      dropdowns.forEach(dropdown => dropdown.classList.remove('active'));

      // Show navbar at all screen sizes
      if (navbar) {
        navbar.style.display = 'block';
      }
    }, 250);
  });

  // Handle flash messages
  const flashMessages = document.querySelectorAll('.flash-message');
  flashMessages.forEach(message => {
    const closeBtn = message.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        message.classList.add('fade-out');
        setTimeout(() => message.remove(), 300);
      });
    }
    
    // Auto-hide after 5 seconds
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