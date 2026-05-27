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

	def get_text(self, selector: str) -> str:
		return self.page.locator(selector).inner_text()

	def click(self, selector: str):
		self.page.click(selector)

	def fill(self, selector: str, value: str):
		self.page.fill(selector, value)

	def evaluate(self, js: str) -> str:
		val = self.page.evaluate(js)
		try:
			return json.dumps(val, ensure_ascii=False)
		except Exception:
			return str(val)
