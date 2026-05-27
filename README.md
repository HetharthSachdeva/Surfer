# Surfer Playwright Agent

A modular, stateful web automation agent that runs tasks defined in a simple `tasks.txt` file using Playwright. Perfect as a lightweight foundation for LLM-powered browser operation.

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   python -m playwright install
   ```

---

## File Structure

- **`web_agent.py`**: The core `WebAgent` class. Handles launching/stopping the browser, managing page sessions, and standard automation tasks.
- **`agent.py`**: The runner script. Reads instructions from `tasks.txt` and calls the agent to perform actions.
- **`tasks.txt`**: Your simple, line-by-line configuration file.

---

## How to Use

Configure your target URL, task, and parameters in **`tasks.txt`** line-by-line.

### `tasks.txt` Format

- **Line 1**: Target URL (e.g., `https://www.linkedin.com`)
- **Line 2**: Task to run (see supported tasks below)
- **Line 3 (Optional)**: Input / Parameter for the task
- **Line 4 (Optional)**: Headless mode (`True` or `False`. Default is `False` for headed mode)
- **Line 5 (Optional)**: Timeout in milliseconds (Default is `60000`)

### Example: Taking a screenshot of LinkedIn
Write the following into your `tasks.txt` file:
```text
https://www.linkedin.com
screenshot
screenshot.png
```

### Running the Agent
Once `tasks.txt` is saved, simply run:
```bash
python agent.py
```

---

## Tasks Supported

- `get-title`: Prints the active page title.
- `screenshot`: Saves a full-page screenshot (parameter = filename).
- `get-text`: Prints inner text of a selector (parameter = selector).
- `click`: Clicks a selector (parameter = selector).
- `fill`: Fills an input (parameter = `selector|||value`).
- `evaluate`: Runs a JavaScript expression and prints the result (parameter = JS expression).

---

## Technical Features

- **Stateful `WebAgent` Class**: Implements context manager support (`__enter__` and `__exit__`), ensuring the Playwright browser is closed gracefully.
- **Headed Mode by Default**: Allows you to watch the browser actions live on your screen as the agent runs.
- **Safe Ignored Files**: Pre-configured `.gitignore` to keep compiled caches, environments, and screenshot files out of Git.
