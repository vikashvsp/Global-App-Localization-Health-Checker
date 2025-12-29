# Global App Localization Health Checker

**Detect gaps, score health, and fix app localization instantly.**

[![Apify](https://img.shields.io/badge/Apify-Actor-green)](https://apify.com)

This Actor visits your website, detects visible UI text, and uses **Lingo.dev** to identify:
- Missing translations (English fallback on non-English pages).
- Terminology inconsistencies.
- Broken placeholders.

It provides a **Localization Score** and outputs **GitHub-ready i18n JSON files** with suggested fixes.

---

## 🚀 Key Features

### 🔍 1. Automated Health Check
Crawls your site and scores each language based on coverage and quality.

### 🧠 2. AI-Powered Suggestions
Uses **Lingo.dev** to provide context-aware translations, not just literal swaps.

### 📦 3. Developer-Ready Exports
- **JSON**: Ready for `i18n` frameworks.
- **CSV**: for Project Managers.

## Usage
Input your website URL and target languages.
```json
{
  "url": "https://example.com",
  "languages": ["es", "fr"]
}
```
