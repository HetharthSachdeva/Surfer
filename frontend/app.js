document.getElementById('goal-form').addEventListener('submit', async (e) => {
	e.preventDefault();

	const goalInput = document.getElementById('goal-input');
	const submitBtn = document.getElementById('submit-btn');
	const loader = document.getElementById('loader');
	const resultsCard = document.getElementById('results-card');

	const goal = goalInput.value.trim();

	// 1. Enter Loading State
	submitBtn.disabled = true;
	loader.classList.remove('hidden');
	resultsCard.classList.add('hidden');

	try {
		// 2. Fetch Results from FastAPI
		const response = await fetch('http://localhost:8000/run', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ goal })
		});

		if (!response.ok) {
			const errData = await response.json();
			throw new Error(errData.detail || 'Failed to execute agent.');
		}

		const data = await response.json();

		// 3. Render Results
		renderResults(data);

	} catch (error) {
		alert(`Error running agent: ${error.message}`);
	} finally {
		// 4. Leave Loading State
		submitBtn.disabled = false;
		loader.classList.add('hidden');
	}
});

function renderResults(data) {
	const resultsCard = document.getElementById('results-card');
	const statusBadge = document.getElementById('status-badge');
	const stepsList = document.getElementById('steps-list');
	const screenshotImg = document.getElementById('screenshot-img');

	// Clear previous steps
	stepsList.innerHTML = '';

	// Render Status
	if (data.success) {
		statusBadge.textContent = 'Success';
		statusBadge.className = 'status-badge success';
	} else {
		statusBadge.textContent = 'Failed';
		statusBadge.className = 'status-badge failed';
	}

	// Render Action History
	data.history.forEach((step, idx) => {
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
	if (data.screenshot) {
		screenshotImg.src = `data:image/png;base64,${data.screenshot}`;
		screenshotImg.style.display = 'block';
	} else {
		screenshotImg.style.display = 'none';
	}

	// Reveal Card
	resultsCard.classList.remove('hidden');
}
