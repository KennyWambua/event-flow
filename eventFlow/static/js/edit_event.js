document.addEventListener('DOMContentLoaded', function () {
  const eventType = document.querySelector('input[name="event_type"]:checked');
  const eventForm = document.getElementById('eventForm');
  const imageContainer = document.getElementById('imageContainer');
  const addImageBtn = document.querySelector('.btn-add-image')
  const addTicketTypeBtn = document.getElementById('addTicketTypeBtn');
  const addUrlBtn = document.querySelector('.btn-add-url');
  const urlInput = document.getElementById('image_url');
  const imageInput = document.querySelector('.image-input-file')
  const ticketTypes = document.getElementById('ticketTypes');
  const maxImages = 5
  let removedImages = new Set();
  let ticketTypeCounter = 0;
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
      if (!document.querySelector('.ticket-type-item')) {
        addTicketType();
      }
    } else {
      ticketSection.style.display = 'none';
    }
  }

  function addTicketType() {

    const ticketHtml = `
      <div class="ticket-type-item">
        <div class="ticket-type-header">
          <h4 class="ticket-type-label">Ticket Type ${ticketTypeCounter + 1}</h4>
          ${ticketTypeCounter > 0 ?
          '<button type="button" class="remove-ticket"><span class="material-icons">delete</span> Remove</button>' : ''}
        </div>
        <div class="ticket-type-grid">
          <div class="form-group">
            <label>Ticket Type *</label>
            <select name="ticket_types-${ticketTypeCounter}-ticket_type" class="form-control ticket-type-select" required>
              <option value="">Select Ticket Type</option>
              <option value="early-bird">Early Bird</option>
              <option value="regular">Regular</option>
              <option value="vip">VIP</option>
              <option value="vvip">VVIP</option>
              <option value="student">Student</option>
              <option value="group">Group</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <div class="form-group custom-type-field" style="display: none;">
            <label>Custom Type Name *</label>
            <input type="text" 
              name="ticket_types-${ticketTypeCounter}-custom_type" 
              class="form-control" 
              placeholder="Enter custom ticket type name">
          </div>

          <div class="form-group">
            <label>Quantity *</label>
            <input type="number" 
              name="ticket_types-${ticketTypeCounter}-quantity" 
              class="form-control" 
              min="1" 
              value="100" 
              required>
          </div>

          <div class="form-group">
            <label>Price *</label>
            <input type="number" 
              name="ticket_types-${ticketTypeCounter}-price" 
              class="form-control" 
              min="0" 
              step="0.01" 
              value="0.00" 
              required>
          </div>

          <div class="form-group full-width">
            <label>Description</label>
            <textarea name="ticket_types-${ticketTypeCounter}-description" 
              class="form-control" rows="3">
            </textarea>
          </div>
        </div>
      </div>
    `;

    const ticketDiv = document.createElement('div');
    ticketDiv.innerHTML = ticketHtml
    const newTicket = ticketDiv.firstElementChild 

    // Add ticket type change handler
		const ticketTypeSelect = newTicket.querySelector('.ticket-type-select');
		const customTypeField = newTicket.querySelector('.custom-type-field');

		ticketTypeSelect.addEventListener('change', function () {
			if (this.value === 'custom') {
				customTypeField.style.display = 'block';
				customTypeField.querySelector('input').required = true;
			} else {
				customTypeField.style.display = 'none';
				customTypeField.querySelector('input').required = false;
			}
		});

    	// Add remove button handler
		const removeBtn = newTicket.querySelector('.remove-ticket');
		if (removeBtn) {
			removeBtn.addEventListener('click', function () {
				newTicket.remove();
				ticketTypeCounter--;
				// Renumber remaining tickets
				const ticketTypeItem = document.querySelectorAll('.ticket-type-item');
				ticketTypeItem.forEach((container, index) => {
					const ticketLabel = container.querySelector('.ticket-type-label');
					if (ticketLabel) {
						ticketLabel.textContent = `Ticket Type ${index + 1}`;
					}
				});
			});
		}

    ticketTypes.appendChild(newTicket);
    ticketTypeCounter++;
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

  document.querySelectorAll('.event-type-option').forEach(option => {
    option.addEventListener('click', function () {
      selectEventType(this);
    });
  });

  if (addTicketTypeBtn) {
    addTicketTypeBtn.addEventListener('click', function () {
      addTicketType();
    });
  }

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

  addUrlBtn.addEventListener('click', async () => {
		const url = urlInput.value.trim();
		if (!url) {
			showUrlError('Please enter an image URL');
			return;
		}

		if (imageCount >= maxImages) {
			showUrlError(`Maximum ${maxImages} images allowed`);
			return;
		}

		try {
			const response = await fetch(url);
			if (!response.ok) throw new Error('Invalid URL');
			
			const contentType = response.headers.get('content-type');
			if (!contentType || !contentType.includes('image')) {
				throw new Error('URL does not point to a valid image');
			}

			// Convert URL image to blob
			const blob = await response.blob();
			const file = new File([blob], 'url-image-' + Date.now() + '.jpg', { type: 'image/jpeg' });
			
			// Create object URL for preview
			const objectUrl = URL.createObjectURL(file);
			addImagePreview(objectUrl, file.name, file);
			
			urlInput.value = '';
		} catch (error) {
			showUrlError('Invalid image URL. Please check the URL and try again.');
		}
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

