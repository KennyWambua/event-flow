document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('paymentForm');
    const modal = document.getElementById('processingModal');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const phoneInput = document.getElementById("phone").value;
        
        if (!phoneInput || phoneInput.length < 9) {
            alert("Please enter a valid phone number.");
            e.preventDefault();
            return;
        }
        const payButton = document.getElementById('payButton');
        
        // Show processing modal
        modal.style.display = 'flex';
        payButton.disabled = true;
        
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ phone: phoneInput })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Update status message
                const statusStep = modal.querySelector('.status-step span:last-child');
                statusStep.textContent = 'Payment successful! Redirecting...';
                
                // Redirect to tickets page after delay
                setTimeout(() => {
                    window.location.href = '/my-tickets';
                }, 4000);
            } else {
                throw new Error(data.error || 'Payment failed');
            }
        } catch (error) {
            console.error('Payment error:', error);
            modal.style.display = 'none';
            alert(error.message || 'Failed to process payment. Please try again.');
        } finally {
            payButton.disabled = false;
        }
    });
});

function updateProcessingStatus(message) {
    const statusContainer = document.querySelector('.processing-status');
    const statusStep = document.createElement('div');
    statusStep.className = 'status-step current';
    statusStep.innerHTML = `
        <span class="material-icons">info</span>
        <span>${message}</span>
    `;
    
    // Update previous step to not current
    const previousStep = statusContainer.querySelector('.current');
    if (previousStep) {
        previousStep.classList.remove('current');
    }
    
    statusContainer.appendChild(statusStep);
}

function pollPaymentStatus(checkoutRequestId) {
    const pollInterval = setInterval(() => {
        fetch(`/check-payment-status/${checkoutRequestId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'COMPLETED') {
                    updateProcessingStatus('Payment completed successfully');
                    clearInterval(pollInterval);
                    // Redirect to tickets page after short delay
                    setTimeout(() => {
                        window.location.href = '/my-tickets';
                    }, 2000);
                } else if (data.status === 'FAILED') {
                    updateProcessingStatus('Payment failed: ' + data.message);
                    clearInterval(pollInterval);
                    setTimeout(() => {
                        location.reload();
                    }, 3000);
                }
                // Continue polling for 'PENDING' status
            })
            .catch(error => {
                console.error('Error checking payment status:', error);
                clearInterval(pollInterval);
            });
    }, 5000); // Poll every 5 seconds

    // Stop polling after 2 minutes
    setTimeout(() => {
        clearInterval(pollInterval);
        updateProcessingStatus('Payment request timed out. Please try again.');
        setTimeout(() => {
            location.reload();
        }, 3000);
    }, 120000);
} 