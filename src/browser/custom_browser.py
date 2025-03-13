from playwright.sync_api import sync_playwright

async def create_browser_context():
    playwright = sync_playwright().start()
    browser = await playwright.chromium.launch()
    
    # Create context with highlighting disabled
    context = await browser.new_context(
        record_har_path=None,
        record_video_dir=None,
        record_har_url_filter=None,
        # Disable highlighting
        record_har_mode='minimal',
        record_har_content='none',
    )
    
    # Disable debug mode which adds visual highlights
    page = await context.new_page()
    await page.set_extra_http_headers({"playwright-debug": "0"})
    
    return context, page# -*- coding: utf-8 -*-
# @Time    : 2025/1/2
# @Author  : nipurnagarwal
# @ProjectName: browser-use-100XPrompt
# @FileName: browser.py

import asyncio
import os
import platform
import subprocess
import requests
import logging

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import (
	BrowserContext as PlaywrightBrowserContext,
	Playwright,
	async_playwright,
)
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig

from .config import BrowserPersistenceConfig
from .custom_context import CustomBrowserContext
from ..exceptions import PromptException, UnknownBrowserType, UnknownErrorWhileCreatingBrowserContext, FailedToNavigateToUrl

logger = logging.getLogger(__name__)

class BrowserNotFoundError(PromptException):
	"""Exception raised when a browser executable is not found."""
	pass

class CustomBrowser(Browser):

	async def new_context(
		self,
		config: BrowserContextConfig = BrowserContextConfig()
	) -> CustomBrowserContext:
		return CustomBrowserContext(config=config, browser=self)

	async def _setup_browser(self, playwright: Playwright) -> PlaywrightBrowser:
		"""Sets up and returns a Playwright Browser instance."""
		try:
			# Always check for Arc first on macOS
			arc_path = "/Applications/Arc.app/Contents/MacOS/Arc"
			using_arc = platform.system() == "Darwin" and os.path.exists(arc_path)
			
			# If we're on macOS and Arc exists, use it instead of chrome_instance_path
			if using_arc:
				browser_path = arc_path
			else:
				browser_path = self.config.chrome_instance_path

			if self.config.wss_url:
				browser = await playwright.chromium.connect(self.config.wss_url)
				return browser

			# Try to connect to existing browser instance
			try:
				response = requests.get('http://localhost:9222/json/version', timeout=2)
				if response.status_code == 200:
					logger.info('Reusing existing browser instance')
					browser = await playwright.chromium.connect_over_cdp(
						endpoint_url='http://localhost:9222',
						timeout=20000,
					)
					return browser
			except requests.ConnectionError:
				logger.debug('No existing browser instance found, starting new one')

			if browser_path:
				# Kill any existing browser processes that might interfere
				if platform.system() == "Darwin":
					os.system("pkill 'Arc'")
					await asyncio.sleep(1)  # Give it time to close

				# Launch the browser with debugging port
				subprocess.Popen(
					[
						browser_path,
						'--remote-debugging-port=9222',
						'--no-first-run',
						'--no-default-browser-check',
						'--disable-features=Translate',
						'--enable-automation',
						'--disable-blink-features=AutomationControlled',
					] + self.config.extra_chromium_args,
					stdout=subprocess.DEVNULL,
					stderr=subprocess.DEVNULL,
				)

				# Wait for browser to be ready
				for _ in range(10):
					try:
						response = requests.get('http://localhost:9222/json/version', timeout=2)
						if response.status_code == 200:
							break
					except requests.ConnectionError:
						pass
					await asyncio.sleep(1)

				try:
					browser = await playwright.chromium.connect_over_cdp(
						endpoint_url='http://localhost:9222',
						timeout=20000,
					)
					if using_arc:
						logger.info('Successfully connected to Arc browser')
					return browser
				except Exception as e:
					logger.error(f'Failed to connect to browser: {str(e)}')
					raise UnknownErrorWhileCreatingBrowserContext(
						browser_type='chromium',
						exception=e
					)

			# Fallback to launching regular chromium if no specific browser path
			disable_security_args = []
			if self.config.disable_security:
				disable_security_args = [
					'--disable-web-security',
					'--disable-site-isolation-trials',
					'--disable-features=IsolateOrigins,site-per-process',
				]

			browser = await playwright.chromium.launch(
				headless=self.config.headless,
				executable_path=None,  # Let Playwright use its bundled Chromium
				args=[
					'--no-sandbox',
					'--disable-blink-features=AutomationControlled',
					'--disable-infobars',
					'--disable-background-timer-throttling',
					'--disable-popup-blocking',
					'--disable-backgrounding-occluded-windows',
					'--disable-renderer-backgrounding',
					'--enable-automation',
				] + disable_security_args + self.config.extra_chromium_args,
				proxy=self.config.proxy,
			)

			return browser

		except Exception as e:
			logger.error(f'Failed to initialize browser: {str(e)}')
			raise UnknownErrorWhileCreatingBrowserContext(
				browser_type='chromium',
				exception=e
			)
