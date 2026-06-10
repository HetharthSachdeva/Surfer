import json
from playwright.sync_api import sync_playwright

class WebAgent:
	def __init__(self, headless: bool = False, slow_mo: int = 500, timeout: int = 60000):
		self.headless = headless
		self.slow_mo = slow_mo
		self.timeout = timeout
		self.playwright = None
		self.browser = None
		self.page = None

	def start(self):
		self.playwright = sync_playwright().start()
		self.browser = self.playwright.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
		self.page = self.browser.new_page()
		self.page.set_default_timeout(self.timeout)

	def stop(self):
		if self.browser:
			self.browser.close()
		if self.playwright:
			self.playwright.stop()

	def __enter__(self):
		self.start()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.stop()

	def navigate(self, url: str):
		self.page.goto(url)

	def get_title(self) -> str:
		return self.page.title()

	def screenshot(self, filename: str):
		self.page.screenshot(path=filename, full_page=True)

	def get_text(self, selector_or_text: str) -> str:
		if selector_or_text.isdigit():
			# If targeting a surfer ID, it should exist immediately (5s timeout)
			return self.page.locator(f'[data-surfer-id="{selector_or_text}"]').inner_text(timeout=5000)
		elements = self.page.get_by_text(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			return visible_elements[0].inner_text(timeout=5000)
		return self.page.locator(selector_or_text).inner_text(timeout=10000)

	def click(self, selector_or_text: str):
		# If it is a digit, target the stable surfer index directly with a 5s timeout
		if selector_or_text.isdigit():
			self.page.click(f'[data-surfer-id="{selector_or_text}"]', timeout=5000)
			return

		# 1. Try to click by visible text
		elements = self.page.get_by_text(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].click(timeout=5000)
			return

		# 2. Try to click by label
		elements = self.page.get_by_label(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].click(timeout=5000)
			return

		# 3. Fallback to standard selector click (10s timeout)
		self.page.click(selector_or_text, timeout=10000)

	def fill(self, selector_or_text: str, value: str):
		# If it is a digit, target the stable surfer index directly with a 5s timeout
		if selector_or_text.isdigit():
			self.page.fill(f'[data-surfer-id="{selector_or_text}"]', value, timeout=5000)
			return

		# 1. Try to fill by label (best practice for form inputs)
		elements = self.page.get_by_label(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].fill(value, timeout=5000)
			return

		# 2. Try to fill by placeholder
		elements = self.page.get_by_placeholder(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].fill(value, timeout=5000)
			return

		# 3. Try to fill by visible text
		elements = self.page.get_by_text(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].fill(value, timeout=5000)
			return

		# 4. Fallback to standard selector fill (10s timeout)
		self.page.fill(selector_or_text, value, timeout=10000)

	def evaluate(self, js: str) -> str:
		val = self.page.evaluate(js)
		try:
			return json.dumps(val, ensure_ascii=False)
		except Exception:
			return str(val)

	def find(self, text: str) -> list[dict]:
		elements = self.page.get_by_text(text, exact=False).all()
		matches = []
		for el in elements:
			try:
				if el.is_visible():
					matches.append({
						"text": el.inner_text(),
						"id": el.get_attribute("id"),
						"class": el.get_attribute("class"),
						"tag": el.evaluate("el => el.tagName.toLowerCase()")
					})
			except Exception:
				continue
		return matches

	def get_interactive_elements(self) -> list[dict]:
		"""
		Scans the active page for visible interactive elements, sets a 
		temporary `data-surfer-id` index on them, and returns their metadata.
		"""
		js_code = """
		() => {
			// Remove any old surfer id attributes
			const oldTags = document.querySelectorAll('[data-surfer-id]');
			for (const tag of oldTags) {
				tag.removeAttribute('data-surfer-id');
			}

			// Define what elements are considered interactive
			const query = 'button, a, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"]';
			const candidates = document.querySelectorAll(query);
			
			const elements = [];
			let count = 0;

			for (const el of candidates) {
				// Check visibility
				const rect = el.getBoundingClientRect();
				if (rect.width === 0 || rect.height === 0) continue;
				
				const style = window.getComputedStyle(el);
				if (style.display === 'none' || style.visibility === 'hidden') continue;
				if (parseFloat(style.opacity) === 0) continue;

				// Determine label using heuristics (innerText, placeholder, values, aria-label)
				let label = '';
				const tagName = el.tagName.toLowerCase();
				if (tagName === 'input') {
					label = el.placeholder || el.getAttribute('aria-label') || el.value || el.name || '';
					if (!label && (el.type === 'checkbox' || el.type === 'radio')) {
						if (el.parentElement && el.parentElement.tagName.toLowerCase() === 'label') {
							label = el.parentElement.innerText;
						} else if (el.id) {
							const labelEl = document.querySelector(`label[for="${el.id}"]`);
							if (labelEl) label = labelEl.innerText;
						}
					}
				} else {
					label = el.innerText || el.textContent || el.getAttribute('aria-label') || '';
				}

				label = label.trim().replace(/\\s+/g, ' ');
				if (label.length > 80) {
					label = label.substring(0, 80) + '...';
				}

				// Assign the temporary index selector
				el.setAttribute('data-surfer-id', String(count));

				elements.push({
					"index": count,
					"tag": tagName,
					"type": el.getAttribute('type') || null,
					"text": label || '[no visible label]'
				});
				count++;
			}
			return elements;
		}
		"""
		return self.page.evaluate(js_code)
