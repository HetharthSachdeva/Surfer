# Surfer Playwright Agent

A modular, stateful web automation agent that runs a sequential flow of tasks defined in a `tasks.txt` file in a single browser window session. Perfect as a lightweight foundation for LLM-powered browser operation.

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
- **`agent.py`**: The runner script. Reads instructions from `tasks.txt` and executes them in a persistent loop.
- **`tasks.txt`**: Your multi-step configuration script.

---

## How to Use

Configure your flow in **`tasks.txt`**. 

### Settings Configuration (Header Comments)
You can configure global settings by adding `# key: value` lines at the top of the file:
* `# headless: True` (Run in background) or `# headless: False` (Watch browser live, **default**)
* `# timeout: 30000` (Timeout in milliseconds, **default 60000**)

### Instruction Format
Each non-comment line is executed sequentially as a step in the format:
```text
<action> [parameter]
```

### Example Flow Script:
Create the following flow in your `tasks.txt` to visit a site, read its title, click a link, and capture a screenshot:
```text
# headless: False
# timeout: 45000

goto https://example.com
get-title
click a
screenshot example_success.png
```

### Running the Agent
Once `tasks.txt` is saved, simply execute:
```bash
python agent.py
```

---

## Tasks Supported

- `goto <url>`: Navigates to the specified URL.
- `get-title`: Prints the active page title.
- `screenshot [filename]`: Saves a full-page screenshot (default is `screenshot.png`).
- `get-text <selector>`: Prints the inner text of the selector.
- `click <selector>`: Clicks the element matching the selector.
- `fill <selector>|||<value>`: Fills an input element with the value.
- `evaluate <js_expression>`: Runs a JS expression and prints the returned result.

---

## Technical Features

- **Sequential Persistence**: All instructions run on the same browser instance, maintaining browser history, loaded states, and sessions.
- **Auto-abort on Error**: If any step in the sequence fails, the agent prints the failure and aborts to prevent cascading errors.
- **Headed Mode by Default**: Allows you to watch the browser actions live on your screen as the agent runs.
- **Safe Ignored Files**: Pre-configured `.gitignore` to keep compiled caches, environments, and screenshot files out of Git.
