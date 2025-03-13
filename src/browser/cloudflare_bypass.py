import asyncio
from playwright.async_api import Page
import logging
import platform
import os

logger = logging.getLogger(__name__)

class CloudflareBypass:
    def __init__(self, page: Page):
        self.page = page
        
    async def find_and_click_checkbox(self):
        """Find and click the Cloudflare checkbox"""
        try:
            # Look for iframe containing the checkbox
            iframe = await self.page.wait_for_selector("iframe[src*='challenges']", timeout=5000)
            if iframe:
                frame = await iframe.content_frame()
                if frame:
                    # Wait for and click the checkbox
                    checkbox = await frame.wait_for_selector("#challenge-stage input[type='checkbox']", timeout=5000)
                    if checkbox:
                        await checkbox.click()
                        return True
            return False
        except Exception as e:
            logger.debug(f"No checkbox found: {str(e)}")
            return False
            
    async def handle_verification_directly(self):
        """Handle verification by directly interacting with challenge elements"""
        try:
            # Look for the challenge iframe
            iframe = await self.page.wait_for_selector("iframe[src*='challenges']", timeout=5000)
            if iframe:
                frame = await iframe.content_frame()
                if frame:
                    # Try to find and click any verification button or element
                    selectors = [
                        ".mark",  # Common class for verification marks
                        "#challenge-stage button",
                        "input[type='checkbox']",
                        "[class*='verify']",
                        "[class*='submit']"
                    ]
                    
                    for selector in selectors:
                        try:
                            element = await frame.wait_for_selector(selector, timeout=2000)
                            if element:
                                await element.click()
                                await asyncio.sleep(2)
                                return True
                        except:
                            continue
            return False
        except Exception as e:
            logger.debug(f"Direct verification failed: {str(e)}")
            return False

    async def wait_for_challenge_completion(self):
        """Wait for the challenge to complete"""
        try:
            # Wait for challenge elements to disappear
            await self.page.wait_for_selector("#challenge-running", state="hidden", timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            return True
        except Exception as e:
            logger.debug(f"Challenge wait failed: {str(e)}")
            return False

    async def bypass(self) -> bool:
        """Main method to bypass Cloudflare protection"""
        try:
            # Check if we need to handle Cloudflare
            challenge_selectors = [
                "#challenge-running",
                "iframe[src*='challenges']",
                "#challenge-form",
                ".ray-id"
            ]
            
            challenge_detected = False
            for selector in challenge_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        challenge_detected = True
                        break
                except:
                    continue
                    
            if not challenge_detected:
                return True
                
            logger.info("Cloudflare challenge detected, attempting bypass...")
            
            # Try clicking checkbox first
            if await self.find_and_click_checkbox():
                logger.info("Clicked Cloudflare checkbox")
                await asyncio.sleep(2)
            
            # Try direct verification method
            if await self.handle_verification_directly():
                logger.info("Handled verification directly")
            
            # Wait for challenge completion
            if await self.wait_for_challenge_completion():
                logger.info("Challenge completed successfully")
                return True
                
            logger.warning("Could not complete Cloudflare challenge")
            return False
            
        except Exception as e:
            logger.error(f"Error during Cloudflare bypass: {str(e)}")
            return False 