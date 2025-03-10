document.addEventListener('DOMContentLoaded', function () {
  const eventType = document.querySelector('input[name="event_type"]:checked');
  const eventForm = document.getElementById('eventForm');
  const imageContainer = document.getElementById('imageContainer');
  const addImageBtn = document.querySelector('.btn-add-image')
  const imageInput = document.querySelector('.image-input-file')
  const maxImages = 5
  let removedImages = new Set();
  let imageCount = 0;

  function selectEventType(element) {
    // Remove selected class from all options
    document.querySelectorAll('.event-type-option').forEach(opt => {
      opt.classList.remove('selected');
    });

    // Add selected class to clicked option
    element.classList.add('selected');

    // Check the radio input
    const radio = element.querySelector('input[type="radio"]');
    radio.checked = true;

    const ticketSection = document.getElementById('ticketSection');

    if (radio.value === 'paid') {
      ticketSection.style.display = 'block';
    } else {
      ticketSection.style.display = 'none';
    }
  }

  function addTicketType() {
    const ticketTypes = document.getElementById('ticketTypes');
    const ticketCount = ticketTypes.children.length;

    const newTicket = document.createElement('div');
    newTicket.className = 'ticket-type-item';
    newTicket.innerHTML = `
					<div class="ticket-type-header">
							<h4>Ticket Type <span class="ticket-counter">${ticketCount + 1}</span></h4>
							<button type="button" class="remove-ticket" onclick="this.closest('.ticket-type-item').remove()">
									<span class="material-icons">delete</span>
									Remove
							</button>
					</div>
					<div class="ticket-type-grid">
							<div class="form-group">
									<label>Ticket Type</label>
									<input type="text" name="ticket_types-${ticketCount}-ticket_type" 
												 class="form-control" required>
							</div>
							<div class="form-group">
									<label>Quantity</label>
									<input type="number" name="ticket_types-${ticketCount}-quantity" 
												 class="form-control" required>
							</div>
							<div class="form-group">
									<label>Quantity</label>
									<input type="number" name="ticket_types-${ticketCount}-quantity" 
												 class="form-control" min="1" required>
							</div>
							<div class="form-group">
									<label>Price</label>
									<input type="number" name="ticket_types-${ticketCount}-price" 
												 class="form-control" min="0" step="0.01" required>
							</div>
							<div class="form-group full-width">
									<label>Description</label>
									<textarea name="ticket_types-${ticketCount}-description" 
														class="form-control" rows="3"></textarea>
							</div>
					</div>
			`;
    ticketTypes.appendChild(newTicket);
  }

  function addImagePreview(src, filename, file = null) {
    const previewDiv = document.createElement('div');
    previewDiv.className = 'image-preview';
    previewDiv.innerHTML = `
      <img src="${src}" alt="${filename}">
      <button type="button" class="remove-image remove-new-image">
          <span class="material-icons">close</span>
      </button>
    `;

    if (file) {
      // Store the actual file object
			previewDiv.dataset.file = 'true';
			const fileInput = document.createElement('input');
			fileInput.type = 'file';
			fileInput.style.display = 'none';
			fileInput.name = 'images';
			
			// Create a new FileList containing just this file
			const dataTransfer = new DataTransfer();
			dataTransfer.items.add(file);
			fileInput.files = dataTransfer.files;
			
			previewDiv.appendChild(fileInput);
    } else {
			// For URL images
			const urlInput = document.createElement('input');
			urlInput.type = 'hidden';
			urlInput.name = 'image_urls[]';
			urlInput.value = src;
			previewDiv.appendChild(urlInput);
		}

    previewDiv.querySelector('.remove-image').addEventListener('click', function() {
			previewDiv.remove();
			imageCount--;
		});

    imageContainer.appendChild(previewDiv);
		imageCount++;
  }

  function checkImageLimit() {
    const currentImages = document.querySelectorAll(".image-preview").length;
    const imagesInput = document.getElementById("images");

    if (currentImages >= 5) {
      imagesInput.disabled = true;
      imagesInput.style.opacity = '0.5';
    } else {
      imagesInput.disabled = false;
      imagesInput.style.opacity = '1';
    }
  }

  document.querySelectorAll('.event-type-option').forEach(option => {
    option.addEventListener('click', function () {
      selectEventType(this);
    });
  });

  const addTicketTypeBtn = document.getElementById('addTicketTypeBtn');
  addTicketTypeBtn.addEventListener('click', function () {
    addTicketType();
  });


  if (eventType) {
    const option = eventType.closest('.event-type-option');
    if (option) {
      selectEventType(option);
    }
  }

  // Handle file input change
  addImageBtn.addEventListener('click', () => imageInput.click());

  imageInput.addEventListener("change", function (e) {
    const files = Array.from(e.target.files);
    console.log('Files selected:', files.length);
    imageCount = document.querySelectorAll(".image-preview").length;
    
    if (imageCount + files.length > maxImages) {
			alert(`You can only upload up to ${maxImages} images.`);
			return;
		}

		files.forEach(file => {
			if (!file.type.match('image/(jpeg|png)')) {
				alert(`File "${file.name}" is not a valid image. Only JPEG and PNG files are allowed.`);
				return;
			}

			const reader = new FileReader();
			reader.onload = function(e) {
				addImagePreview(e.target.result, file.name, file);
			};
			reader.readAsDataURL(file);
		});

		// Clear the input
		e.target.value = '';    
  });

  // Handle image removal (both existing and new images)
  imageContainer.addEventListener('click', function (e) {
    const removeButton = e.target.closest('.remove-image');
    if (!removeButton) return;

    if (removeButton.classList.contains('remove-existing-image')) {
      // Handle existing image removal
      const imageId = removeButton.dataset.imageId;
      removedImages.add(imageId);
      document.getElementById(`image-${imageId}`).remove();
      document.getElementById("removedImages").value = Array.from(removedImages).join(",");
    } else if (removeButton.classList.contains('remove-new-image')) {
      // Handle new image removal
      const index = parseInt(removeButton.dataset.index);
      const input = document.getElementById("images");
      const dt = new DataTransfer();

      Array.from(input.files).forEach((file, i) => {
        if (i !== index) dt.items.add(file);
      });

      input.files = dt.files;
      removeButton.closest('.image-preview').remove();
    }

    checkImageLimit();
  });

  // Initial check for image limit
  checkImageLimit();

  eventForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    console.log('Starting form submission...');

    try {
      const formData = new FormData(this);
      const currentPath = window.location.pathname;
      const eventId = currentPath.split('/')[2];

      // Add removed images to formData
      if (removedImages.size > 0) {
        formData.set('removed_images', Array.from(removedImages).join(','));
      }

      // Only process new images if they were added
      const fileInput = document.getElementById('images');
      if (fileInput.files.length > 0) {
        // Clear existing image entries
        formData.delete('images');
        // Add new images
        Array.from(fileInput.files).forEach(file => {
          formData.append('images', file);
        });
      }

      console.log('Sending form data to server...');
      const response = await fetch(`/event/${eventId}/edit`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        }
      });

      const result = await response.json();
      console.log('Server response:', result);

      if (result.success) {
        window.location.href = result.redirect;
      } else {
        alert(result.message || 'Error updating event');
      }
    } catch (error) {
      console.error('Form submission error:', error);
      alert('Error updating event. Please try again.');
    }
  });
});

