document.addEventListener('DOMContentLoaded', function () {
	console.log('Initializing event creation form...');

	if (window.eventFlowInitialized) {
		console.log('Event flow already initialized, skipping...');
		return;
	}
	window.eventFlowInitialized = true;

	// Get form elements
	const eventForm = document.getElementById('eventForm');
	const imageInput = document.querySelector('.form-control-file');
	const addImageBtn = document.querySelector('.btn-add-image');
	const ticketSettings = document.getElementById('ticketSettings');
	const eventTypeRadios = document.querySelectorAll('input[name="event_type"]');
	const addTicketTypeBtn = document.getElementById('addTicketType');
	const ticketTypesList = document.getElementById('ticketTypesList');
	const currencySelect = document.querySelector('select[name="currency"]');

	let ticketTypeCounter = 0;

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

	function updateCurrencySymbols() {
		const currencySymbols = document.querySelectorAll('.currency-symbol');
		const selectedCurrency = currencySelect?.value || 'KES';
		currencySymbols.forEach(symbol => {
			symbol.textContent = selectedCurrency;
		});
	}

	function addTicketType() {
		const ticketHtml = `
			<div class="ticket-type-item">
				<div class="ticket-type-header">
					<h4>Ticket Type ${ticketTypeCounter + 1}</h4>
					${ticketTypeCounter > 0 ? '<button type="button" class="remove-ticket">Remove</button>' : ''}
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
						<div class="price-input-wrapper">
							<span class="currency-symbol">${currencySelect?.value || 'KES'}</span>
							<input type="number" 
								   name="ticket_types-${ticketTypeCounter}-price" 
								   class="form-control" 
								   min="0" 
								   step="0.01" 
								   value="0.00" 
								   required>
						</div>
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
		radio.addEventListener('change', function() {
			console.log('Event type changed:', this.value);
			const ticketSettings = document.getElementById('ticketSettings');
			const currencySelect = document.querySelector('select[name="currency"]');
			
			if (this.value === 'paid') {
				enableTicketValidation();
				ticketSettings.style.display = 'block';
				currencySelect.disabled = false;
				currencySelect.required = true;
				// Add first ticket type if none exists
				if (!document.querySelector('.ticket-type-item')) {
					addTicketType();
				}
			} else {
				disableTicketValidation();
				ticketSettings.style.display = 'none';
				currencySelect.disabled = true;
				currencySelect.required = false;
				currencySelect.value = ''; // Clear currency selection
				// Clear ticket types
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

	// Remove ticket type handler
	ticketTypesList?.addEventListener('click', function (e) {
		if (e.target.classList.contains('remove-ticket')) {
			const ticketType = e.target.closest('.ticket-type');
			if (ticketTypesList.children.length > 1) {
				ticketType.remove();

				// Disable remove button if only one ticket type left
				if (ticketTypesList.children.length === 1) {
					const removeButton = ticketTypesList.querySelector('.remove-ticket');
					if (removeButton) removeButton.disabled = true;
				}
			}
		}
	});

	// Track selected files
	let currentFiles = new DataTransfer();
	const imagePreviews = document.querySelector('.image-previews');
	const uploadMessage = document.querySelector('.upload-message');

	// Update file input handler
	imageInput.addEventListener('change', function (e) {
		console.log('Files selected:', this.files);

		// Clear existing files
		currentFiles = new DataTransfer();

		// Add new files to currentFiles
		Array.from(this.files).forEach(file => {
			// Check file type
			if (!file.type.match('image/jpeg') && !file.type.match('image/png')) {
				alert('Only JPEG and PNG images are allowed');
				return;
			}

			// Check file size (5MB)
			if (file.size > 5 * 1024 * 1024) {
				alert('File size must be less than 5MB');
				return;
			}

			currentFiles.items.add(file);
			console.log('Added file to currentFiles:', file.name);
		});

		updatePreviews();
	});

	// Add image button click handler
	addImageBtn.addEventListener('click', function () {
		imageInput.click();
	});

	function updatePreviews() {
		console.log('Updating previews, files count:', currentFiles.files.length);
		// Clear existing previews
		imagePreviews.innerHTML = '';

		if (currentFiles.files.length === 0) {
			uploadMessage.textContent = 'No images selected yet';
			uploadMessage.style.display = 'block';
			imagePreviews.style.display = 'none';
		} else {
			uploadMessage.style.display = 'none';
			imagePreviews.style.display = 'grid';

			Array.from(currentFiles.files).forEach(file => {
				const preview = createImagePreview(file);
				imagePreviews.appendChild(preview);
			});
		}

		// Update the actual file input
		imageInput.files = currentFiles.files;
	}

	function createImagePreview(file) {
		console.log('Creating preview for:', file.name);
		const wrapper = document.createElement('div');
		wrapper.className = 'image-preview-wrapper';

		const img = document.createElement('img');
		img.src = URL.createObjectURL(file);
		img.onload = () => URL.revokeObjectURL(img.src);

		const removeBtn = document.createElement('button');
		removeBtn.type = 'button';
		removeBtn.className = 'remove-image';
		removeBtn.innerHTML = '<span class="material-icons">close</span>';
		removeBtn.onclick = () => removeImage(file);

		wrapper.appendChild(img);
		wrapper.appendChild(removeBtn);
		return wrapper;
	}

	function removeImage(file) {
		console.log('Removing image:', file.name);
		const dt = new DataTransfer();
		Array.from(currentFiles.files)
			.filter(f => f !== file)
			.forEach(f => dt.items.add(f));
		currentFiles = dt;
		updatePreviews();
	}

	// Form submission handler
	eventForm.addEventListener('submit', async function(e) {
		e.preventDefault();
		console.log('Submitting form...');

		const formData = new FormData(this);
		const eventType = formData.get('event_type');

		// Handle free vs paid event validation
		if (eventType === 'paid') {
			const currency = formData.get('currency');
			if (!currency) {
				alert('Please select a currency for paid events');
				return;
			}

			const ticketTypes = document.querySelectorAll('.ticket-type-item');
			if (ticketTypes.length === 0) {
				alert('Please add at least one ticket type for paid events');
				return;
			}
		} else {
			// Remove currency and ticket data for free events
			formData.delete('currency');
			for (let pair of formData.entries()) {
				if (pair[0].startsWith('ticket_types-')) {
					formData.delete(pair[0]);
				}
			}
		}

		// Add images
		if (currentFiles.files.length === 0) {
			alert('Please add at least one image');
			return;
		}

		// Add each image file explicitly
		Array.from(currentFiles.files).forEach((file, index) => {
			formData.append('images', file);
			console.log(`Adding image to FormData: ${file.name}, size: ${file.size} bytes`);
		});

		// Log all form data entries for debugging
		console.log('Final form data contents:');
		for (let [key, value] of formData.entries()) {
			console.log(`${key}:`, value instanceof File ? `File: ${value.name}` : value);
		}

		try {
			console.log('Sending form data to server...');
			const response = await fetch('/event/create', {
				method: 'POST',
				body: formData,
				headers: {
					'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
				},
				// Important: Don't set Content-Type header, let the browser set it with boundary
			});

			const result = await response.json();
			console.log('Server response:', result);

			if (result.success) {
				window.location.href = result.redirect;
			} else {
				alert(result.message || 'Error creating event');
			}
		} catch (error) {
			console.error('Error:', error);
			alert('Error creating event. Please try again.');
		}
	});

	// Update the ticket type change handler
	document.addEventListener('change', function (e) {
		if (e.target.name && e.target.name.endsWith('[ticket_type]')) {
			updateTicketDescription(e.target);
		}
	});

	// Add currency change handler
	if (currencySelect) {
		currencySelect.addEventListener('change', updateCurrencySymbols);
	}

	// Initialize currency symbols on page load
	updateCurrencySymbols();
});