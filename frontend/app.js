let pollingInterval = null;

document.getElementById('goal-form').addEventListener('submit', async (e) => {
	e.preventDefault();

	const goalInput = document.getElementById('goal-input');
	const submitBtn = document.getElementById('submit-btn');
	const loader = document.getElementById('loader');
	const resultsCard = document.getElementById('results-card');

	const goal = goalInput.value.trim();

	// Clear any existing polling loop
	if (pollingInterval) {
		clearInterval(pollingInterval);
	}

	// 1. Enter Loading State
	submitBtn.disabled = true;
	loader.classList.remove('hidden');
	resultsCard.classList.add('hidden');

	try {
		// 2. Submit Goal to queue (fast POST response)
		const response = await fetch('http://localhost:8000/run', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ goal })
		});

		if (!response.ok) {
			const errData = await response.json();
			throw new Error(errData.detail || 'Failed to submit goal.');
		}

		const data = await response.json();
		const taskId = data.task_id;
		
		console.log(`Task queued successfully. Task ID: ${taskId}`);

		// 3. Start Polling Loop to check background worker status
		pollTaskStatus(taskId, submitBtn, loader);

	} catch (error) {
		alert(`Error starting agent: ${error.message}`);
		submitBtn.disabled = false;
		loader.classList.add('hidden');
	}
});

function pollTaskStatus(taskId, submitBtn, loader) {
	const statusMessage = loader.querySelector('p');

	pollingInterval = setInterval(async () => {
		try {
			const response = await fetch(`http://localhost:8000/status/${taskId}`);
			if (!response.ok) {
				throw new Error('Failed to fetch task status.');
			}

			const data = await response.json();

			if (data.status === 'pending') {
				statusMessage.textContent = 'Task queued... waiting for a free Celery worker.';
			} else if (data.status === 'processing') {
				statusMessage.textContent = 'Agent is running the Playwright browser in the background...';
			} else if (data.status === 'success') {
				// Task finished successfully!
				clearInterval(pollingInterval);
				renderResults(data.result);
				submitBtn.disabled = false;
				loader.classList.add('hidden');
			} else if (data.status === 'failed') {
				// Task crashed in the worker
				clearInterval(pollingInterval);
				alert(`Agent task failed in background: ${data.error}`);
				submitBtn.disabled = false;
				loader.classList.add('hidden');
			}
		} catch (err) {
			console.error('Polling error:', err);
		}
	}, 1500); // Poll every 1.5 seconds
}

function renderResults(result) {
	const resultsCard = document.getElementById('results-card');
	const statusBadge = document.getElementById('status-badge');
	const stepsList = document.getElementById('steps-list');
	const screenshotImg = document.getElementById('screenshot-img');

	// Clear previous steps
	stepsList.innerHTML = '';

	// Render Success Status
	if (result.success) {
		statusBadge.textContent = 'Success';
		statusBadge.className = 'status-badge success';
	} else {
		statusBadge.textContent = 'Failed';
		statusBadge.className = 'status-badge failed';
	}

	// Render Action History
	result.history.forEach((step, idx) => {
		const li = document.createElement('li');
		
		let text = `${idx + 1}. Action: ${step.action} ${step.argument || ''}`;
		if (step.status === 'failed') {
			li.classList.add('failed-step');
		}

		const details = document.createElement('span');
		details.className = 'step-details';
		details.textContent = `Result: ${step.result}`;

		li.appendChild(document.createTextNode(text));
		li.appendChild(details);
		stepsList.appendChild(li);
	});

	// Render Screenshot
	if (result.screenshot) {
		screenshotImg.src = `data:image/png;base64,${result.screenshot}`;
		screenshotImg.style.display = 'block';
	} else {
		screenshotImg.style.display = 'none';
	}

	// Reveal Card
	resultsCard.classList.remove('hidden');
}
