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
		elements = self.page.get_by_text(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			return visible_elements[0].inner_text()
		return self.page.locator(selector_or_text).inner_text()

	def click(self, selector_or_text: str):
		# 1. Try to click by visible text
		elements = self.page.get_by_text(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].click()
			return

		# 2. Try to click by label
		elements = self.page.get_by_label(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].click()
			return

		# 3. Fallback to standard selector click
		self.page.click(selector_or_text)

	def fill(self, selector_or_text: str, value: str):
		# 1. Try to fill by label (best practice for form inputs)
		elements = self.page.get_by_label(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].fill(value)
			return

		# 2. Try to fill by placeholder
		elements = self.page.get_by_placeholder(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].fill(value)
			return

		# 3. Try to fill by visible text
		elements = self.page.get_by_text(selector_or_text, exact=False).all()
		visible_elements = [el for el in elements if el.is_visible()]
		if visible_elements:
			visible_elements[0].fill(value)
			return

		# 4. Fallback to standard selector fill
		self.page.fill(selector_or_text, value)

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
