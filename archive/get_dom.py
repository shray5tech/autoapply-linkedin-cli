from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os, time
load_dotenv()

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    page = b.new_page()
    page.goto('https://www.naukri.com/nlogin/login', wait_until='domcontentloaded')
    time.sleep(3)
    page.locator('#usernameField').fill(os.getenv('NAUKRI_EMAIL'))
    time.sleep(1)
    page.locator('#passwordField').fill(os.getenv('NAUKRI_PASS'))
    time.sleep(1)
    page.get_by_role('button', name='Login', exact=True).click()
    time.sleep(5)
    page.goto('https://www.naukri.com/mnjuser/profile', wait_until='domcontentloaded')
    time.sleep(4)
    html = page.content()
    open('profile_dom.html', 'w', encoding='utf-8').write(html)
    print('Saved profile_dom.html — share this file')
    b.close()