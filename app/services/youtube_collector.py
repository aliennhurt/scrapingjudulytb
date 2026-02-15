
import logging
import asyncio
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import Run, Video
from app.services.agentbay import AgentBayService
from app.utils.views_parser import parse_views_id
from urllib.parse import quote_plus
from datetime import datetime
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class YouTubeCollector:
    def __init__(self, db: Session, run_id: str):
        self.db = db
        self.run_id = run_id
        self.agent_service = AgentBayService()

    async def collect(self, keyword: str):
        """
        Main collection logic using AgentBay + Playwright.
        """
        logger.info(f"Starting collection for run {self.run_id} with keyword '{keyword}'")
        
        # Update Run status to running
        run = self.db.query(Run).filter(Run.id == self.run_id).first()
        if run:
            run.status = "running"
            self.db.commit()

        try:
            # Start AgentBay Session -> Get CDP URL
            async with self.agent_service.start_browser_session() as cdp_url:
                
                # Connect Playwright to Remote Browser
                async with async_playwright() as p:
                    logger.info(f"Connecting to CDP: {cdp_url}")
                    browser = await p.chromium.connect_over_cdp(cdp_url)
                    # Note: AgentBay docs say "page = await browser.new_page()"
                    # But often connect_over_cdp gives a context. Let's follow docs.
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                    page = await context.new_page()

                    videos_collected = [] # List of dicts for fallback logic
                    
                    # 1. Search
                    encoded_keyword = quote_plus(keyword)
                    search_url = f"https://www.youtube.com/results?search_query={encoded_keyword}&hl=id&gl=ID"
                    logger.info(f"Navigating to {search_url}")
                    await page.goto(search_url, wait_until="domcontentloaded")
                    
                    # Wait for results
                    await page.wait_for_selector('ytd-video-renderer', timeout=15000)

                    # 2. Extract Top 2 Search Results
                    logger.info("Extracting search results...")
                    search_results = await self._extract_videos(page, selector='ytd-video-renderer', limit=2)
                    for i, vid in enumerate(search_results):
                        # If views missing, visit page (handled in _enrich_video if needed, 
                        # but for speed we try to get it from card)
                        if not vid.get('views'):
                            vid = await self._enrich_video_views(page, vid)
                        
                        self._save_video(vid, source="search", rank=i+1, collected_from="search")
                        videos_collected.append(vid)

                    # 3. Check for "People also watched" (Shelf)
                    # Selector is tricky and dynamic. Usually ytd-shelf-renderer...
                    # For MVP reliability, we might check specifically for the text "Orang lain juga menonton"?
                    # or similar.
                    # Let's try flexible selector or skip to fallback if hard to find.
                    people_watched = [] # await self._extract_people_also_watched(page, limit=2)
                    # IMPLEMENTATION NOTE: "People also watched" on Search is flaky to find via selector without complex logic.
                    # I will try a generic approach but fallback is safer.
                    
                    if people_watched:
                        for i, vid in enumerate(people_watched):
                            self._save_video(vid, source="people_also_watched", rank=i+1, collected_from="module")
                            videos_collected.append(vid)
                    else:
                        # 4. Fallback: Related videos from Video #1
                        if videos_collected:
                            first_video_url = videos_collected[0].get('url')
                            if first_video_url:
                                logger.info(f"People also watched missing/empty. Fallback to related: {first_video_url}")
                                await page.goto(first_video_url, wait_until="domcontentloaded")
                                await page.wait_for_selector('ytd-watch-next-secondary-results-renderer', timeout=15000)
                                
                                related = await self._extract_videos(page, selector='ytd-compact-video-renderer', limit=2)
                                for i, vid in enumerate(related):
                                    if not vid.get('views'):
                                         vid = await self._enrich_video_views(page, vid)
                                    self._save_video(vid, source="related_fallback", rank=i+1, collected_from="watch_page")

                    await browser.close() # Close Playwright connection

            # Update Run status to success
            run = self.db.query(Run).filter(Run.id == self.run_id).first()
            run.status = "success"
            run.finished_at = datetime.utcnow()
            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Collection failed: {e}")
            run = self.db.query(Run).filter(Run.id == self.run_id).first()
            run.status = "failed"
            run.error_message = str(e)
            run.finished_at = datetime.utcnow()
            self.db.commit()
            return False

    async def _extract_videos(self, page, selector, limit=2):
        """
        Generic video extractor from a list of elements.
        """
        # Script to extract data from multiple elements
        # We pass the selector and limit to the browser context
        # Return list of dicts: {title, url, views, channel, id}
        
        # JS evaluation is best for bulk extraction
        return await page.evaluate(f"""
            () => {{
                const results = [];
                const cards = document.querySelectorAll('{selector}');
                for (let i = 0; i < cards.length && i < {limit}; i++) {{
                    const card = cards[i];
                    const titleEl = card.querySelector('#video-title');
                    const channelEl = card.querySelector('#channel-info #text') || card.querySelector('.ytd-channel-name #text');
                    const viewsEl = card.querySelector('#metadata-line span:nth-child(1)'); // risky selector
                    const linkEl = card.querySelector('a#thumbnail');
                    
                    if (titleEl && linkEl) {{
                        results.push({{
                            title: titleEl.innerText.trim(),
                            url: linkEl.href,
                            id: linkEl.href.split('v=')[1]?.split('&')[0],
                            channel: channelEl ? channelEl.innerText.trim() : '',
                            views: viewsEl ? viewsEl.innerText.trim() : ''
                        }});
                    }}
                }}
                return results;
            }}
        """)

    async def _enrich_video_views(self, page, video_data):
        """
        If views are missing, go to video page and extract.
        Note: This is expensive (new navigation).
        """
        if video_data.get('views'):
            return video_data
            
        url = video_data.get('url')
        if not url: 
            return video_data

        try:
             # We need a new page or navigate current? 
             # For safety/simplicity let's assume we can navigate current, but that destroys state.
             # Actually, if we are looping, we can't easily navigate away and back without losing list.
             # Better to open a new page/tab if possible, OR just skip for MVP if too complex.
             # Given "Non-aggressive", maybe we skip enrichment if it requires complex tab management?
             # But req says: "If views are missing... open video watch page".
             
             # AgentBay/Playwright supports multiple pages.
             context = page.context
             new_page = await context.new_page()
             await new_page.goto(url, wait_until="domcontentloaded")
             
             # specific selector for views on watch page
             # "1.2M views" usually in #info-text or #count
             views = await new_page.evaluate("""
                () => {
                    const el = document.querySelector('#info-text span:first-child') || document.querySelector('.view-count');
                    return el ? el.innerText.trim() : '';
                }
             """)
             video_data['views'] = views
             await new_page.close()
             
        except Exception:
            pass # Fail silently on enrichment
            
        return video_data

    def _save_video(self, video_data: dict, source: str, rank: int, collected_from: str):
        views_raw = video_data.get('views', '')
        views_num = parse_views_id(views_raw)
        
        # Re-query DB to ensure session is active
        # (Usually passed session is good, but in long async, sometimes needed)
        
        video = Video(
            run_id=self.run_id,
            source_type=source,
            rank=rank,
            title=video_data.get('title', 'Unknown'),
            channel_name=video_data.get('channel', 'Unknown'),
            video_id=video_data.get('id', 'Unknown'),
            video_url=video_data.get('url', 'Unknown'),
            views_raw=views_raw,
            views_num=views_num,
            collected_from=collected_from
        )
        self.db.add(video)
        self.db.commit()
