import os
import random
import json
from google import genai
from google.genai import types
from telegram import Bot
from datetime import datetime
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
    # Japanese Contemporary
    "in the style of Yoshitomo Nara, big-eyed curious figures, soft pastel with dark undertones",
    "in the style of Yusuke Hanai, clean lines, vibrant modern street art",
    "in the style of Nagaba Yuma, delicate emotional character illustration",
    "in the style of Takashi Murakami, superflat, vibrant pop art",
    "in the style of Yayoi Kusama, infinity dot patterns, bold repetitive motifs",
    # Inoue Takehiko 水墨
    "in the style of Inoue Takehiko, expressive sumi-e ink wash painting, bold brushstrokes, dramatic black ink on white, high contrast, fluid motion, zen minimalism",
    "Inoue Takehiko Vagabond manga style, loose sumi-e ink wash, gestural brushwork, monochrome with ink splatter, deeply emotional and raw",
    # JoJo
    "in the style of JoJo no Kimyou na Bouken by Araki Hirohiko, bold dramatic poses, heavy crosshatching, intense expressions, baroque ornamentation, surreal color gradients, fashion-forward character design",
    # Street Art
    "in the style of Banksy, bold stencil street art, stark black and white with one accent color, satirical and thought-provoking",
    "in the style of Van Gogh, swirling expressive impasto brushstrokes, vivid emotional color palette",
    # Western Classical Masters
    "in the style of Leonardo da Vinci, Renaissance sfumato technique, soft diffused light, detailed anatomical precision, warm golden tones, chiaroscuro",
    "in the style of Rembrandt, dramatic chiaroscuro, deep shadow and warm candlelight, rich oil painting texture, baroque emotional depth",
    "in the style of Johannes Vermeer, soft diffused natural light, intimate domestic atmosphere, pearl-like luminous quality, Dutch Golden Age",
    "in the style of Michelangelo, powerful muscular figures, Sistine Chapel grandeur, divine light, Renaissance fresco style",
    "in the style of Claude Monet, soft impressionist brushwork, dappled light, pastel water reflections, dreamy atmospheric perspective",
    "in the style of Gustav Klimt, Art Nouveau gold leaf patterns, ornate decorative motifs, sensual flowing figures, mosaic-like details",
    # Traditional Asian
    "classic ukiyo-e woodblock print style inspired by Hokusai, bold outlines, flat color areas, Mount Fuji grandeur",
    "traditional Chinese ink brush painting, elegant sparse composition, misty mountain landscape, Song Dynasty style",
]

def get_random_style():
    return random.choice(ART_STYLES)

# ====================== MARKET DATA ======================
CORE_TICKERS = {
    "S&P 500":   "^GSPC",
    "Nasdaq":    "^IXIC",
    "Dow Jones": "^DJI",
    "VIX":       "^VIX",
}

def fetch_ticker_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            last_close = hist['Close'].iloc[-1]
            change_pct = ((last_close - prev_close) / prev_close) * 100
            return {
                "price": round(last_close, 2),
                "change_pct": round(change_pct, 2),
            }
    except:
        pass
    return None

def get_core_market_data():
    results = {}
    for name, symbol in CORE_TICKERS.items():
        data = fetch_ticker_data(symbol)
        if data:
            results[name] = data
    return results

def extract_tickers_from_news(news_items):
    """Use Gemini to extract company names and tickers mentioned in news."""
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
        raw = response.text.strip()
        # Clean up in case Gemini adds markdown
        raw = raw.replace("```json", "").replace("```", "").strip()
        extracted = json.loads(raw)
        return extracted
    except Exception as e:
        print(f"⚠️ Ticker extraction failed: {e}")
        return []

def get_dynamic_stock_data(extracted_tickers):
    results = {}
    for item in extracted_tickers:
        name = item.get("name")
        symbol = item.get("ticker")
        if not name or not symbol:
            continue
        data = fetch_ticker_data(symbol)
        if data:
            results[name] = data
            print(f"  ✅ {name} ({symbol}): {data['change_pct']:+.2f}%")
        else:
            print(f"  ⚠️ Skipped {name} ({symbol})")
    return results

def format_market_data(core_data, dynamic_data):
    lines = []

    lines.append("📊 Major Indices:")
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

