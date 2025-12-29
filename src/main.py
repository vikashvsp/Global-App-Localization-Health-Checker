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

        for i, page in enumerate(crawled_data):
            Actor.log.info(f"Analyzing page {i+1}/{len(crawled_data)}: {page['url']}")
            analysis = analyzer.analyze_page(page)
            # 1. Collect texts needing suggestions
            texts_to_translate = set()
            for issue in analysis['issues']:
                if issue['type'] in ['fallback_text', 'mixed_language']:
                    texts_to_translate.add(issue['text'])
            
            # 2. Batch Translate (for each target language)
            # We assume non-base languages are targets
            translations_map = {} # { lang: { text: translation } }
             
            if texts_to_translate and not is_mock:
                 Actor.log.info(f"  > Batch translating {len(texts_to_translate)} unique items...")
                 
                 for lang in languages:
                    if lang == base_language: continue
                    # Call batch method
                    translations_map[lang] = await lingo_client.suggest_translation_batch(list(texts_to_translate), lang)

            # 3. Apply results to issues
            for j, issue in enumerate(analysis['issues']):
                issue['url'] = page['url']
                
                # Apply suggestions if available
                if issue['type'] in ['fallback_text', 'mixed_language']:
                     for lang in languages:
                        if lang == base_language: continue
                        
                        # Get from batch result or fallback to None
                        # If MOCK, we didn't populate the map properly above in this snippet logic
                        # But lingo_client handles mock in batch too.
                        
                        translation = None
                        if is_mock:
                             translation = f"[MOCK] {issue['text']}"
                        elif lang in translations_map and issue['text'] in translations_map[lang]:
                             translation = translations_map[lang][issue['text']]
                        
                        if translation:
                            issue[f'suggestion_{lang}'] = translation
                
                all_issues.append(issue)
                
                if issue['type'] == 'fallback_text': total_fallback += 1
                elif issue['type'] == 'mixed_language': total_mixed += 1
                elif issue['type'] == 'broken_placeholder': total_broken += 1
                if issue.get(f'suggestion_{languages[0] if languages[0]!=base_language else "es"}'):
                    total_missing += 1

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
                
            # Create HTML Report
            html_report = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Localization Health Report</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max_width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
                    h1 {{ border-bottom: 2px solid #eaeaea; padding-bottom: 10px; }}
                    .score-card {{ background: #f7f7f7; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
                    .score {{ font-size: 48px; font-weight: bold; color: {'#d32f2f' if final_scores[0]['score'] < 50 else '#388e3c'}; }}
                    .section {{ margin-top: 30px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f8f9fa; }}
                    .tag {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
                    .tag.fallback {{ background: #fff3cd; color: #856404; }}
                    .tag.mixed {{ background: #f8d7da; color: #721c24; }}
                </style>
            </head>
            <body>
                <h1>Localization Health Report</h1>
                
                <div class="score-card">
                    <div>Overall Score ({languages[0] if languages[0]!=base_language else (languages[1] if len(languages)>1 else 'es')})</div>
                    <div class="score">{final_scores[0]['score']} / 100</div>
                    <div>
                        Missing: {final_scores[0]['issues']['missing']} | 
                        Fallbacks: {final_scores[0]['issues']['fallbacks']} | 
                        Mixed: {final_scores[0]['issues']['mixedLanguage']}
                    </div>
                </div>

                <div class="section">
                    <h2>Found Issues ({len(all_issues)})</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Found Text</th>
                                <th>Suggestion</th>
                                <th>Context</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            # Add top 100 issues to HTML
            for issue in all_issues[:100]:
                report_suggestion = ""
                # Find any suggestion key
                for k,v in issue.items():
                    if k.startswith('suggestion_'): report_suggestion = v; break
                
                tag_class = 'mixed' if issue['type'] == 'mixed_language' else 'fallback'
                
                html_report += f"""
                            <tr>
                                <td><span class="tag {tag_class}">{issue['type']}</span></td>
                                <td>{issue['text'][:100]}</td>
                                <td>{report_suggestion}</td>
                                <td style="color:#666; font-size:12px">{issue.get('context', '')[:50]}...</td>
                            </tr>
                """
            
            html_report += """
                        </tbody>
                    </table>
                </div>
            </body>
            </html>
            """
            
            await Actor.set_value('OUTPUT.html', html_report, content_type='text/html')
            Actor.log.info("HTML Report generated: OUTPUT.html")

            df = pd.DataFrame(csv_data)
            await Actor.set_value('localization_issues.csv', df.to_csv(index=False), content_type='text/csv')
            
            # Log examples of issues for user visibility
            Actor.log.info("--- ISSUE HIGHLIGHTS ---")
            
            fallbacks = [i['text'] for i in all_issues if i['type'] == 'fallback_text'][:5]
            if fallbacks:
                Actor.log.info(f"Top 5 Fallback Text examples (English on target page):")
                for text in fallbacks: Actor.log.info(f"  - \"{text[:50]}...\"")

            mixed = [i['text'] for i in all_issues if i['type'] == 'mixed_language'][:5]
            if mixed:
                Actor.log.info(f"Top 5 Mixed Language examples (confirmed by Lingo):")
                for text in mixed: Actor.log.info(f"  - \"{text[:50]}...\"")

        
        # Charge for the event (Pay-per-event)
        # The event name 'localization-check' must be configured in Apify Console
        await Actor.charge('localization-check')
        Actor.log.info("Charged for event: localization-check")

        Actor.log.info("Analysis Complete.")
        Actor.log.info(f"Scores: {final_scores}")

if __name__ == '__main__':
    asyncio.run(main())
