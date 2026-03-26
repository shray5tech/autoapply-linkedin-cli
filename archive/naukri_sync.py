import json
import time
import random
import logging
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
load_dotenv()

PROFILE_JSON = 'profile/profile.json'
RESUME_PATH  = 'profile/Shray_Bisht_Master_Resume_v4.pdf'
NAUKRI_EMAIL = os.getenv('NAUKRI_EMAIL')
NAUKRI_PASS  = os.getenv('NAUKRI_PASS')
HEADLESS     = False
SCREENSHOTS  = 'outputs/screenshots'

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

def load_profile():
    with open(PROFILE_JSON) as f:
        return json.load(f)

def human_delay(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))

def screenshot(page, name):
    os.makedirs(SCREENSHOTS, exist_ok=True)
    ts = datetime.now().strftime('%H%M%S')
    path = SCREENSHOTS + '/' + name + '_' + ts + '.png'
    page.screenshot(path=path)
    log.info('Screenshot -> ' + path)

def login(page):
    log.info('Logging into Naukri...')
    page.goto('https://www.naukri.com/nlogin/login', wait_until='domcontentloaded')
    human_delay(3, 4)
    page.wait_for_selector('#usernameField', state='visible', timeout=15000)
    page.locator('#usernameField').fill(NAUKRI_EMAIL)
    human_delay(0.5, 1.0)
    page.wait_for_selector('#passwordField', state='visible', timeout=15000)
    page.locator('#passwordField').fill(NAUKRI_PASS)
    human_delay(0.5, 1.0)
    page.get_by_role('button', name='Login', exact=True).click()
    page.wait_for_load_state('networkidle')
    human_delay(2, 3)
    screenshot(page, 'login')
    log.info('Logged in')

HEADLINE_SEL = 'textarea#resumeHeadlineTxt, textarea.materialize-textarea, .resumeHeadlineEdit textarea'
SAVE_SEL     = '.resumeHeadlineEdit button.btn-dark-ot, .profileEditDrawer button.btn-dark-ot'
SKILL_INP    = '.keySkillsEdit input[type=text], .profileEditDrawer .keySkillSuggCont input[type=text]'
SKILL_SAVE   = '.keySkillsEdit button.btn-dark-ot, .profileEditDrawer button.btn-dark-o