# ====================== NEWS SCRAPING ======================
def get_market_news():
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

# ====================== GEMINI: STORY + IMAGE PROMPT ======================
def generate_story_and_image_prompt(core_data, dynamic_data, news_items, art_style):
    try:
        market_data_str = format_market_data(core_data, dynamic_data)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."

        prompt = f"""You are a creative financial art director for a daily market storytelling project.

Your job:
1. Read today's market data and news headlines.
2. Identify the single most interesting, dramatic, funny, or important story of the day.
3. Write a SHORT punchy market recap (3-5 sentences, flowing prose, no bullet points).
4. Then create a vivid, creative, sometimes exaggerated image description that captures this story visually.
   - The image should be symbolic, funny, dramatic, or surprising — NOT a literal chart or graph.
   - Include real people or brand names if they are central to the story (e.g. Trump holding a Dell laptop, a crying trader, a bull stomping on a bear).
   - The mood should match the market: euphoric, panicked, boring, chaotic, triumphant, etc.
   - Be creative and bold. This image will go viral on social media.

Market Data:
{market_data_str}

News Headlines:
{news_text}

Art Style to use: {art_style}

Return ONLY valid JSON in this exact format, no markdown, no explanation:
{{
  "recap": "Your 3-5 sentence market recap here.",
  "image_prompt": "Your detailed visual image description here, incorporating the art style."
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result.get("recap", ""), result.get("image_prompt", "")

    except Exception as e:
        print(f"⚠️ Story generation failed: {e}")
        # Fallback
        recap = "Markets moved today with notable activity across major indices and key stocks."
        image_prompt = f"A dramatic stock market scene, {art_style}, masterpiece, ultra detailed."
        return recap, image_prompt

# ====================== GENERATE IMAGE ======================
async def generate_image(image_prompt):
    print(f"🎨 Image prompt: {image_prompt[:150]}...")

    full_prompt = f"""Create a stunning high-resolution vertical digital painting.
Edge-to-edge, no white borders, no padding, no frames, full bleed.
Vertical 3:4 portrait orientation.
{image_prompt}
Masterpiece, ultra detailed, sharp focus, rich saturated colors, professional composition, best quality."""

    response = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    image_path = "market_museum_today.jpg"
    for part in response.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(image_path, "JPEG", quality=95)
            print(f"✅ Image saved: {image.size}")
            return image_path

    return None

# ====================== MAIN ======================
async def main():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 🚀 Market Museum Started")

        # 1. Fetch core indices
        print("📈 Fetching core market data...")
        core_data = get_core_market_data()

        # 2. Fetch news
        print("📰 Fetching market news...")
        news_items = get_market_news()
        print(f"  Got {len(news_items)} headlines")

        # 3. Extract mentioned tickers from news
        print("🔍 Extracting tickers from news...")
        extracted_tickers = extract_tickers_from_news(news_items)
        print(f"  Found {len(extracted_tickers)} companies in news")

        # 4. Fetch dynamic stock data
        print("📊 Fetching dynamic stock data...")
        dynamic_data = get_dynamic_stock_data(extracted_tickers)

        # 5. Pick random art style
        art_style = get_random_style()
        print(f"🎨 Art style: {art_style[:60]}...")

        # 6. Generate story + image prompt via Gemini
        print("✍️ Generating story and image concept...")
        recap, image_prompt = generate_story_and_image_prompt(
            core_data, dynamic_data, news_items, art_style
        )
        print(f"  Recap: {recap[:100]}...")

        # 7. Generate image
        image_path = await generate_image(image_prompt)
        if not image_path:
            print("❌ No image returned")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ No image generated today.")
            return

        # 8. Build caption
        market_data_str = format_market_data(core_data, dynamic_data)
        date_str = datetime.now().strftime('%B %d, %Y')

        caption = f"""🎨 Market Museum Daily • {date_str}

{recap}

{market_data_str}

#MarketMuseum #StockMarket #WallStreet #USStocks"""

        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        # 9. Send to Telegram
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=open(image_path, 'rb'),
            caption=caption
        )
        print("✅ Success! Sent to Telegram.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Error: {str(e)[:300]}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
