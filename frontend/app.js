let currentTaskId = null;

document.getElementById('goal-form').addEventListener('submit', async (e) => {
	e.preventDefault();

	const goalInput = document.getElementById('goal-input');
	const submitBtn = document.getElementById('submit-btn');
	const loader = document.getElementById('loader');
	const resultsCard = document.getElementById('results-card');

	const goal = goalInput.value.trim();

	// 1. Initialize Loading UI State
	submitBtn.disabled = true;
	loader.classList.remove('hidden');
	
	// Reset list, screenshots, and logs in preparation for stream
	document.getElementById('steps-list').innerHTML = '';
	document.getElementById('screenshot-img').style.display = 'none';
	
	const placeholder = document.getElementById('screenshot-placeholder');
	placeholder.style.display = 'flex';
	placeholder.querySelector('span').textContent = 'Contacting queue...';

	document.getElementById('screenshot-title').textContent = 'Live Browser View';

	const consoleElement = document.getElementById('live-console');
	consoleElement.innerHTML = '<div class="console-line system-line">[System] Contacting backend agent queue...</div>';
	
	// Reveal card immediately so user can see step-by-step actions stream in real-time
	resultsCard.classList.remove('hidden');

	try {
		// 2. Submit Goal to FastAPI (instant 202 queue acceptance)
		const response = await fetch('http://localhost:8000/run', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ goal })
		});

		if (!response.ok) {
			const errData = await response.json();
			throw new Error(errData.detail || 'Failed to queue task.');
		}

		const data = await response.json();
		const taskId = data.task_id;
		currentTaskId = taskId; // Track active task ID globally
		
		console.log(`Task successfully queued. ID: ${taskId}`);
		appendConsoleLine(`[System] Task successfully queued in Redis. Task ID: ${taskId}`, 'system-line');

		// 3. Connect to the WebSocket stream channel
		connectWebSocket(taskId, submitBtn, loader);

	} catch (error) {
		appendConsoleLine(`[System Error] Failed to initialize goal: ${error.message}`, 'error-line');
		submitBtn.disabled = false;
		loader.classList.add('hidden');
	}
});

function connectWebSocket(taskId, submitBtn, loader) {
	const statusBadge = document.getElementById('status-badge');
	const screenshotImg = document.getElementById('screenshot-img');
	const screenshotTitle = document.getElementById('screenshot-title');
	const statusMessage = loader.querySelector('p');

	// Set dynamic badge styling for "Running" state
	statusBadge.textContent = 'Running';
	statusBadge.className = 'status-badge';
	statusBadge.style.backgroundColor = 'rgba(99, 102, 241, 0.2)';
	statusBadge.style.color = '#6366f1';
	statusBadge.style.borderColor = '#6366f1';

	const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);

	ws.onopen = () => {
		appendConsoleLine('[System] WebSocket link opened. Subscribed to Redis task stream.', 'system-line');
	};

	ws.onmessage = (event) => {
		const payload = JSON.parse(event.data);

		// Update backend loader text
		if (payload.status === 'processing') {
			statusMessage.textContent = 'Agent is executing browser steps. Watch the live view below.';
		}

		// Stream logs to console with custom line highlight colors
		if (payload.log) {
			let lineClass = 'action-line';
			if (payload.status === 'failed') {
				lineClass = 'error-line';
			} else if (payload.log.startsWith('[System')) {
				lineClass = 'system-line';
			}
			appendConsoleLine(payload.log, lineClass);
		}

		// Render completed steps sequence
		if (payload.history) {
			renderSteps(payload.history);
		}

		// Render screenshot frame live as it updates
		if (payload.screenshot) {
			screenshotImg.src = `data:image/png;base64,${payload.screenshot}`;
			screenshotImg.style.display = 'block';
			document.getElementById('screenshot-placeholder').style.display = 'none';
		}

		// Check if execution has completed or crashed
		if (payload.status === 'success' || payload.status === 'failed') {
			ws.close();
			submitBtn.disabled = false;
			loader.classList.add('hidden');

			if (payload.status === 'success') {
				statusBadge.textContent = 'Success';
				statusBadge.className = 'status-badge success';
				statusBadge.style = ''; // Reset standard styles
				screenshotTitle.textContent = 'Final State Screenshot';
				appendConsoleLine('[System] Goal executed successfully. Terminated channel.', 'system-line');
			} else {
				statusBadge.textContent = 'Failed';
				statusBadge.className = 'status-badge failed';
				statusBadge.style = ''; // Reset standard styles
				screenshotTitle.textContent = 'Failure State Screenshot';
				appendConsoleLine('[System] Task aborted due to errors.', 'error-line');
			}
		}
	};

	ws.onerror = (err) => {
		console.error('WebSocket error:', err);
		appendConsoleLine('[System Error] WebSocket channel closed unexpectedly.', 'error-line');
	};

	ws.onclose = () => {
		submitBtn.disabled = false;
		loader.classList.add('hidden');
	};
}

function appendConsoleLine(text, className) {
	const consoleElement = document.getElementById('live-console');
	const line = document.createElement('div');
	line.className = `console-line ${className}`;

	// Add localized clock timestamp
	const now = new Date();
	const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
	
	line.textContent = `[${timeStr}] ${text}`;
	consoleElement.appendChild(line);

	// Auto-scroll to lowest line
	consoleElement.scrollTop = consoleElement.scrollHeight;
}

function renderSteps(history) {
	const stepsList = document.getElementById('steps-list');
	stepsList.innerHTML = '';

	history.forEach((step, idx) => {
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
}

// Click listener to set cancellation flag in Redis
document.getElementById('stop-btn').addEventListener('click', async () => {
	if (!currentTaskId) return;

	appendConsoleLine('[System] Sending cancellation request to backend...', 'system-line');
	try {
		const response = await fetch(`http://localhost:8000/stop/${currentTaskId}`, {
			method: 'POST'
		});
		if (response.ok) {
			appendConsoleLine('[System] Cancel flag registered. Worker will abort on next step.', 'system-line');
		} else {
			appendConsoleLine('[System Error] Failed to register cancellation flag.', 'error-line');
		}
	} catch (err) {
		appendConsoleLine(`[System Error] Network error during cancel dispatch: ${err.message}`, 'error-line');
	}
});
