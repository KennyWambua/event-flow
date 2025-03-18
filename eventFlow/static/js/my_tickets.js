document.addEventListener('DOMContentLoaded', function () {
  // Delete order
  document.querySelectorAll('.delete-order-btn').forEach(button => {
    button.addEventListener('click', async function () {
      const orderId = this.dataset.orderId;
      console.log('Delete button clicked for order:', orderId);

      if (!confirm('Are you sure you want to delete this order? This action cannot be undone.')) {
        return;
      }

      try {
        // Get CSRF token from meta tag
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (!csrfToken) {
          throw new Error('CSRF token not found');
        }

        console.log('Sending delete request for order:', orderId);
        const response = await fetch(`/delete-order/${orderId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          }
        });

        const data = await response.json();
        console.log('Delete response:', data);

        if (response.ok) {
          // Remove the ticket card from the DOM
          const ticketCard = this.closest('.ticket-card');
          ticketCard.remove();

          // Show success notification
          showNotification('Order deleted successfully', 'success');
        } else {
          throw new Error(data.error || 'Failed to delete order');
        }
      } catch (error) {
        console.error('Error deleting order:', error);
        showNotification(error.message, 'error');
      }
    });
  });

  // Download tickets
  document.querySelectorAll('.download-tickets-btn').forEach(button => {
    button.addEventListener('click', function () {
      const orderId = this.dataset.orderId;
      const originalText = this.innerHTML;
      
      this.innerHTML = '<span class="material-icons loading">sync</span> Processing...';
      this.disabled = true;
      
      // Create a temporary iframe for download
      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.src = `/download-tickets/${orderId}`;
      document.body.appendChild(iframe);
      
      // Reset button after delay
      setTimeout(() => {
        this.innerHTML = originalText;
        this.disabled = false;
        document.body.removeChild(iframe);
      }, 2000);
    });
  });

  // View QR code
  document.querySelectorAll('.view-qr-btn').forEach(button => {
    button.addEventListener('click', async function () {
      const orderId = this.dataset.orderId;
      const modal = document.getElementById('ticketQRModal');
      const qrContainer = document.getElementById('qrCodeContainer');
      
      if (!modal || !qrContainer) {
        console.error('Modal or QR container not found');
        return;
      }
      
      try {
        // Show loading state
        qrContainer.innerHTML = '<span class="material-icons loading">sync</span>';
        modal.style.display = 'flex';
        
        // Fetch QR code image
        const response = await fetch(`/generate-ticket-qr/${orderId}`);
        if (!response.ok) throw new Error('Failed to generate QR code');
        
        const blob = await response.blob();
        const img = document.createElement('img');
        img.src = URL.createObjectURL(blob);
        qrContainer.innerHTML = '';
        qrContainer.appendChild(img);
        
      } catch (error) {
        console.error('Error loading QR code:', error);
        qrContainer.innerHTML = 'Failed to load QR code';
        showNotification('Failed to load QR code', 'error');
      }
    });
  });

  // Close QR modal
  const closeQrModalBtn = document.getElementById('closeQrModal');
  if (closeQrModalBtn) {
    closeQrModalBtn.addEventListener('click', function () {
      const modal = document.getElementById('ticketQRModal');
      if (modal) {
        modal.style.display = 'none';
      }
    });
  }

  // Filter tickets
  document.querySelectorAll('.filter-btn').forEach(button => {
    button.addEventListener('click', function () {
      const filter = this.dataset.filter;
      
      // Update active button
      document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
      });
      this.classList.add('active');
      
      // Filter tickets
      document.querySelectorAll('.ticket-card').forEach(card => {
        if (filter === 'all') {
          card.style.display = 'grid';
        } else {
          card.style.display = card.dataset.status === filter ? 'grid' : 'none';
        }
      });
    });
  });
});

function showNotification(message, type) {
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;

  document.body.appendChild(notification);

  // Remove notification after 3 seconds
  setTimeout(() => {
    notification.remove();
  }, 3000);
} 