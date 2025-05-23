import asyncio
import json
import logging
import os
from pathlib import Path
import random
from playwright.async_api import async_playwright, Page
from datetime import datetime, time

Path("./screenshots").mkdir(parents=True, exist_ok=True)
Path("./data").mkdir(parents=True, exist_ok=True)
Path("./logs").mkdir(parents=True, exist_ok=True)

def create_screenshot_path(email: str, name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    account_dir = Path("./screenshots") / email.replace("@", "_")
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir / f"{name}_{timestamp}.png"

class EmailLogger:
    """Specific logger for each email account that saves to a logs.txt file"""
    def __init__(self, email: str):
        self.email = email
        self.log_dir = Path("./logs") / email.replace("@", "_")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "logs.txt"

        self.logger = logging.getLogger(email)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)

    def log(self, message: str, level: str = "info"):
        """Logs a message"""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)

        print(f"[{self.email}] {message}")

class SessionStorage:
    _instance = None
    SESSIONS_FILE = "data/sessions.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionStorage, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.sessions = []
        self._ensure_sessions_file()
        self.load_sessions()

    def _ensure_sessions_file(self):
        """Creates the sessions.json file if it doesn't exist"""
        if not Path(self.SESSIONS_FILE).exists():
            with open(self.SESSIONS_FILE, 'w') as f:
                json.dump([], f)
            print(f"✅ File {self.SESSIONS_FILE} created successfully")

    def load_sessions(self):
        """Loads sessions from the JSON file"""
        try:
            with open(self.SESSIONS_FILE, 'r') as f:
                self.sessions = json.load(f)
            print(f"✅ Sessions loaded from {self.SESSIONS_FILE}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ Error loading sessions: {str(e)} - Creating new file")
            self.sessions = []
            with open(self.SESSIONS_FILE, 'w') as f:
                json.dump(self.sessions, f)
        return self.sessions

    def save_sessions(self):
        """Saves sessions to the JSON file"""
        with open(self.SESSIONS_FILE, 'w') as f:
            json.dump(self.sessions, f, indent=2)
        print(f"💾 Sessions saved to {self.SESSIONS_FILE}")

    def find_session(self, email):
        for session in self.sessions:
            if session['email'] == email:
                return session
        return None

    def update_or_add_session(self, email: str, password=None, arl=None, enable=True):
        session = self.find_session(email)
        timestamp = int(datetime.now().timestamp())

        if session:
            if password is not None:
                session['password'] = password
            if arl is not None:
                session['arl'] = arl
            session['lastUpdated'] = timestamp
            session['enable'] = enable
        else:
            if password is None:
                raise ValueError("Password is required for new sessions")
            new_session = {
                'email': email,
                'password': password,
                'arl': arl,
                'lastUpdated': timestamp
            }
            self.sessions.append(new_session)

        self.save_sessions()

    def get_sessions(self):
        sessions = []

        for session in self.sessions:
            last_updated = session.get('lastUpdated') or 0
            expired = last_updated < datetime.now().timestamp() - (15 * 24 * 3600)
            no_arl = session.get('arl') is None or session.get('arl') == ""

            if no_arl or expired:
                sessions.append(session)

        return sessions

    def get_valid_sessions(self, max_age_days=1):
        now = datetime.now().timestamp()
        valid_sessions = []

        for session in self.sessions:
            if 'arl' not in session:
                continue

            if not session.get('lastUpdated'):
                continue

            age_seconds = now - session['lastUpdated']
            age_days = age_seconds / (24 * 3600)
            if age_days <= max_age_days:
                valid_sessions.append(session)

        return valid_sessions

class Session:
    def __init__(self, email: str, password: str, arl=None, enable=None):
        self.email = email
        self.password = password
        self.arl = arl
        self.enable = enable if enable is not None else True
        self.storage = SessionStorage()

    def __repr__(self):
        return f"Session(email={self.email}, enable={self.enable}, arl={'******' if self.arl else 'None'})"

    def __str__(self):
        return self.__repr__()

    def save(self):
        self.storage.update_or_add_session(
            email=self.email,
            password=self.password,
            arl=self.arl,
            enable=self.enable
        )

    @classmethod
    def load(cls, email: str):
        storage = SessionStorage()
        session_data = storage.find_session(email)
        if session_data:
            return cls(
                email=session_data['email'],
                password=session_data['password'],
                enable=session_data.get('enable', True),
                arl=session_data.get('arl'),
            )
        return None

    @classmethod
    def load_without_arl(cls):
        storage = SessionStorage()
        return [
            cls(
                email=s['email'],
                password=s['password'],
                enable=s.get('enable', True),
                arl=s.get('arl'),
            )
            for s in storage.get_sessions()
        ]

    @classmethod
    def get_valid_sessions(cls, max_age_days=30):
        storage = SessionStorage()
        return [
            cls(
                email=s['email'],
                password=s['password'],
                arl=s.get('arl'),
                enable=s.get('enable', True)
            )
            for s in storage.get_valid_sessions(max_age_days)
        ]

