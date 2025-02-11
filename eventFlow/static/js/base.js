document.addEventListener('DOMContentLoaded', function() {
  const mobileMenuBtn = document.querySelector('.mobileMenuBtn');
  const menuIcon = document.querySelector('.material-icons');
  const navSection = document.querySelector('.navSection');
  const dropdownButtons = document.querySelectorAll('.dropdownTitle');


  mobileMenuBtn.addEventListener('click', function() {
    navSection.classList.toggle('active');
    if (menuIcon.textContent === 'menu') {
      menuIcon.textContent = 'close';
    } else {
      menuIcon.textContent = 'menu';
    }
  });

  dropdownButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        const parentItem = this.closest('.nav-item');

        dropdownButtons.forEach(otherButton => {
          if (otherButton !== this) {
            otherButton.closest('.nav-item').classList.remove('active');
          }
        });

        parentItem.classList.toggle('active')
      }
    });
  });

  // Close mobile menu when clicking outside
  document.addEventListener('click', function(event) {
    const target = event.target;
    if (!target.closest('.headerSection')) {
      navSection.classList.remove('active');
      menuIcon.textContent = 'menu';
      dropdownButtons.forEach(button => {
        button.closest('.nav-item').classList.remove('active');
      });
    }
  });
}); 