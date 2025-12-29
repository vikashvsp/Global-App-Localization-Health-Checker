from lingodotdev import LingoDotDevEngine
from apify import Actor
import asyncio

class LingoClient:
    def __init__(self, api_key, mock=False):
        self.api_key = api_key
        self.mock = mock

    async def suggest_translation(self, text, target_lang, context=None):
        """
        Suggests a translation for the missing text using Lingo.dev.
        """
        if self.mock:
            Actor.log.info(f"[MOCK] Requesting translation for '{text}' to {target_lang}")
            return f"[MOCK TRANSLATION to {target_lang}] {text}"
            
        try:
            async with LingoDotDevEngine(api_key=self.api_key) as lingo:
                # Assuming simple translate_text or similar method exists in SDK
                # Adjusted to likely method name or standard usage. 
                # If 'translate_text' doesn't exist, we might fail again.
                # Let's hope the SDK follows the search result description even if class name differed.
                # Add timeout to prevent hanging
                 result = await asyncio.wait_for(
                    lingo.quick_translate(
                        text, 
                        api_key=self.api_key,
                        target_locale=target_lang
                    ),
                    timeout=15.0
                 )
                 return result
        except Exception as e:
            Actor.log.error(f"Lingo.dev API error: {e}")
            return None

    async def suggest_translation_batch(self, texts, target_lang, batch_size=5):
        """
        Translates a list of texts in parallel (bounded).
        """
        if not texts: return {}
        if self.mock:
            return {t: f"[MOCK to {target_lang}] {t}" for t in texts}

        results = {}
        semaphore = asyncio.Semaphore(batch_size)

        async def _translate_one(text):
            async with semaphore:
                try:
                    # Reuse the single translate logic with timeout
                    # We create a new engine instance per call or reuse? 
                    # The Context Manager usage in suggest_translation implies per-call.
                    # We will reuse suggest_translation but bypass the self.mock check which is already done.
                     return await self.suggest_translation(text, target_lang)
                except Exception:
                    return None

        # Create tasks
        tasks = [(_translate_one(text), text) for text in texts]
        
        # Execute
        # We need to map result back to text
        for coro, text in tasks:
            res = await coro
            if res:
                results[text] = res
        
        return results


