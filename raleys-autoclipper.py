#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "asyncio",
#     "playwright",
#     "python-dotenv"
# ]
# ///

import asyncio
from playwright.async_api import async_playwright
import logging
from datetime import datetime
import sys
import argparse
import os
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file if available
except ImportError:
    logging.warning("python-dotenv not installed. Skipping loading from .env file.")
import os

# Your Raley's credentials - loaded from .env file or environment variables
RALEYS_EMAIL = os.getenv("RALEYS_EMAIL")
RALEYS_PASSWORD = os.getenv("RALEYS_PASSWORD")

# URL Constants
RALEYS_HOME_URL = "https://www.raleys.com/"
UNCLIPPED_MY_OFFERS_URL = "https://www.raleys.com/something-extra/offers-and-savings?fq=SomethingExtra&clip=Unclipped"
MEMBER_DEALS_URL = "https://www.raleys.com/something-extra/offers-and-savings?fq=WeeklyExclusive&clip=Unclipped"
MY_COUPONS_URL = "https://www.raleys.com/something-extra/offers-and-savings?fq=DigitalCoupons&clip=Unclipped"
SOMETHING_EXTRA_DOLLARS_URL = "https://www.raleys.com/account/something-extra-dollars"

def parse_arguments():
    parser = argparse.ArgumentParser(description='Raley\'s Autoclipper - Automatically clip digital offers')
    parser.add_argument('--head', action='store_true', help='Run browser in headed mode (show GUI)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--log', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                       help='Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--screenshots', action='store_true', help='Take screenshots at key points during execution')
    return parser.parse_args()

def configure_logging(args):
    if args.debug:
        log_level = logging.DEBUG
    elif args.log:
        log_level = getattr(logging, args.log.upper())
    else:
        log_level = logging.INFO
    
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

async def take_screenshot(page, name, screenshots_enabled=False):
    if not screenshots_enabled:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshots_dir = "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    filename = f"{screenshots_dir}/{timestamp}_{name}.png"
    await page.screenshot(path=filename, full_page=True)
    logging.info(f"Screenshot saved: {filename}")

async def toggle_something_extra_dollars(page, screenshots_enabled=False):
    logging.debug("Navigating to Something Extra Dollars page")
    logging.debug(f"Going to URL: {SOMETHING_EXTRA_DOLLARS_URL}")
    await page.goto(SOMETHING_EXTRA_DOLLARS_URL)
    await take_screenshot(page, "something_extra_dollars_page_initial", screenshots_enabled)
    
    logging.debug("Waiting for Something Extra Dollars content to load...")
    
    # Wait for the SE dollars content specifically - look for the dollar amount or SE icon
    try:
        # Wait for either the dollar amount display or the SE icon to appear
        await page.wait_for_selector('svg[alt="se-dollars"], h1:has-text("$"), button:has-text("Activate")', timeout=20000)
        logging.debug("SE Dollars content detected, waiting a bit more for full render...")
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "something_extra_dollars_content_loaded", screenshots_enabled)
    except Exception as e:
        logging.warning(f"SE Dollars content didn't load within timeout: {e}")
        await take_screenshot(page, "something_extra_dollars_timeout", screenshots_enabled)
        
        # Try waiting a bit longer and take another screenshot
        logging.debug("Trying additional wait...")
        await page.wait_for_timeout(5000)
        await take_screenshot(page, "something_extra_dollars_additional_wait", screenshots_enabled)
    
    logging.debug("Looking for Activate button or checking if already activated...")
    
    # First check if there's an Activate button
    activate_button = page.locator('button:has-text("Activate")')
    if await activate_button.is_visible():
        logging.info("Found Activate button - activating Something Extra Dollars")
        await take_screenshot(page, "before_activate_click", screenshots_enabled)
        await activate_button.click()
        logging.debug("Clicked Activate button, waiting 2 seconds...")
        await page.wait_for_timeout(2000)  # Allow time for the action to register
        await take_screenshot(page, "after_activate_click", screenshots_enabled)
        return
    
    # Fallback: try the old toggle switch method
    try:
        logging.debug("No Activate button found, looking for toggle switch...")
        await page.wait_for_selector('button[role="switch"]', timeout=5000)
        logging.debug("Toggle switch found")
        
        is_checked = await page.get_attribute('button[role="switch"]', 'aria-checked')
        logging.debug(f"Toggle switch aria-checked value: {is_checked}")
        if is_checked == "false":
            logging.info("Activating Something Extra Dollars via toggle")
            await take_screenshot(page, "before_toggle_click", screenshots_enabled)
            await page.click('button[role="switch"]')
            await page.wait_for_timeout(1000)
            await take_screenshot(page, "after_toggle_click", screenshots_enabled)
        else:
            logging.debug("Toggle switch is already on.")
    except:
        logging.info("Something Extra Dollars may already be activated - no Activate button or toggle found")

