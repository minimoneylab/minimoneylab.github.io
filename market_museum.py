import os
import random
import json
from google import genai
from google.genai import types
from telegram import Bot
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import asyncio
import yfinance as yf

# ====================== CONFIG ======================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# ====================== ART STYLES ======================
ART_STYLES = [
    "in the style of Yoshitomo Nara, big-eyed curious figures, soft pastel with dark undertones",
    "in the style of Yusuke Hanai, clean lines, vibrant modern street art",
    "in the style of Nagaba Yuma, delicate emotional character illustration",
    "in the style of Takashi Murakami, superflat, vibrant pop art",
    "in the style of Yayoi Kusama, infinity dot patterns, bold repetitive motifs",
    "in the style of Inoue Takehiko, expressive sumi-e ink wash painting, bold brushstrokes, dramatic black ink on white, high contrast, fluid motion, zen minimalism",
    "Inoue Takehiko Vagabond manga style, loose sumi-e ink wash, gestural brushwork, monochrome with ink splatter, deeply emotional and raw",
    "in the style of JoJo no Kimyou na Bouken by Araki Hirohiko, bold dramatic poses, heavy crosshatching, intense expressions, baroque ornamentation, surreal color gradients, fashion-forward character design",
    "in the style of Banksy, bold stencil street art, stark black and white with one accent color, satirical and thought-provoking",
    "in the style of Van Gogh, swirling expressive impasto brushstrokes, vivid emotional color palette",
    "in the style of Leonardo da Vinci, Renaissance sfumato technique, soft diffused light, detailed anatomical precision, warm golden tones, chiaroscuro",
    "in the style of Rembrandt, dramatic chiaroscuro, deep shadow and warm candlelight, rich oil painting texture, baroque emotional depth",
    "in the style of Johannes Vermeer, soft diffused natural light, intimate domestic atmosphere, pearl-like luminous quality, Dutch Golden Age",
    "in the style of Michelangelo, powerful muscular figures, Sistine Chapel grandeur, divine light, Renaissance fresco style",
    "in the style of Claude Monet, soft impressionist brushwork, dappled light, pastel water reflections, dreamy atmospheric perspective",
    "in the style of Gustav Klimt, Art Nouveau gold leaf patterns, ornate decorative motifs, sensual flowing figures, mosaic-like details",
    "classic ukiyo-e woodblock print style inspired by Hokusai, bold outlines, flat color areas, Mount Fuji grandeur",
    "traditional Chinese ink brush painting, elegant sparse composition, misty mountain landscape, Song Dynasty style",
]

def get_random_style():
    return random.choice(ART_STYLES)

# ====================== HELPERS ======================
def is_sunday_hk():
    hk_time = datetime.utcnow() + timedelta(hours=8)
    return hk_time.weekday() == 6

def get_hk_time():
    return datetime.utcnow() + timedelta(hours=8)

def fix_hashtags(caption):
    """Auto-fix missing # symbols in hashtag lines."""
    lines = caption.strip().split('\n')
    fixed_lines = []
    for line in lines:
        words = line.split()
        # Check if this line contains any hashtags at all
        has_hashtag = any(w.startswith('#') for w in words)
        if not has_hashtag:
            fixed_lines.append(line)
            continue
        fixed_words = []
        for word in words:
            clean = word.strip('.,!?')
            if (
                len(clean) > 1
                and not clean.startswith('#')
                and not clean.startswith('@')
                and clean[0].isupper()
                and clean.isalnum()
            ):
                fixed_words.append('#' + word)
            else:
                fixed_words.append(word)
        fixed_lines.append(' '.join(fixed_words))
    return '\n'.join(fixed_lines)

# ====================== MARKET DATA ======================
CORE_TICKERS = {
    "S&P 500":   "^GSPC",
    "Nasdaq":    "^IXIC",
    "Dow Jones": "^DJI",
    "VIX":       "^VIX",
}

