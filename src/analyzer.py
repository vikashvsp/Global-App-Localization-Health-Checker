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

            # 2. Mixed Language / Fallback Detection
            
            # A. Confident Mismatch (Long text, lang detected, mismatch)
            if len(text) > 15 and item_lang and item_lang != current_page_lang:
                 if item_lang == 'en' and current_page_lang != 'en':
                     issues.append({
                        'type': 'fallback_text',
                        'text': text,
                        'key': key,
                        'severity': 'medium',
                        'context': item['context']
                     })
                 else:
                     issues.append({
                        'type': 'mixed_language',
                        'text': text,
                        'key': key,
                        'severity': 'medium',
                        'context': item['context'],
                        'details': f'Detected {item_lang} on {current_page_lang} page'
                     })
            
            # B. Suspected Mixed (Short text, UI elements, flaky detection)
            # If text is short (< 15) AND we are on a non-English page
            # We suspect it might be English if it's not explicitly matching current lang
            elif len(text) <= 15 and len(text) > 3 and current_page_lang != 'en':
                # We flag this for verification.
                # Optimization: If langdetect says it matches page lang, we trust it?
                # langdetect is flaky on short text. "Login" -> "it". 
                # So we should verify EVERYTHING short unless we are very sure.
                # Let's verify anything short (>3 chars) on non-English pages.
                
                 issues.append({
                    'type': 'suspected_mixed',
                    'text': text,
                    'key': key,
                    'severity': 'low',
                    'context': item['context']
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
