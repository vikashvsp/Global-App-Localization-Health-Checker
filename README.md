# 🌍 Global App Localization Health Checker

![Apify](https://img.shields.io/badge/Platform-Apify-9B51E0) ![Python](https://img.shields.io/badge/Language-Python-3776AB) ![Lingo.dev](https://img.shields.io/badge/Powered%20By-Lingo.dev-FF4F00) ![License](https://img.shields.io/badge/License-MIT-green)

> **Stop losing global users to bad translations.** 🛑  
> Automatically crawl, analyze, and score your web app's localization health with AI.

---

## 🚀 What is this?

This is an **Apify Actor** that acts as your automated QA engineer for internationalization (i18n). It crawls your website, detects every piece of text, and uses the power of **Lingo.dev** to verify if your content is truly localized or if you're serving "English fallbacks" to your Spanish users.

### ✨ Key Features

*   **🕵️‍♂️ Smart Crawling**: Navigates your site automatically (configurable depth).
*   **🧠 AI Verification**: Uses [Lingo.dev](https://www.lingo.dev/) to distinguish between intended English terms (like brand names) and actual missing translations.
*   **⚡ Fast Batch Analysis**: Processes hundreds of text items in parallel using intelligent batching.
*   **📊 Localization Score**: Gives you a health score (0-100) for each language.
*   **📝 Actionable Reports**:
    *   **HTML Dashboard**: Visual report with red/green indicators.
    *   **JSON/CSV Exports**: Ready for your developers to fix.
    *   **i18n JSON Generation**: Auto-generates the missing translation files for you!

---

## 🛠️ How it Works

1.  **Crawl**: The actor starts at your entry URL and visits `maxPages`.
2.  **Extract**: It scrapes visible text from buttons, headings, labels, and paragraphs.
3.  **Analyze**:
    *   Detects the language of each text block.
    *   Identifies **Fallback Text** (English on a non-English page).
    *   Identifies **Mixed Language** content.
    *   Checks for **Broken Placeholders** (e.g., `Hello {{user}}`).
4.  **Verify & Suggest**: Calls the Lingo.dev API to confirm issues and **generate accurate translation suggestions**.
5.  **Report**: Outputs a detailed health score and artifacts.

---

## 📦 Output Example

You get a clean **HTML Report** in the Apify Key-Value store:

| Type | Found Text | AI Suggestion |
| :--- | :--- | :--- |
| <span style="background:#fff3cd;padding:2px 5px;border-radius:3px">Fallback</span> | `Subscribe Now` | `Jetzt abonnieren` |
| <span style="background:#f8d7da;padding:2px 5px;border-radius:3px">Mixed</span> | `Welcome to my website` | `Bienvenido a mi sitio web` |

---

## 🏃‍♂️ Running on Apify

1.  Go to the [Apify Console](https://console.apify.com/).
2.  Select this Actor.
3.  **Input Configuration**:
    *   `url`: The starting URL of your app.
    *   `languages`: List of target languages (e.g., `['es', 'fr', 'de']`).
    *   `lingoApiKey`: Your API key from Lingo.dev.
4.  **Start** the run! 🏁

---

## 💻 Local Development

Want to run it locally?

```bash
# 1. Clone the repo
git clone https://github.com/vikashvsp/Global-App-Localization-Health-Checker.git
cd Global-App-Localization-Health-Checker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create an INPUT.json in storage/key_value_stores/default/
# (See .actor/input_schema.json for format)

# 4. Run it
python -m src.main
```

## 🤝 Contributing

Found a bug? Want to add support for Next.js i18n routing?
PRs are welcome! Let's make the web truly global. 🌐

---

*Built with ❤️ using [Apify](https://apify.com) & [Lingo.dev](https://lingo.dev)*
