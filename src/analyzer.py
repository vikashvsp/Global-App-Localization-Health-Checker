from langdetect import detect, DetectorFactory, LangDetectException
import re

DetectorFactory.seed = 0

class Analyzer:
    def __init__(self, target_languages, base_language='en'):
        self.target_languages = target_languages
        self.base_language = base_language

    def detect_language(self, text):
        try:
            return detect(text)
        except LangDetectException:
            return None

    def analyze_page(self, page_data):
        """Analyzes a single page's data for localization issues."""
        issues = []
        
        # Determine expected language for the page (heuristic for now: assume base URL structure or default to base_lang)
        # Real impl might look at /es/ in URL, but for MVP we might just check if text matches ANY target lang
        # actually, the requirement is "English fallback in non-English page".
        # But if we are scanning "example.com", we assumed it's the base language version?
        # The user input has "languages": ["en", "hi", "es"].
        # If we crawl, we might hit example.com/es. 
        # For MVP, let's assume the crawler finds pages, and we try to guess the INTENDED language of that page
        # OR we just check against ALL target languages.
        
        # Let's simplify: We check each text string.
        # If it looks like English, but we are supposed to be in 'hi' mode? 
        # Since we don't know which page maps to which language yet without URL analysis...
        # Let's try to detect the DOMINANT language of the page first.
        
        page_text_blob = " ".join([item['text'] for item in page_data['items']])
        detected_page_lang = self.detect_language(page_text_blob[:1000]) # Detect from first 1000 chars
        
        # If detection fails, assume base val
        current_page_lang = detected_page_lang if detected_page_lang else self.base_language
        
        for item in page_data['items']:
            text = item['text']
            key = item.get('key') # Extract key
            item_lang = self.detect_language(text)
            
            # 1. Broken Placeholders
            if self._has_broken_placeholders(text):
                issues.append({
                    'type': 'broken_placeholder',
                    'text': text,
                    'key': key, # Pass key
                    'severity': 'high', 
                    'context': item['context']
                })

            # 2. Mixed Language (if item lang differs from page lang, and both are confident)
            # Only flag if text is long enough to be confident
            if len(text) > 20 and item_lang and item_lang != current_page_lang:
                 # Special case: English fallback
                 if item_lang == 'en' and current_page_lang != 'en':
                     issues.append({
                        'type': 'fallback_text',
                        'text': text,
                        'key': key, # Pass key
                        'severity': 'medium',
                        'context': item['context']
                     })
                 else:
                     issues.append({
                        'type': 'mixed_language',
                        'text': text,
                        'key': key, # Pass key
                        'severity': 'medium',
                        'context': item['context'],
                        'details': f'Detected {item_lang} on {current_page_lang} page'
                     })

            # 3. Missing Translation (Heuristic: same as fallback really, or if we had a reference)
            # For MVP without a reference JSON, "Missing Translation" is hard to distinguish from "Fallback".
            # We will treat "English text on non-English page" as the primary "Missing Translation" candidate.

        return {
            'url': page_data['url'],
            'detected_language': current_page_lang,
            'issues': issues
        }

    def _has_broken_placeholders(self, text):
        # Checks for things like {{name, %s with missing parts, etc.
        # Simple regex for broken handlebars or printf
        # e.g. {{ name } (missing closing brace)
        # This is tricky without knowing the exact syntax.
        # Let's look for common patterns.
        
        # Unbalanced braces
        if text.count('{') != text.count('}'):
            return True
        if text.count('%') > 0 and not re.search(r'%[sfd@]', text): # suspicious single %
             # Not perfect, but MVP check
             pass
             
        return False