class CookieManager:
    @staticmethod
    async def get_arl_cookie(context):
        cookies = await context.cookies()
        for cookie in cookies:
            if cookie.get("name") == "arl":
                return cookie.get("value")
        return None

    @staticmethod
    async def clear_cookies(context, logger: EmailLogger):
        await context.clear_cookies()
        logger.log("✅ All cookies cleared")

class LoginManager:
    @staticmethod
    async def accept_cookies(page: Page, email: str, logger: EmailLogger):
        try:
            screenshot_path = create_screenshot_path(email, "cookies")
            cookies_button = page.get_by_test_id("gdpr-btn-accept-all")

            if await cookies_button.count() > 0:
                await page.screenshot(path=screenshot_path)
                await cookies_button.click(timeout=10000)
                logger.log("✅ Cookies accepted successfully")
                return True

            logger.log("❌ Cookies button not found")
            await page.screenshot(path=create_screenshot_path(email, "error_cookies"))
            return False
        except Exception as e:
            logger.log(f"❌ Error accepting cookies: {str(e)}")
            await page.screenshot(path=create_screenshot_path(email, "error_cookies_exception"))
            return False

    @staticmethod
    async def fill_login_form(page: Page, session: Session, logger: EmailLogger):
        try:
            email = session.email
            screenshot_path = create_screenshot_path(email, "login_form")

            await page.get_by_test_id("email-field").type(email, delay=100)
            logger.log("✅ Email entered successfully")

            await page.get_by_test_id("password-field").type(session.password, delay=100)
            logger.log("✅ Password entered successfully")

            await page.screenshot(path=screenshot_path)
            await page.get_by_test_id("login-button").click(timeout=15000)
            logger.log("🔄 Sending credentials...")
        except Exception as e:
            logger.log(f"❌ Error in login form: {str(e)}")
            await page.screenshot(path=create_screenshot_path(email, "error_login_form"))
            raise

    @staticmethod
    async def verify_successful_login(page: Page, email: str, logger: EmailLogger):
        try:
            screenshot_path = create_screenshot_path(email, "login_success")
            await page.wait_for_url("https://www.deezer.com/en/*", timeout=20000)
            logger.log("✅ Login successful - Redirection completed")

            await page.wait_for_selector("text=Home", timeout=25000)
            logger.log("✅ 'Home' element found")
            await page.screenshot(path=screenshot_path)
            return True
        except Exception as e:
            logger.log(f"❌ Error verifying login: {str(e)}")
            await page.screenshot(path=create_screenshot_path(email, "error_login_verification"))
            return False

class CaptchaHandler:
    @staticmethod
    async def handle_captcha(page: Page, email: str, logger: EmailLogger):
        try:
            screenshot_path = create_screenshot_path(email, "captcha_detected")
            await page.wait_for_timeout(3000)

            captcha_frame = page.frame_locator("iframe[src*='recaptcha']")
            if captcha_frame.first:
                logger.log("🛡️ CAPTCHA detected - Manual intervention required")
                await page.screenshot(path=screenshot_path)

                logger.log("⏳ Waiting for manual resolution (3 minutes)...")

                try:
                    await page.wait_for_selector("iframe[src*='recaptcha']", state="detached", timeout=180000)

                    logger.log("✅ CAPTCHA resolved successfully")
                    await page.screenshot(path=create_screenshot_path(email, "captcha_solved"))
                    return True
                except Exception as e:
                    logger.log(f"❌ CAPTCHA not resolved exception: {str(e)}")
                    return False

            return False
        except Exception as e:
            logger.log(f"❌ Error handling CAPTCHA: {str(e)}")
            await page.screenshot(path=create_screenshot_path(email, "error_captcha"))
            return False

class PlaywrightManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.lock = asyncio.Lock()
        self.user_data_dir = os.path.join(os.getcwd(), 'user_data')

    async def start(self, logger: EmailLogger):
        async with self.lock:
            if not self.playwright:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch_persistent_context(
                    self.user_data_dir,
                    headless=False,
                    viewport={'width': 1200, 'height': 700}
                )
                logger.log("🚀 Chromium browser started with persistent context")

    async def stop(self):
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                print("🛑 Browser and Playwright stopped successfully")
        except Exception as e:
            print(f"⚠️ Error closing resources: {str(e)}")
        finally:
            self.playwright = None
            self.browser = None

    async def capture_requests(self, url: str, session: Session, logger: EmailLogger):
        if not self.browser:
            await self.start(logger)

        async with self.lock:
            page = None
            try:
                page = await self.browser.new_page()
                logger.log(f"\n🔹 Starting session for: {session.email}")

                await page.goto(url, wait_until="networkidle", timeout=15000)
                current_url = page.url

                if "www.deezer.com/en" in current_url:
                    logger.log("🔄 Existing session detected, clearing cookies...")
                    await CookieManager.clear_cookies(page.context, logger)
                    await page.goto(url, wait_until="networkidle", timeout=15000)

                await page.screenshot(path=create_screenshot_path(session.email, "initial_page"))

                logger.log("🌐 Login page loaded successfully")

                if not await LoginManager.accept_cookies(page, session.email, logger):
                    logger.log(f"❌ Could not accept cookies for {session.email}")

                await LoginManager.fill_login_form(page, session, logger)
                await page.wait_for_timeout(3000)

                if not await CaptchaHandler.handle_captcha(page, session.email, logger):
                    logger.log(f"❌ CAPTCHA not resolved for {session.email}")
                    return None

                if await LoginManager.verify_successful_login(page, session.email, logger):
                    arl_cookie = await CookieManager.get_arl_cookie(page.context)
                    if arl_cookie:
                        logger.log(f"🔑 ARL obtained for {session.email}: {arl_cookie[:15]}...")
                        session.arl = arl_cookie
                        session.save()

                        await page.screenshot(path=create_screenshot_path(session.email, "successful_session"))
                        return session
                    else:
                        logger.log(f"❌ ARL cookie not found for {session.email}")
                else:
                    logger.log(f"❌ Login failed for {session.email}")

                return None

            except Exception as e:
                logger.log(f"‼️ Critical error for {session.email}: {str(e)}")
                if page:
                    await page.screenshot(path=create_screenshot_path(session.email, "critical_error"))
                return None
            finally:
                if page:
                    await page.close()

    async def process_accounts(self):
        accounts = Session.load_without_arl()
        results = []
        total = len(accounts)

        print(f"\n📦 Starting processing of {total} accounts with expired or missing ARL")

        for index, account in enumerate(accounts, 1):
            print(f"📝 [{index}/{total}] Processing account: {account.email}")

            logger = EmailLogger(account.email)

            result = await self.capture_requests(
                "https://account.deezer.com/en/login/",
                session=account,
                logger=logger
            )

            if result and result.arl:
                results.append({
                    'email': account.email,
                    'success': True,
                    'arl': result.arl,
                    'lastUpdated': datetime.now().timestamp()
                })
                logger.log(f"✅ [{index}/{total}] Success - ARL obtained")
            else:
                results.append({
                    'email': account.email,
                    'success': False,
                    'arl': None,
                    'lastUpdated': None
                })
                logger.log(f"❌ [{index}/{total}] Failure - Could not obtain ARL")

            wait_time = random.uniform(2, 5)
            print(f"⏳ Waiting {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)

        print("\n📊 EXECUTION SUMMARY:")
        print(f"├── Total accounts: {total}")
        print(f"├── Processed accounts: {len(results)}")
        print(f"├── ARLs obtained: {sum(1 for r in results if r['success'])}")
        print(f"└── Failures: {len(results) - sum(1 for r in results if r['success'])}")
        print(f"\n📁 Screenshots saved in: {Path('./screenshots').absolute()}")

        return results

async def main():
    print("\n" + "="*50)
    print("🚀 DEEZER SESSION MANAGER")
    print("="*50)
    print(f"📂 Working directory: {Path().absolute()}\n")

    sessions_file = Path("data/sessions.json")
    if not sessions_file.exists() or os.path.getsize(sessions_file) == 0:
        print("⚠️ The file data/sessions.json does not exist or is empty")
        print("ℹ️ Please create the file with the accounts in the appropriate format")
        return

    playwright_manager = PlaywrightManager()

    try:
        results = await playwright_manager.process_accounts()

        print("\n🎯 FINAL RESULTS:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            arl_preview = f"ARL: {result['arl'][:10]}..." if result['success'] else "NO ARL"
            print(f"{status} {result['email']} - {arl_preview}")

        # Guardar los ARLs exitosos en archivos separados por type
        arls_by_type = {}
        for result in results:
            if result['success'] and result['arl']:
                # Obtener el type desde sessions.json si no está en el resultado
                type_value = None
                if 'type' in result:
                    type_value = result['type']
                else:
                    with open(sessions_file, 'r') as f:
                        sessions = json.load(f)
                    session = next((s for s in sessions if s['email'] == result['email']), None)
                    type_value = session.get('type', 'unknown') if session else 'unknown'
                arls_by_type.setdefault(type_value, []).append(result['arl'])

        if not arls_by_type:
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)
            for s in sessions:
                type_value = s.get('type', 'unknown')
                if s.get('arl'):
                    arls_by_type.setdefault(type_value, []).append(s['arl'])

        for type_value, arls in arls_by_type.items():
            arls_path = Path(f'data/arls_{type_value}.txt')
            arls_str = ','.join(arls)
            with open(arls_path, 'w') as f:
                f.write(arls_str)
            print(f"\n📝 Archivo {arls_path} creado con {len(arls)} ARLs para type '{type_value}'")

    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    finally:
        print("\n🔧 Cleaning up resources...")
        await playwright_manager.stop()
        print("\n🏁 Process completed\n")

if __name__ == "__main__":
    asyncio.run(main())