async def login_and_clip_offers(args):
    logging.debug("Starting...")
    total_clipped = 0  # Initialize total counter
    screenshots_enabled = args.screenshots
    async with async_playwright() as p:
        # Start a browser session
        headed = args.head
        logging.debug(f"Running in {'headed' if headed else 'headless'} mode")
        arc_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Arc/1.48.1"
        logging.debug("Launching browser...")
        
        # Minimal stealth - only hide the most obvious automation indicator
        browser = await p.chromium.launch(
            headless=not headed,
            args=['--disable-blink-features=AutomationControlled'] if not headed else []
        )
        
        logging.debug("Creating browser context...")
        context = await browser.new_context(
            user_agent=arc_user_agent,
            viewport={'width': 1920, 'height': 1080},  # Set consistent viewport size
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9'
            }
        )
        
        # Only hide the webdriver property
        if not headed:
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
        
        logging.debug("Creating new page...")
        page = await context.new_page()
        
        try:
            # Go to Raley's homepage and click the login button to open the modal
            logging.debug(f"Navigating to Raley's homepage: {RALEYS_HOME_URL}")
            await page.goto(RALEYS_HOME_URL)
            logging.debug("Waiting for page to load...")
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            logging.debug("Page reached domcontentloaded state")
            await take_screenshot(page, "homepage_loaded", screenshots_enabled)
            
            logging.debug("Looking for login link...")
            await page.click('a:has-text("Log In")')  # Click the login link to open the modal
            logging.debug("Clicked login link, waiting for email input field...")
            await page.wait_for_selector('input[name="email"]', timeout=10000)  # Wait for the modal to appear, with a longer timeout
            await take_screenshot(page, "login_modal_open", screenshots_enabled)

            # Fill in the login form
            logging.debug("Filling in email field...")
            await page.fill('input[name="email"]', RALEYS_EMAIL)
            logging.debug("Filling in password field...")
            await page.fill('input[name="password"]', RALEYS_PASSWORD)
            await take_screenshot(page, "login_form_filled", screenshots_enabled)

            # Click the login button using the correct HTML class
            logging.debug("Clicking login submit button...")
            await page.click('button[type="submit"].group.flex.items-center.justify-center')
            
            # Wait for login modal to close (indicates successful login)
            logging.debug("Waiting for login modal to close...")
            try:
                await page.wait_for_selector('input[name="email"]', state="hidden", timeout=10000)
                logging.debug("Login modal closed")
            except:
                logging.warning("Login modal may not have closed")
            
            # Wait additional time for login to fully process
            logging.debug("Waiting for login to complete...")
            await page.wait_for_timeout(3000)
            await take_screenshot(page, "after_login", screenshots_enabled)
            
            # Check if we're actually logged in by looking for the user greeting
            logging.debug("Checking if login was successful...")
            try:
                # Look for the "Hi, [Name]" pattern which indicates successful login
                await page.wait_for_selector('span:has-text("Hi,"):has(+ span.skip-translation)', timeout=5000)
                logging.info("Login confirmed - found user greeting")
            except:
                logging.warning("Login may have failed - user greeting not found")
                # Try alternative login indicator - check if we still see "Log In" link
                try:
                    login_link = await page.locator('a:has-text("Log In")').is_visible()
                    if login_link:
                        logging.error("Login failed - still showing Log In link")
                        await take_screenshot(page, "login_failed", screenshots_enabled)
                    else:
                        logging.info("Login may have succeeded - no Log In link visible")
                except:
                    logging.warning("Could not determine login status")

            # Clip Unclipped My Offers
            logging.debug("Starting to clip Unclipped My Offers...")
            clipped = await clip_offers(page, UNCLIPPED_MY_OFFERS_URL, screenshots_enabled)
            total_clipped += clipped
            logging.debug(f"Clipped {clipped} from Unclipped My Offers")

            # Clip Member Deals
            logging.debug("Starting to clip Member Deals...")
            clipped = await clip_offers(page, MEMBER_DEALS_URL, screenshots_enabled)
            total_clipped += clipped
            logging.debug(f"Clipped {clipped} from Member Deals")

            # Clip My Coupons
            logging.debug("Starting to clip My Coupons...")
            clipped = await clip_offers(page, MY_COUPONS_URL, screenshots_enabled)
            total_clipped += clipped
            logging.debug(f"Clipped {clipped} from My Coupons")

            # Toggle Something Extra Dollars switch
            logging.debug("Starting Something Extra Dollars toggle...")
            try:
                await toggle_something_extra_dollars(page, screenshots_enabled)
            except Exception as e:
                logging.warning(f"Failed to toggle Something Extra Dollars: {e}")

            logging.info(f"Successfully clipped {total_clipped} total offers")
            logging.debug("Process completed successfully")

        
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            logging.debug(f"Current page URL: {page.url}")
        finally:
            logging.debug("Closing browser...")
            await browser.close()

