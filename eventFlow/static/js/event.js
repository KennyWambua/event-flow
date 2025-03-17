const swiper = new Swiper('.eventSwiper', {
  loop: true,
  pagination: {
    el: '.swiper-pagination',
    clickable: true
  },
  navigation: {
    nextEl: '.swiper-button-next',
    prevEl: '.swiper-button-prev'
  },
  autoplay: {
    delay: 5000,
    disableOnInteraction: false
  }
})

let cart = {}

function scrollToTickets() {
  document.getElementById('tickets').scrollIntoView({ behavior: 'smooth' })
}

function updateQuantity(ticketId, change) {
  const input = document.getElementById(`quantity-${ticketId}`)
  const ticketCard = document.querySelector(`.ticket-card[data-ticket-id="${ticketId}"]`)
  const maxAvailable = parseInt(input.max)

  // Get current total for this ticket type
  const currentValue = parseInt(input.value) || 0
  const newValue = Math.max(0, Math.min(currentValue + change, maxAvailable))

  // Update input value
  input.value = newValue

  // Visual feedback if max reached
  if (newValue >= maxAvailable) {
    ticketCard.classList.add('max-reached')
  } else {
    ticketCard.classList.remove('max-reached')
  }

  updateCart()
}

function updateCart() {
  cart = {}
  let total = 0
  let totalTickets = 0

  document.querySelectorAll('.ticket-card').forEach((card) => {
    const ticketId = card.dataset.ticketId
    const quantity = parseInt(document.getElementById(`quantity-${ticketId}`).value) || 0
    const price = parseFloat(card.dataset.price)
    const ticketName = card.querySelector('h3').textContent
    const maxAvailable = parseInt(document.getElementById(`quantity-${ticketId}`).max)

    if (quantity > 0) {
      if (quantity > maxAvailable) {
        alert(`Only ${maxAvailable} tickets available for ${ticketName}`)
        document.getElementById(`quantity-${ticketId}`).value = maxAvailable
        return updateCart()
      }

      cart[ticketId] = {
        name: ticketName,
        quantity: quantity,
        price: price,
        subtotal: quantity * price
      }
      total += cart[ticketId].subtotal
      totalTickets += quantity
    }
  })

  // Update the review order button visibility
  const reviewButton = document.getElementById('reviewOrderBtn')
  if (reviewButton) {
    reviewButton.style.display = totalTickets > 0 ? 'flex' : 'none'
  }

  // Update cart total
  const cartTotal = document.getElementById('cartTotal')
  if (cartTotal) {
    cartTotal.textContent = `${total.toFixed(2)} ${EVENT_CURRENCY}`
  }

  const checkoutBtn = document.getElementById('checkoutBtn')
  if (checkoutBtn) {
    checkoutBtn.disabled = total === 0
  }

  // Update cart items
  updateCartItems()
}

function updateCartItems() {  
  const cartItems = document.getElementById('cartItems')
  const cartModal = document.getElementById('cartModal')
    
  if (cartItems && cartModal) {
    cartItems.innerHTML = ''
    
    if (Object.keys(cart).length === 0) {
      cartItems.innerHTML = '<div class="empty-cart">Your cart is empty</div>'
      return
    }


    Object.values(cart).forEach(item => {
      const itemHTML = `
        <div class="cart-item">
          <div class="cart-item-details">
            <h4>${item.name}</h4>
            <p>${item.quantity} × ${item.price.toFixed(2)} ${EVENT_CURRENCY}</p>
          </div>
          <div class="cart-item-subtotal">
            ${item.subtotal.toFixed(2)} ${EVENT_CURRENCY}
          </div>
        </div>
      `
      cartItems.innerHTML += itemHTML
    })
  }
}

function showCartModal() {
  const cartModal = document.getElementById('cartModal')
  cartModal.style.display = 'flex'
  updateCartItems()
}

function closeCartModal() {
  const cartModal = document.getElementById('cartModal')
  cartModal.style.display = 'none'
}

function checkout() {
  const checkoutBtn = document.getElementById('checkoutBtn')
  checkoutBtn.disabled = true
  checkoutBtn.innerHTML = '<span class="spinner"></span> Processing...'

  // Validate cart before proceeding
  let totalTickets = 0
  for (const ticketId in cart) {
    totalTickets += cart[ticketId].quantity
    const maxAvailable = parseInt(document.getElementById(`quantity-${ticketId}`).max)
    
    if (cart[ticketId].quantity > maxAvailable) {
      alert(`Sorry, only ${maxAvailable} tickets available for ${cart[ticketId].name}`)
      checkoutBtn.disabled = false
      checkoutBtn.innerHTML = 'Proceed to Checkout'
      return
    }
  }

  if (totalTickets === 0) {
    alert('Please select at least one ticket')
    checkoutBtn.disabled = false
    checkoutBtn.innerHTML = 'Proceed to Checkout'
    return
  }

  // Create order and redirect to payment
  fetch('/create-order', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF_TOKEN
    },
    body: JSON.stringify({
      eventId: EVENT_ID,
      tickets: cart
    })
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok')
      }
      return response.json()
    })
    .then(data => {
      if (data.error) {
        throw new Error(data.error)
      }
      window.location.href = data.redirect_url
    })
    .catch(error => {
      alert('There was an error processing your order. Please try again.')
      checkoutBtn.disabled = false
      checkoutBtn.innerHTML = 'Proceed to Checkout'
    })
}

function shareEvent(platform) {
  const url = encodeURIComponent(window.location.href)
  const title = encodeURIComponent('{{ event.title }}')

  switch (platform) {
    case 'facebook':
      window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}`)
      break
    case 'twitter':
      window.open(`https://twitter.com/intent/tweet?url=${url}&text=${title}`)
      break
    case 'whatsapp':
      window.open(`https://wa.me/?text=${title}%20${url}`)
      break
  }
}

function copyEventLink() {
  navigator.clipboard.writeText(window.location.href)
  // Show success message
  const notification = document.createElement('div')
  notification.className = 'notification success'
  notification.textContent = 'Link copied to clipboard!'
  document.body.appendChild(notification)
  setTimeout(() => notification.remove(), 3000)
}

function registerFreeEvent() {
  document.getElementById('registrationModal').style.display = 'flex';
}

function closeRegistrationModal() {
  document.getElementById('registrationModal').style.display = 'none';
}

function confirmRegistration() {
  const confirmBtn = document.getElementById('confirmRegBtn');
  const originalText = confirmBtn.innerHTML;
  confirmBtn.innerHTML = '<span class="material-icons loading">sync</span> Processing...';
  confirmBtn.disabled = true;

  fetch('/register-free-event', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF_TOKEN
    },
    body: JSON.stringify({
      eventId: EVENT_ID 
    })
  })
  .then(response => {
    return response.json();
  })
  .then(data => {
    if (data.success) {
      window.location.href = data.redirect;
    } else {
      throw new Error(data.message || 'Registration failed');
    }
  })
  .catch(error => {
    alert(error.message || 'Error processing registration. Please try again.');
    confirmBtn.innerHTML = originalText;
    confirmBtn.disabled = false;
  });
}