def fetch_ticker_data(symbol, period="2d"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[0]
            last_close = hist['Close'].iloc[-1]
            change_pct = ((last_close - prev_close) / prev_close) * 100
            return {
                "price": round(last_close, 2),
                "change_pct": round(change_pct, 2),
            }
    except:
        pass
    return None

def get_core_market_data(weekly=False):
    period = "5d" if weekly else "2d"
    results = {}
    for name, symbol in CORE_TICKERS.items():
        data = fetch_ticker_data(symbol, period=period)
        if data:
            results[name] = data
    return results

def extract_tickers_from_news(news_items):
    try:
        news_text = "\n".join(f"- {n}" for n in news_items)
        prompt = f"""From the following financial news headlines, extract all companies or assets mentioned.
Return ONLY a valid JSON array of objects with "name" and "ticker" fields.
Use real Yahoo Finance ticker symbols. If unsure of ticker, skip that company.
Limit to the 10 most prominently mentioned companies.
Do not include indices like S&P 500 or Nasdaq.
Return only JSON, no explanation, no markdown.

Headlines:
{news_text}

Example output:
[{{"name": "Apple", "ticker": "AAPL"}}, {{"name": "Tesla", "ticker": "TSLA"}}]"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️ Ticker extraction failed: {e}")
        return []

def get_dynamic_stock_data(extracted_tickers, weekly=False):
    period = "5d" if weekly else "2d"
    results = {}
    for item in extracted_tickers:
        name = item.get("name")
        symbol = item.get("ticker")
        if not name or not symbol:
            continue
        data = fetch_ticker_data(symbol, period=period)
        if data:
            results[name] = data
            print(f"  ✅ {name} ({symbol}): {data['change_pct']:+.2f}%")
        else:
            print(f"  ⚠️ Skipped {name} ({symbol})")
    return results

def format_market_data(core_data, dynamic_data, weekly=False):
    label = "Weekly Change" if weekly else "Daily Change"
    lines = []
    lines.append(f"📊 Major Indices ({label}):")
    for name, d in core_data.items():
        arrow = "▲" if d['change_pct'] > 0 else "▼"
        lines.append(f"  {arrow} {name}: {d['price']:,}  ({d['change_pct']:+.2f}%)")

    if dynamic_data:
        lines.append("")
        lines.append("🏢 Stocks In The News:")
        sorted_stocks = sorted(dynamic_data.items(), key=lambda x: abs(x[1]['change_pct']), reverse=True)
        for name, d in sorted_stocks:
            arrow = "▲" if d['change_pct'] > 0 else "▼"
            lines.append(f"  {arrow} {name}: ${d['price']:,}  ({d['change_pct']:+.2f}%)")

    return "\n".join(lines)

# ====================== NEWS ======================
def get_daily_news():
    news_items = []
    watch = ["^GSPC", "^IXIC", "NVDA", "AAPL", "MSFT", "TSLA", "META", "AMZN", "GOOGL"]
    seen_titles = set()

    for symbol in watch:
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            if news:
                for item in news[:4]:
                    title = item.get('content', {}).get('title', '')
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        news_items.append(title)
        except Exception as e:
            print(f"⚠️ News fetch failed for {symbol}: {e}")
        if len(news_items) >= 20:
            break

    return news_items[:20]

def get_weekly_news():
    news_items = []
    watch = [
        "^GSPC", "^IXIC", "^DJI",
        "NVDA", "AAPL", "MSFT", "TSLA", "META", "AMZN", "GOOGL",
        "JPM", "GS", "BRK-B", "IBIT", "AMD", "NFLX", "DIS"
    ]
    seen_titles = set()

    for symbol in watch:
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            if news:
                for item in news[:5]:
                    title = item.get('content', {}).get('title', '')
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        news_items.append(title)
        except Exception as e:
            print(f"⚠️ News fetch failed for {symbol}: {e}")
        if len(news_items) >= 30:
            break

    return news_items[:30]

# ====================== GEMINI: DAILY STORY ======================
def generate_daily_story(core_data, dynamic_data, news_items, art_style):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, weekly=False)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."

        prompt = f"""You are a creative financial art director for a viral daily market storytelling project.
Today is {get_hk_time().strftime('%A, %B %d, %Y')} (Hong Kong Time). This is a DAILY recap.

Your job:
1. Identify the single most interesting, dramatic, funny, or important story of the day.
2. Write a SHORT punchy market recap (3-5 sentences, flowing prose, no bullet points).
3. Create a vivid, creative, exaggerated image description capturing this story visually.
   - Symbolic, funny, dramatic, or surprising. NOT a literal chart or graph.
   - Include real people or brands if central to the story.
   - Mood matches the market: euphoric, panicked, boring, chaotic, triumphant, absurd.
   - Bold and creative. This image should stop people scrolling on Instagram.
4. Write a punchy Instagram caption:
   - Strong hook line at the start
   - 2-3 short witty sentences
   - End with 5-8 hashtags on a new line, EVERY hashtag MUST start with #
   - Max 150 words total

Market Data:
{market_data_str}

News Headlines:
{news_text}

Art Style: {art_style}

Return ONLY valid JSON, no markdown:
{{
  "recap": "3-5 sentence daily market recap.",
  "image_prompt": "Detailed visual image description with art style.",
  "ig_caption": "Punchy IG caption with hook + hashtags."
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result.get("recap", ""), result.get("im
