from apify import Actor
import asyncio
from src.crawler import Crawler
from src.analyzer import Analyzer
from src.lingo import LingoClient
import pandas as pd
import json

async def main():
    async with Actor:
        Actor.log.info('Actor starting...')
        
        # Get input
        actor_input = await Actor.get_input() or {}
        source_type = actor_input.get('sourceType', 'website')
        url = actor_input.get('url')
        languages = actor_input.get('languages', ['es']) # Default to Spanish check if empty
        base_language = actor_input.get('baseLanguage', 'en')
        max_pages = actor_input.get('maxPages', 5)
        lingo_api_key = actor_input.get('lingoApiKey') # User provided key
        
        # MOCK MODE SAFETY: Default to MOCK if no key or for testing
        is_mock = False
        if not lingo_api_key:
             Actor.log.warning("No Lingo API Key provided. Running in MOCK mode.")
             is_mock = True
        
        # Initialize Components
        crawler = Crawler(start_url=url, max_pages=max_pages)
        analyzer = Analyzer(target_languages=languages, base_language=base_language)
        lingo_client = LingoClient(api_key=lingo_api_key, mock=is_mock)
        
        # 1. Crawl
        Actor.log.info(f"Crawling {url}...")
        crawled_data = await crawler.run()
        Actor.log.info(f"Crawled {len(crawled_data)} pages.")
        
        # 2. Analyze & Score
        all_issues = []
        localization_scores = {lang: 100 for lang in languages} # Start at 100
        
        # Global stats for scoring
        total_missing = 0
        total_fallback = 0
        total_mixed = 0
        total_broken = 0

        for page in crawled_data:
            analysis = analyzer.analyze_page(page)
            for issue in analysis['issues']:
                issue['url'] = page['url'] # Add context
                
                # Deduct points (Simplified scoring per issue type)
                # Apply to ALL target languages for now, as we don't know which one failed specifically 
                # unless we detected the language.
                # If we found "English fallback", that applies to ALL target langs that are NOT English.
                
                if issue['type'] == 'fallback_text': # 1x
                    total_fallback += 1
                elif issue['type'] == 'mixed_language': # 3x
                    total_mixed += 1
                elif issue['type'] == 'broken_placeholder': # 5x
                    total_broken += 1
                
                # Check for Missing Translation (using Lingo)
                # If it's a fallback, it IS a missing translation candidate
                if issue['type'] in ['fallback_text', 'mixed_language']:
                     # For each target language, suggest a fix
                     for lang in languages:
                        if lang == base_language: continue
                        
                        suggestion = await lingo_client.suggest_translation(
                            issue['text'], 
                            target_lang=lang, 
                            context=issue.get('context')
                        )
                        issue[f'suggestion_{lang}'] = suggestion
                        total_missing += 1 # Count this as a missing translation need
                
                all_issues.append(issue)

        # 3. Calculate Final Scores
        # Score = 100 - 2*missing - 1*fallback - 3*mixed - 5*broken
        # We'll calculate one global score per language or just one global score.
        # The prompt asked for "Localization Score { language: hi, score: 62 }"
        
        final_scores = []
        for lang in languages:
            if lang == base_language: continue
            
            # Simple formula application
            # Note: This simple formula might go below 0, so clamp it.
            score = 100 - (2 * total_missing) - (1 * total_fallback) - (3 * total_mixed) - (5 * total_broken)
            score = max(0, score)
            
            final_scores.append({
                "language": lang,
                "score": score,
                "issues": {
                    "missing": total_missing, # approximate
                    "fallbacks": total_fallback,
                    "mixedLanguage": total_mixed,
                    "brokenPlaceholders": total_broken
                }
            })

        # 4. Export
        # Save to Key-Value Store (visible in Apify Console)
        await Actor.push_data(final_scores) # The primary output
        
        # Detailed Report
        await Actor.set_value('DETAILED_REPORT', all_issues)
        
        # Generate i18n JSONs (GitHub-ready)
        # Structure: { lang: { key: translation } }
        i18n_export = {}
        for issue in all_issues:
            # We use the key from crawler if available, or text slug
            key = issue.get('key')
            if not key:
                 # Should have been set by analyzer passing through from crawler items
                 # But analyzer just passed 'issues'. Rethink data flow if needed.
                 # Ah, analyzer receives 'page_data' which has 'items' which has 'key'.
                 # But 'issues' are created new. We need to pass 'key' from item to issue in analyzer.
                 key = issue.get('text', '')[:20].strip().replace(' ', '_').lower()
            
            for lang in languages:
                if lang == base_language: continue
                suggestion_key = f'suggestion_{lang}'
                if suggestion_key in issue and issue[suggestion_key]:
                    if lang not in i18n_export: i18n_export[lang] = {}
                    i18n_export[lang][key] = issue[suggestion_key]
        
        # Save i18n JSONs
        for lang, translations in i18n_export.items():
            await Actor.set_value(f'i18n_{lang}.json', translations)
            Actor.log.info(f"Exported i18n_{lang}.json with {len(translations)} keys.")

        # Create CSV
        if all_issues:
            # Flatten for CSV
            csv_data = []
            for i in all_issues:
                row = {
                    'url': i.get('url'),
                    'type': i.get('type'),
                    'severity': i.get('severity'),
                    'text_found': i.get('text'),
                    'context': i.get('context'),
                    'detected_lang': i.get('details', '')
                }
                for lang in languages:
                    if lang == base_language: continue
                    row[f'suggestion_{lang}'] = i.get(f'suggestion_{lang}', '')
                csv_data.append(row)
                
            df = pd.DataFrame(csv_data)
            await Actor.set_value('localization_issues.csv', df.to_csv(index=False), content_type='text/csv')
        
        Actor.log.info("Analysis Complete.")
        Actor.log.info(f"Scores: {final_scores}")

if __name__ == '__main__':
    asyncio.run(main())
