
import logging
import contextlib
from typing import AsyncGenerator
from app.core.config import settings

# Strict Imports per Official Docs
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption

logger = logging.getLogger(__name__)

class AgentBayService:
    def __init__(self):
        self.api_key = settings.AGENTBAY_API_KEY
        if not self.api_key:
            logger.warning("AGENTBAY_API_KEY not set! AgentBay functions will fail.")
        
        # 1. Initialize client
        self.client = AgentBay(api_key=self.api_key)

    @contextlib.asynccontextmanager
    async def start_browser_session(self) -> AsyncGenerator[str, None]:
        """
        Creates an AgentBay session, initializes the browser, 
        and yields the CDP Endpoint URL for Playwright connection.
        Ensures strict cleanup of the session.
        
        Reference: https://www.alibabacloud.com/help/en/agentbay/agentbay-sdk-browser-use
        """
        session = None
        try:
            # 2. Create session (uses browser_latest by default/recommendation)
            logger.info("Creating AgentBay session (image_id='browser_latest')...")
            params = CreateSessionParams(image_id="browser_latest")
            
            # Note: client.create() is synchronous in SDK example
            session_result = self.client.create(params)
            
            if not session_result.success:
                raise RuntimeError(f"Failed to create AgentBay session: {session_result.error_message}")
            
            session = session_result.session
            logger.info("Session created. Initializing browser...")

            # 3. Initialize browser
            # "BrowserOption supports stealth, proxy, fingerprint, and more."
            # We use default as prompt requested "Clean session".
            option = BrowserOption()
            
            ok = await session.browser.initialize_async(option)
            if not ok:
                raise RuntimeError("AgentBay Browser initialization failed")

            # 4. Retrieve CDP endpoint
            endpoint_url = session.browser.get_endpoint_url()
            logger.info(f"Browser initialized. CDP Endpoint: {endpoint_url}")

            yield endpoint_url

        except Exception as e:
            logger.error(f"AgentBay Service Error: {e}")
            raise
        finally:
            # 5. Clean up resources
            if session:
                try:
                    logger.info("Deleting AgentBay session...")
                    session.delete()
                    logger.info("AgentBay session deleted.")
                except Exception as close_err:
                    logger.error(f"Error deleting session: {close_err}")
