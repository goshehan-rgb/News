import feedparser
import json
import os
from datetime import datetime
import google.generativeai as genai
import hashlib

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Your news sources - customize these!
NEWS_SOURCES = {
    "tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "ai": [
        "https://news.mit.edu/topic/mitartificial-intelligence-rss.xml",
        "https://venturebeat.com/category/ai/feed/",
    ],
    "science": [
        "https://www.nature.com/nature.rss",
        "https://www.sciencemag.org/rss/news_current.xml",
    ]
}
# Ensure the data directory exists
os.makedirs("data", exist_ok=True)
def fetch_news():
    articles = []
    for category, urls in NEWS_SOURCES.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    article = {
                        "id": hashlib.md5(entry.link.encode()).hexdigest(),
                        "title": entry.title,
                        "summary": entry.get("summary", "")[:500],
                        "url": entry.link,
                        "source": feed.feed.get("title", "Unknown"),
                        "published": entry.get("published", ""),
                        "category": category
                    }
                    articles.append(article)
            except Exception as e:
                print(f"Error with {url}: {e}")
    return articles

def analyze_with_gemini(article):
    prompt = f"""
    Analyze this {article['category']} article briefly:
    Title: {article['title']}
    Summary: {article['summary'][:300]}
    
    Return JSON only:
    {{
        "importance": (1-5, 5=must read),
        "summary": "one sentence summary",
        "why_read": "one sentence why this matters"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except:
        return {"importance": 3, "summary": article["summary"][:100], "why_read": "Interesting read"}

def generate_html(articles, analyzed):
    analyzed_dict = {a["id"]: a for a in analyzed}
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>My News Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            h1 {{ margin: 0; color: #1a73e8; }}
            .date {{ color: #666; margin-top: 5px; }}
            .section {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
            .section h2 {{ color: #1a73e8; margin-top: 0; }}
            .news-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
            .news-card {{ border: 1px solid #eee; border-radius: 8px; padding: 15px; }}
            .importance-high {{ border-left: 4px solid #d93025; }}
            .importance-medium {{ border-left: 4px solid #f9ab00; }}
            .source {{ color: #666; font-size: 0.85em; margin-top: 10px; }}
            .why-read {{ color: #1a73e8; font-style: italic; margin: 10px 0; }}
            a {{ color: #333; text-decoration: none; }}
            a:hover {{ color: #1a73e8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📰 My News Dashboard</h1>
                <div class="date">Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
            </header>
    """
    important = [a for a in articles if a["id"] in analyzed_dict and analyzed_dict[a["id"]].get("importance", 0) >= 4]
    if important:
        html += '<div class="section"><h2>⭐ Must Read</h2><div class="news-grid">'
        for article in important[:6]:
            analysis = analyzed_dict[article["id"]]
            html += f'''
                <div class="news-card importance-high">
                    <div><strong>{article["title"]}</strong></div>
                    <div class="why-read">💡 {analysis.get("why_read", "Important")}</div>
                    <div class="source">📰 {article["source"]}</div>
                </div>
            '''
        html += "</div></div>"
    
    for category in NEWS_SOURCES:
        cat_news = [a for a in articles if a["category"] == category]
        if cat_news:
            html += f'<div class="section"><h2>{category.title()}</h2><div class="news-grid">'
            for article in cat_news[:4]:
                analysis = analyzed_dict.get(article["id"], {})
                imp_class = "importance-high" if analysis.get("importance", 0) >= 4 else "importance-medium"
                html += f'''
                    <div class="news-card {imp_class}">
                        <div><strong><a href="{article["url"]}" target="_blank">{article["title"][:80]}...</a></strong></div>
                        <div>{analysis.get("summary", article["summary"][:100])}</div>
                        <div class="source">{article["source"][:20]}</div>
                    </div>
                '''
            html += "</div></div>"
    
    html += "</div></body></html>"
    
    with open("index.html", "w", encoding='utf-8') as f:
        f.write(html)
    print("✅ Dashboard generated!")

def main():
    print("📰 Fetching news...")
    articles = fetch_news()
    print(f"✅ Found {len(articles)} articles")
    print("🤖 Analyzing with Gemini...")
    analyzed = []
    for i, article in enumerate(articles[:15]):
        print(f"   Analyzing {i+1}/15: {article['title'][:30]}...")
        analysis = analyze_with_gemini(article)
        article.update(analysis)
        analyzed.append(article)
    generate_html(articles, analyzed) 
    with open(f"data/news_{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
        json.dump(analyzed, f, indent=2)

if __name__ == "__main__":
    main()