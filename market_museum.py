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
    return hk_time.weekday() == 6  # 6 = Sunday

def get_hk_time():
    return datetime.utcnow() + timedelta(hours=8)

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
    """Get broader news for weekly recap using more tickers."""
    news_items = []
    # Cast wider net for weekly
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
   - End with 5-8 relevant hashtags on a new line
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
        return result.get("recap", ""), result.get("image_prompt", ""), result.get("ig_caption", "")

    except Exception as e:
        print(f"⚠️ Daily story generation failed: {e}")
        recap = "Markets moved today with notable activity across major indices."
        image_prompt = f"A dramatic stock market scene, {art_style}, masterpiece, ultra detailed."
        ig_caption = "The market never sleeps. 📈\n#StockMarket #WallStreet #Investing"
        return recap, image_prompt, ig_caption

# ====================== GEMINI: WEEKLY STORY ======================
def generate_weekly_story(core_data, dynamic_data, news_items, art_style):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, weekly=True)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."

        # Calculate week date range
        hk_now = get_hk_time()
        week_start = (hk_now - timedelta(days=6)).strftime('%B %d')
        week_end = hk_now.strftime('%B %d, %Y')

        prompt = f"""You are a creative financial art director for a viral weekly market storytelling project.
This is the WEEKLY RECAP for the week of {week_start} - {week_end} (Hong Kong Time).

Your job:
1. Identify the 2-3 biggest themes or stories that defined this week in markets.
2. Write a punchy weekly market narrative (5-7 sentences, flowing prose, no bullet points).
   Capture the arc of the week — how did it start, what happened, how did it end?
3. Create a vivid, creative, exaggerated image description capturing the essence of this week.
   - Think of it as a "weekly movie poster" — bold, symbolic, dramatic.
   - Include real people, companies, or events that defined the week.
   - Be creative, funny, or dramatic. Make it shareable.
4. Write a punchy Instagram caption for the weekly recap:
   - Open with a strong "Week in Review" hook
   - 3-4 short witty sentences summarising the week
   - End with 6-10 relevant hashtags on a new line
   - Max 200 words total

Weekly Market Data (Mon-Fri performance):
{market_data_str}

This Week's Key Headlines:
{news_text}

Art Style: {art_style}

Return ONLY valid JSON, no markdown:
{{
  "recap": "5-7 sentence weekly market narrative.",
  "image_prompt": "Detailed weekly movie poster visual description with art style.",
  "ig_caption": "Weekly recap IG caption with hook + hashtags."
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result.get("recap", ""), result.get("image_prompt", ""), result.get("ig_caption", "")

    except Exception as e:
        print(f"⚠️ Weekly story generation failed: {e}")
        recap = "It was an eventful week on Wall Street with significant moves across major indices."
        image_prompt = f"A dramatic weekly stock market scene, {art_style}, masterpiece, ultra detailed."
        ig_caption = "Another week on Wall Street in the books. 📊\n#WeeklyRecap #StockMarket #WallStreet"
        return recap, image_prompt, ig_caption

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
        hk_time = get_hk_time()
        sunday = is_sunday_hk()
        mode = "📅 WEEKLY RECAP" if sunday else "📰 DAILY RECAP"
        print(f"[{hk_time.strftime('%Y-%m-%d %H:%M')} HKT] 🚀 Market Museum Started — {mode}")

        # 1. Core market data
        print("📈 Fetching core market data...")
        core_data = get_core_market_data(weekly=sunday)

        # 2. News
        print("📰 Fetching news...")
        news_items = get_weekly_news() if sunday else get_daily_news()
        print(f"  Got {len(news_items)} headlines")

        # 3. Extract tickers
        print("🔍 Extracting tickers from news...")
        extracted_tickers = extract_tickers_from_news(news_items)
        print(f"  Found {len(extracted_tickers)} companies in news")

        # 4. Dynamic stock data
        print("📊 Fetching dynamic stock data...")
        dynamic_data = get_dynamic_stock_data(extracted_tickers, weekly=sunday)

        # 5. Random art style
        art_style = get_random_style()
        print(f"🎨 Art style: {art_style[:60]}...")

        # 6. Generate story
        print("✍️ Generating story...")
        if sunday:
            recap, image_prompt, ig_caption = generate_weekly_story(
                core_data, dynamic_data, news_items, art_style
            )
        else:
            recap, image_prompt, ig_caption = generate_daily_story(
                core_data, dynamic_data, news_items, art_style
            )
        print(f"  Recap: {recap[:100]}...")
        print(f"  IG Caption: {ig_caption[:80]}...")

        # 7. Generate image
        image_path = await generate_image(image_prompt)
        if not image_path:
            print("❌ No image returned")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ No image generated today.")
            return

        # 8. Build Telegram caption
        market_data_str = format_market_data(core_data, dynamic_data, weekly=sunday)
        date_str = hk_time.strftime('%B %d, %Y')
        header = f"🗓 Weekly Recap • {date_str}" if sunday else f"🎨 Market Museum Daily • {date_str}"

        tg_caption = f"""{header}

{recap}

{market_data_str}

#MarketMuseum #StockMarket #WallStreet"""

        if len(tg_caption) > 1024:
            tg_caption = tg_caption[:1020] + "..."

        # 9. Send photo
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=open(image_path, 'rb'),
            caption=tg_caption
        )

        # 10. Send IG caption as separate message
        ig_label = "📱 *IG Caption (Weekly) — copy & paste ready:*" if sunday else "📱 *IG Caption — copy & paste ready:*"
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"{ig_label}\n\n{ig_caption}",
            parse_mode="Markdown"
        )

        print(f"✅ Success! {mode} sent to Telegram.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Error: {str(e)[:300]}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
