from apify import Actor
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import urljoin, urlparse

class Crawler:
    def __init__(self, start_url, max_pages=5):
        self.start_url = start_url
        self.max_pages = max_pages
        self.visited_urls = set()
        self.crawled_data = []

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            queue = [self.start_url]
            
            while queue and len(self.visited_urls) < self.max_pages:
                url = queue.pop(0)
                if url in self.visited_urls:
                    continue
                
                self.visited_urls.add(url)
                Actor.log.info(f"Crawling: {url}")
                
                try:
                    Actor.log.info(f"DEBUG: Opening new page")
                    page = await context.new_page()
                    Actor.log.info(f"DEBUG: Going to {url}")
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # Extract content
                    Actor.log.info(f"DEBUG: Getting content")
                    content = await page.content()
                    Actor.log.info(f"DEBUG: Parsing soup")
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract visible text nodes, buttons, headings
                    Actor.log.info(f"DEBUG: Extracting text")
                    page_data = self._extract_text(soup, url)
                    Actor.log.info(f"DEBUG: Text extracted, items: {len(page_data['items'])}")
                    self.crawled_data.append(page_data)
                    
                    # Find links for next crawl
                    if len(self.visited_urls) < self.max_pages:
                        Actor.log.info(f"DEBUG: Getting links")
                        links = self._get_links(soup, url)
                        for link in links:
                            if link not in self.visited_urls and link not in queue:
                                queue.append(link)
                                
                    await page.close()
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    Actor.log.error(f"Failed to crawl {url}: {e}")
            
            await browser.close()
        
        return self.crawled_data

    def _extract_text(self, soup, url):
        """Extracts visible text and categorizes it."""
        extracted = []
        
        def get_key(tag, text):
            """Generates a key from ID, Name, or Text."""
            if tag.get('id'):
                return tag['id']
            if tag.get('name'):
                return tag['name']
            # Fallback to slugified text
            slug = "".join(c if c.isalnum() else "_" for c in text[:30]).lower()
            return slug.strip('_')

        # 1. Buttons
        for btn in soup.find_all(['button', 'a']):
            text = btn.get_text(strip=True)
            if text:
                key = get_key(btn, text)
                extracted.append({'type': 'button', 'text': text, 'key': key, 'context': str(btn)[:100]})

        # 2. Headings
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = h.get_text(strip=True)
            if text:
                key = get_key(h, text)
                extracted.append({'type': 'heading', 'text': text, 'key': key, 'context': str(h)[:100]})

        # 3. Label-like text
        # 3. Text Blobs (Robust find_all approach)
        # We capture text from common container tags. 
        # Duplicates are handled by the dedup logic below.
        for tag in soup.find_all(['label', 'span', 'p', 'div', 'li', 'td', 'th']):
            text = tag.get_text(strip=True)
            # Skip if empty or too long (likely code/params)
            if not text or len(text) > 1000:
                continue
            
            # Skip script/style parent content
            if tag.parent.name in ['script', 'style', 'head', 'noscript']:
                continue

            # Heuristic: If it has many children tags, it's likely a container, not a leaf text node.
            # But we want to catch "Mixed content". 
            # Let's try to capture it if it has text.
            
            key = get_key(tag, text)
            
            # Simple typing based on tag
            t_type = 'text'
            if tag.name == 'label': t_type = 'label'
            elif 'error' in str(tag.get('class', '')): t_type = 'error_message'
            
            extracted.append({'type': t_type, 'text': text, 'key': key, 'context': str(tag)[:100]})

        # Dedup extracted items based on text+type
        unique_extracted = []
        seen = set()
        for item in extracted:
            # unique by text, but keep the best key if possible (id > name > slug)
            # simpler: just dedupe by text for now to avoid noise
            key_id = (item['type'], item['text'])
            if key_id not in seen:
                seen.add(key_id)
                unique_extracted.append(item)

        return {
            'url': url,
            'items': unique_extracted
        }

    def _get_links(self, soup, current_url):
        links = []
        base_domain = urlparse(self.start_url).netloc
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(current_url, href)
            parsed = urlparse(full_url)
            
            # Internal links only
            if parsed.netloc == base_domain:
                links.append(full_url)
        
        return links
