document.addEventListener('DOMContentLoaded', function () {
	console.log('Initializing event creation form...');

	if (window.eventFlowInitialized) {
		console.log('Event flow already initialized, skipping...');
		return;
	}
	window.eventFlowInitialized = true;

	// Get form elements
	const eventForm = document.getElementById('eventForm');
	const eventTypeRadios = document.querySelectorAll('input[name="event_type"]');
	const addTicketTypeBtn = document.getElementById('addTicketType');
	const ticketTypesList = document.getElementById('ticketTypesList');
	const addImageBtn = document.querySelector('.btn-add-image');
	const imageInput = document.querySelector('.form-control-file');
	const imagePreviewsContainer = document.querySelector('.image-previews');
	const uploadMessage = document.querySelector('.upload-message');
	const addUrlBtn = document.querySelector('.btn-add-url');
	const urlInput = document.getElementById('image_url');
	const maxImages = 5;
	let ticketTypeCounter = 0;
	let imageCount = 0;

	function getDefaultDescription(ticketType) {
		const descriptions = {
			'early-bird': 'Early bird special rate for early registrations.',
			'regular': 'Standard admission ticket.',
			'vip': 'VIP access with premium benefits.',
			'vvip': 'VVIP access with exclusive perks and premium benefits.',
			'student': 'Special rate for students with valid ID.',
			'group': 'Discounted rate for group bookings.',
			'custom': ''
		};
		return descriptions[ticketType] || '';
	}

	function updateTicketDescription(ticketTypeSelect) {
		const descriptionField = ticketTypeSelect.closest('.ticket-type-row').querySelector('[name$="description"]');
		if (descriptionField && !descriptionField.value) {
			descriptionField.value = getDefaultDescription(ticketTypeSelect.value);
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
						<select name="ticket_types-${ticketTypeCounter}-ticket_type" 
								class="form-control ticket-type-select" 
								required>
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
								  class="form-control" 
								  rows="3"></textarea>
					</div>
				</div>
			</div>
		`;

		const tempDiv = document.createElement('div');
		tempDiv.innerHTML = ticketHtml;
		const newTicket = tempDiv.firstElementChild;

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

		ticketTypesList.appendChild(newTicket);
		ticketTypeCounter++;
	}

	function disableTicketValidation() {
		console.log('Disabling ticket validation');
		const ticketFields = document.querySelectorAll('[name^="ticket_types-"]');
		ticketFields.forEach(field => {
			field.disabled = true;
			field.removeAttribute('required');
			// Clear values
			if (field.tagName === 'SELECT') {
				field.value = '';
			} else if (field.type === 'number') {
				field.value = '0';
			} else {
				field.value = '';
			}
		});

		const ticketSettings = document.getElementById('ticketSettings');
		if (ticketSettings) {
			ticketSettings.style.display = 'none';
		}
	}

	function enableTicketValidation() {
		console.log('Enabling ticket validation');
		const ticketFields = document.querySelectorAll('[name^="ticket_types-"]');
		const currencyField = document.querySelector('select[name="currency"]');

		if (currencyField) {
			currencyField.disabled = false;
			currencyField.required = true;
		}

		ticketFields.forEach(field => {
			field.disabled = false;
			if (field.classList.contains('required')) {
				field.setAttribute('required', '');
			}
		});

		const ticketSettings = document.getElementById('ticketSettings');
		if (ticketSettings) {
			ticketSettings.style.display = 'block';
		}
	}

	// Event type change handler
	eventTypeRadios.forEach(radio => {
		radio.addEventListener('change', function () {
			console.log('Event type changed:', this.value);
			const ticketSettings = document.getElementById('ticketSettings');
			const currencySelect = document.querySelector('select[name="currency"]');

			if (this.value === 'paid') {
				enableTicketValidation();
				ticketSettings.style.display = 'block';
				currencySelect.disabled = false;
				currencySelect.required = true;
				if (!document.querySelector('.ticket-type-item')) {
					addTicketType();
				}
			} else {
				disableTicketValidation();
				ticketSettings.style.display = 'none';
				currencySelect.disabled = true;
				currencySelect.required = false;
				currencySelect.value = '';
				ticketTypeCounter = 0;
				const ticketsList = document.getElementById('ticketTypesList');
				if (ticketsList) {
					ticketsList.innerHTML = '';
				}
			}
		});
	});

	// Add ticket type button handler
	if (addTicketTypeBtn) {
		addTicketTypeBtn.addEventListener('click', function () {
			console.log('Adding new ticket type');
			addTicketType();
		});
	}

	// Handle file input change
	addImageBtn.addEventListener('click', () => imageInput.click());

	imageInput.addEventListener('change', function(e) {
		const files = Array.from(e.target.files);
		console.log('Files selected:', files.length);
		
		if (imageCount + files.length > maxImages) {
			alert(`You can only upload up to ${maxImages} images. Please select fewer images.`);
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

	// Handle URL image addition
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
			updateUploadMessage();
		} catch (error) {
			showUrlError('Invalid image URL. Please check the URL and try again.');
		}
	});

	function addImagePreview(src, filename, file = null) {
		const wrapper = document.createElement('div');
		wrapper.className = 'image-preview-wrapper';
		
		wrapper.innerHTML = `
			<img src="${src}" alt="${filename}">
			<button type="button" class="remove-image" title="Remove image">
				<span class="material-icons">close</span>
			</button>
		`;

		if (file) {
			// Store the actual file object
			wrapper.dataset.file = 'true';
			const fileInput = document.createElement('input');
			fileInput.type = 'file';
			fileInput.style.display = 'none';
			fileInput.name = 'images';
			
			// Create a new FileList containing just this file
			const dataTransfer = new DataTransfer();
			dataTransfer.items.add(file);
			fileInput.files = dataTransfer.files;
			
			wrapper.appendChild(fileInput);
		} else {
			// For URL images
			const urlInput = document.createElement('input');
			urlInput.type = 'hidden';
			urlInput.name = 'image_urls[]';
			urlInput.value = src;
			wrapper.appendChild(urlInput);
		}

		wrapper.querySelector('.remove-image').addEventListener('click', function() {
			wrapper.remove();
			imageCount--;
			updateUploadMessage();
		});

		imagePreviewsContainer.appendChild(wrapper);
		imageCount++;
		updateUploadMessage();
	}

	function updateUploadMessage() {
		if (imageCount === 0) {
			uploadMessage.style.display = 'block';
			uploadMessage.textContent = 'No images selected yet';
		} else {
			uploadMessage.style.display = 'none';
		}
		
		addImageBtn.disabled = imageCount >= maxImages;
	}

	function showUrlError(message) {
		const errorDiv = document.createElement('div');
		errorDiv.className = 'error-message';
		errorDiv.textContent = message;
		
		const existingError = urlInput.parentElement.querySelector('.error-message');
		if (existingError) existingError.remove();
		
		urlInput.parentElement.appendChild(errorDiv);
		setTimeout(() => errorDiv.remove(), 3000);
	}

	// Form submission handler
	eventForm.addEventListener('submit', async function (e) {
		e.preventDefault();
		console.log('Starting form submission...');

		try {
			const formData = new FormData(this);
			
			// Remove any existing image fields
			for (let pair of formData.entries()) {
				if (pair[0] === 'images') {
					formData.delete('images');
				}
			}

			// Get all image files from preview containers
			const imageContainers = imagePreviewsContainer.querySelectorAll('.image-preview-wrapper');
			console.log('Found image containers:', imageContainers.length);

			if (imageContainers.length === 0) {
				alert('Please add at least one image');
				return;
			}

			// Add each image file to formData
			let imageAdded = false;
			imageContainers.forEach((container, index) => {
				const fileInput = container.querySelector('input[type="file"]');
				if (fileInput && fileInput.files && fileInput.files[0]) {
					formData.append('images', fileInput.files[0]);
					imageAdded = true;
					console.log(`Added image file ${index + 1}:`, fileInput.files[0].name);
				}
			});

			if (!imageAdded) {
				alert('Please add at least one valid image');
				return;
			}

			console.log('Sending form data to server...');
			const response = await fetch('/event/create', {
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
				alert(result.message || 'Error creating event');
			}
		} catch (error) {
			console.error('Form submission error:', error);
			alert('Error creating event. Please try again.');
		}
	});

	// Update the ticket type change handler
	document.addEventListener('change', function (e) {
		if (e.target.name && e.target.name.endsWith('[ticket_type]')) {
			updateTicketDescription(e.target);
		}
	});

	// Event type selection handler
	document.querySelectorAll('.event-type-option').forEach(option => {
		const radio = option.querySelector('input[type="radio"]');

		option.addEventListener('click', () => {
			document.querySelectorAll('.event-type-option').forEach(opt => {
				opt.classList.remove('selected');
			});
			option.classList.add('selected');
			radio.checked = true;
			radio.dispatchEvent(new Event('change'));
		});
	});

	// Initialize the event type selection on page load
	window.addEventListener('DOMContentLoaded', () => {
		const defaultEventType = document.querySelector('input[name="event_type"][value="free"]');
		if (defaultEventType) {
			const option = defaultEventType.closest('.event-type-option');
			option.classList.add('selected');
			defaultEventType.checked = true;
			defaultEventType.dispatchEvent(new Event('change'));
		}
	});
});