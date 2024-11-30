import asyncio
from playwright.async_api import async_playwright
import logging
from datetime import datetime
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file if available
except ImportError:
    logging.warning("python-dotenv not installed. Skipping loading from .env file.")
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Your Raley's credentials - loaded from .env file or environment variables
RALEYS_EMAIL = os.getenv("RALEYS_EMAIL")
RALEYS_PASSWORD = os.getenv("RALEYS_PASSWORD")

# URL Constants
RALEYS_HOME_URL = "https://www.raleys.com/"
UNCLIPPED_MY_OFFERS_URL = "https://www.raleys.com/something-extra/offers-and-savings?fq=SomethingExtra&clip=Unclipped"
MEMBER_DEALS_URL = "https://www.raleys.com/something-extra/offers-and-savings?fq=WeeklyExclusive&clip=Unclipped"
MY_COUPONS_URL = "https://www.raleys.com/something-extra/offers-and-savings?fq=DigitalCoupons&clip=Unclipped"

async def login_and_clip_offers():
    logging.debug("Starting...")
    total_clipped = 0  # Initialize total counter
    async with async_playwright() as p:
        # Start a browser session
        browser = await p.chromium.launch(headless=True)  # set headless=True to run without GUI
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Go to Raley's homepage and click the login button to open the modal
            await page.goto(RALEYS_HOME_URL)
            await page.click('a:has-text("Log In")')  # Click the login link to open the modal
            await page.wait_for_selector('input[name="email"]', timeout=10000)  # Wait for the modal to appear, with a longer timeout

            # Fill in the login form
            await page.fill('input[name="email"]', RALEYS_EMAIL)
            await page.fill('input[name="password"]', RALEYS_PASSWORD)

            # Click the login button using the correct HTML class
            await page.click('button[type="submit"].group.flex.items-center.justify-center')
            await page.wait_for_load_state("networkidle")  # Wait for the page to finish loading after login
            logging.debug("Logged in successfully")

            # Clip Unclipped My Offers
            clipped = await clip_offers(page, UNCLIPPED_MY_OFFERS_URL)
            total_clipped += clipped

            # Clip Member Deals
            clipped = await clip_offers(page, MEMBER_DEALS_URL)
            total_clipped += clipped

            # Clip My Coupons
            clipped = await clip_offers(page, MY_COUPONS_URL)
            total_clipped += clipped

            logging.info(f"Successfully clipped {total_clipped} total offers")
            logging.debug("... Finished")

        
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            await browser.close()

async def clip_offers(page, offers_url):
    offers_clipped = 0  # Initialize counter for this category
    while True:
        # Go to the offers page
        logging.debug(f"Checking {offers_url}")
        await page.goto(offers_url)
        await page.wait_for_timeout(3000)  # Allow time for offers to load

        # Find all clip buttons on the page
        clip_buttons = await page.locator('button[aria-label^="Clip"]:has(svg[alt="scissor"])').all()
        count = len(clip_buttons)
        if count == 0:
            logging.debug(f"No more offers to clip on {offers_url}")
            break

        logging.debug(f"Found {count} offers to clip on {offers_url}")

        # Click each clip button in reverse order to avoid DOM update issues
        for i in range(count - 1, -1, -1):
            try:
                button = clip_buttons[i]
                await button.scroll_into_view_if_needed()
                await button.click()
                logging.debug(f"Clicked clip button {i + 1}.")
                await page.wait_for_timeout(500)  # Allow time for the action to register

                # Check if a modal dialog appears after clicking
                if await page.locator('text="Unfortunately, this offer is no longer available to clip."').is_visible():
                    logging.debug("Offer is no longer available. Clicking OK to continue.")
                    await page.click('button:has-text("OK")')
                    await page.wait_for_timeout(500)
                else:
                    offers_clipped += 1  # Increment counter only if successfully clipped
            except Exception as e:
                logging.warning(f"Failed to clip offer at index {i}: {e}")
                continue

        # Reload the page to check if there are additional offers left to clip
        await page.wait_for_timeout(2000)
    
    return offers_clipped  # Return the number of offers clipped in this category

if __name__ == "__main__":
    # Schedule this script to run daily (use cron for Linux or Task Scheduler for Windows)
    asyncio.run(login_and_clip_offers())

    # To set up a cron job for daily execution:
    # Edit your cron file with `crontab -e` and add the following line:
    # 0 0 * * * /usr/bin/python3 /path/to/raleys-autoclippper.py
    
    # For Windows Task Scheduler, create a new task and set a daily trigger, pointing to the Python executable and the script path.