async def clip_offers(page, offers_url, screenshots_enabled=False):
    offers_clipped = 0  # Initialize counter for this category
    logging.debug(f"Starting clip_offers for {offers_url}")
    page_counter = 1
    
    while True:
        # Go to the offers page
        logging.info(f"Navigating to {offers_url}")
        try:
            logging.debug(f"Calling page.goto for {offers_url}")
            await page.goto(offers_url, timeout=30000)
            logging.debug("page.goto completed, waiting for domcontentloaded...")
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            logging.info(f"Successfully loaded {offers_url}")
        except Exception as e:
            logging.error(f"Failed to navigate to {offers_url}: {e}")
            logging.debug(f"Navigation error details: {type(e).__name__}: {str(e)}")
            return offers_clipped
        
        logging.debug("Waiting 3 seconds for offers to load...")
        await page.wait_for_timeout(3000)  # Allow time for offers to load

        # Take screenshot of the offers page
        page_name = offers_url.split('=')[-1] if '=' in offers_url else 'offers'
        await take_screenshot(page, f"{page_name}_page_{page_counter}", screenshots_enabled)

        # Find all clip buttons on the page
        logging.debug("Looking for clip buttons on page...")
        clip_buttons = await page.locator('button[aria-label^="Clip"]:has(svg[alt="scissor"])').all()
        count = len(clip_buttons)
        logging.debug(f"Found {count} clip buttons")
        if count == 0:
            logging.debug(f"No more offers to clip on {offers_url}")
            break

        logging.debug(f"Found {count} offers to clip on {offers_url}")

        # Click each clip button in reverse order to avoid DOM update issues
        logging.debug(f"Starting to click {count} buttons in reverse order...")
        for i in range(count - 1, -1, -1):
            try:
                logging.debug(f"Processing button {i + 1} of {count}")
                button = clip_buttons[i]
                logging.debug("Scrolling button into view...")
                await button.scroll_into_view_if_needed()
                logging.debug("Clicking button...")
                await button.click()
                logging.debug(f"Clicked clip button {i + 1}.")
                logging.debug("Waiting 500ms after click...")
                await page.wait_for_timeout(500)  # Allow time for the action to register

                # Check if a modal dialog appears after clicking
                logging.debug("Checking for unavailable offer modal...")
                if await page.locator('text="Unfortunately, this offer is no longer available to clip."').is_visible():
                    logging.debug("Offer is no longer available. Clicking OK to continue.")
                    await take_screenshot(page, f"unavailable_offer_modal", screenshots_enabled)
                    # Use more specific selector for the modal's OK button
                    await page.locator('[data-testid="modal-overlay"] button:has-text("OK")').click()
                    await page.wait_for_timeout(500)
                else:
                    offers_clipped += 1  # Increment counter only if successfully clipped
                    logging.debug(f"Successfully clipped offer {i + 1}, total clipped: {offers_clipped}")
            except Exception as e:
                logging.warning(f"Failed to clip offer at index {i}: {e}")
                logging.debug(f"Button click error details: {type(e).__name__}: {str(e)}")
                continue

        # Reload the page to check if there are additional offers left to clip
        logging.debug("Waiting 2 seconds before checking for more offers...")
        await page.wait_for_timeout(2000)
        page_counter += 1
    
    logging.debug(f"Finished clipping offers from {offers_url}, total clipped: {offers_clipped}")
    return offers_clipped  # Return the number of offers clipped in this category

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging based on arguments
    configure_logging(args)
    
    # Schedule this script to run daily (use cron for Linux or Task Scheduler for Windows)
    asyncio.run(login_and_clip_offers(args))

    # To set up a cron job for daily execution:
    # Edit your cron file with `crontab -e` and add the following line:
    # 0 0 * * * /usr/bin/python3 /path/to/raleys-autoclippper.py
    
    # For Windows Task Scheduler, create a new task and set a daily trigger, pointing to the Python executable and the script path.
