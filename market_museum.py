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

# ====================== ART STYLES (ENHANCED) ======================
ART_STYLES = [
    # --- Japanese Contemporary ---
    (
        "Yoshitomo Nara style: lone big-eyed child figure with deceptively innocent face hiding dark emotion, "
        "flat matte acrylic paint, limited pastel palette with one jarring dark accent, "
        "raw naive brushwork, minimalist background, emotional tension beneath cute surface, "
        "NO gradients, NO realism, deliberately childlike yet unsettling"
    ),
    (
        "Yusuke Hanai style: bold graphic street poster, strong black outlines, "
        "flat areas of 3-4 saturated colors, vintage wear texture overlaid, "
        "athletic or urban figure in dynamic pose, retro Japanese streetwear aesthetic, "
        "screen-print look with slight misregistration, gritty urban energy"
    ),
    (
        "Nagaba Yuma style: delicate fine-line illustration, single emotional female figure, "
        "sparse elegant composition, soft muted watercolor washes, "
        "introspective melancholic mood, fashion-forward clothing detail, "
        "lots of white breathing space, poetic and quiet"
    ),
    (
        "Takashi Murakami superflat style: hyper-flat zero-perspective composition, "
        "explosive psychedelic color palette, manga-influenced characters mixed with fine art motifs, "
        "obsessive pattern repetition, flowers with smiley faces, "
        "high-gloss finish aesthetic, pop culture and traditional Japanese art colliding, "
        "zero shadow zero depth, pure 2D graphic impact"
    ),
    (
        "Yayoi Kusama style: entire canvas consumed by obsessive hand-painted polka dots and nets, "
        "infinity hallucination effect, bold contrasting colors in dot patterns, "
        "figure or object barely visible beneath dot obsession, "
        "raw repetitive mark-making, psychedelic and meditative simultaneously"
    ),

    # --- Inoue Takehiko Sumi-e ---
    (
        "Inoue Takehiko sumi-e masterpiece in the style of Vagabond manga: "
        "dramatic black sumi ink on raw white washi paper, "
        "visible bristle marks and ink bleed into paper grain, "
        "heavy ink pooling in deep shadows fading to ghost-light grey washes, "
        "lightning gestural brushstrokes conveying explosive motion and inner stillness, "
        "80 percent negative white space, zero color, "
        "NO digital smoothing, RAW traditional ink media texture, "
        "the kind of brushwork that takes 30 years to master"
    ),
    (
        "Inoue Takehiko real style ink painting: loose expressive sumi-e, "
        "monochrome ink wash with dramatic tonal range from jet black to pale silver grey, "
        "ink splatter and drip marks intentionally left, "
        "single powerful figure rendered in 5 bold strokes, "
        "zen emptiness surrounding the subject, "
        "rough uneven paper texture visible, deeply emotional and raw, "
        "museum-quality traditional Japanese ink painting"
    ),

    # --- Araki JoJo ---
    (
        "Araki Hirohiko JoJo's Bizarre Adventure style: "
        "impossibly dramatic contrapposto pose defying anatomy for maximum impact, "
        "heavy baroque cross-hatching and stippling for shadows, "
        "fashion illustration meets Italian Renaissance meets manga, "
        "intense screaming facial expression with detailed musculature, "
        "surreal color gradient background in magenta and teal, "
        "ornate decorative framing elements, "
        "over-the-top masculine energy with high fashion sensibility"
    ),

    # --- Street Art ---
    (
        "Banksy stencil street art: razor-sharp high-contrast stencil spray paint on rough concrete wall, "
        "stark black silhouette against white with ONE single bold accent color, "
        "subversive political message embedded in apparently simple image, "
        "photorealistic stencil technique, "
        "gritty urban texture of weathered wall visible through paint, "
        "wit and dark irony in every element, "
        "the kind of image that makes you stop and think"
    ),

    # --- Van Gogh ---
    (
        "Vincent van Gogh oil painting: thick impasto paint applied with palette knife and bristle brush, "
        "every inch of canvas covered in swirling directional brushstrokes, "
        "electric cobalt blue and cadmium yellow dominate, "
        "sky and background in hypnotic cyclone swirls, "
        "raw emotional intensity in every mark, "
        "visible paint texture you could reach out and touch, "
        "post-impressionist color theory pushed to breaking point"
    ),

    # --- Western Classical Masters ---
    (
        "Leonardo da Vinci Renaissance oil painting: "
        "sfumato technique with no hard edges, forms emerging from smoky atmospheric haze, "
        "warm amber and raw umber palette of Renaissance masters, "
        "anatomically perfect figures with psychological depth in their gaze, "
        "golden ratio composition, soft chiaroscuro modeling of form, "
        "the meditative quality of a painting that took 4 years to complete, "
        "craquelure texture of 500-year-old oil paint"
    ),
    (
        "Rembrandt van Rijn Dutch Golden Age oil painting: "
        "single dramatic shaft of warm candlelight piercing absolute darkness, "
        "rich impasto paint surface with decades of glazing, "
        "psychological intensity in illuminated face emerging from deep shadow, "
        "burnt sienna and raw umber with gold ochre light, "
        "baroque emotional depth, "
        "the lighting of a Dutch master who understood human suffering"
    ),
    (
        "Johannes Vermeer Dutch Golden Age oil painting: "
        "cool pearl-like northern light from single left window, "
        "incredibly precise photorealistic detail in fabric and surface texture, "
        "calm domestic intimacy frozen in perfect moment, "
        "lapis lazuli blue and warm yellow ochre color harmony, "
        "stillness and silence you can almost hear, "
        "the quality of a painting that rewards 30 minutes of quiet looking"
    ),
    (
        "Michelangelo Sistine Chapel fresco style: "
        "heroic muscular figures in twisting contrapposto poses, "
        "divine light from upper left casting dramatic shadows, "
        "Renaissance fresco color palette of terracotta, azure and gold, "
        "monumental scale and grandeur, "
        "figures straining with the weight of human destiny, "
        "the visual language of God reaching toward man"
    ),
    (
        "Claude Monet Impressionist oil painting: "
        "rapid broken brushstrokes capturing light not form, "
        "canvas surface alive with dabs and flecks of pure unmixed color, "
        "soft atmospheric haze dissolving hard edges, "
        "complementary color vibration of orange and blue, violet and yellow, "
        "the feeling of standing in a garden at 8am in summer light, "
        "painted from pure optical sensation"
    ),
    (
        "Gustav Klimt Art Nouveau oil and gold leaf painting: "
        "real gold leaf mosaic patterns consuming the background entirely, "
        "ornate Byzantine and Egyptian decorative motifs, "
        "figures emerging from abstract pattern like figures from wallpaper, "
        "rich jewel-tone palette of gold emerald sapphire and crimson, "
        "flat decorative pattern fighting with volumetric figure, "
        "erotic symbolism wrapped in opulent surface beauty"
    ),

    # --- Traditional Asian ---
    (
        "Katsushika Hokusai ukiyo-e woodblock print: "
        "bold confident outlines of hand-carved woodblock, "
        "flat areas of Prussian blue and vermillion with zero shading, "
        "dynamic diagonal composition suggesting violent natural force, "
        "Mount Fuji as eternal witness in background, "
        "decorative wave or wind pattern as central visual element, "
        "the graphic power of an image printed 10,000 times"
    ),
    (
        "Song Dynasty Chinese ink brush painting guohua style: "
        "sparse elegant brushwork leaving vast empty space as active element, "
        "mountain mist rendered in pale ink wash dissolving into white silk, "
        "three tonal values only: dark ink, mid wash, white ground, "
        "single gnarled pine or bamboo as focal point, "
        "the philosophy of emptiness made visible, "
        "painted with brushes made of rabbit hair on thousand-year-old technique"
    ),
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
    lines = caption.strip().split('\n')
    fixed_lines = []
    for line in lines:
        words = line.split()
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
    except Exception:
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
        prompt = (
            "From the following financial news headlines, extract all companies or assets mentioned.\n"
            "Return ONLY a valid JSON array of objects with 'name' and 'ticker' fields.\n"
            "Use real Yahoo Finance ticker symbols. If unsure of ticker, skip that company.\n"
            "Limit to the 10 most prominently mentioned companies.\n"
            "Do not include indices like S&P 500 or Nasdaq.\n"
            "Return only JSON, no explanation, no markdown.\n\n"
            f"Headlines:\n{news_text}\n\n"
            'Example output:\n[{"name": "Apple", "ticker": "AAPL"}, {"name": "Tesla", "ticker": "TSLA"}]'
        )
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
        sorted_stocks = sorted(
            dynamic_data.items(),
            key=lambda x: abs(x[1]['change_pct']),
            reverse=True
        )
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
        prompt = (
            "You are a creative financial art director for a viral daily market storytelling project.\n"
            f"Today is {get_hk_time().strftime('%A, %B %d, %Y')} (Hong Kong Time). This is a DAILY recap.\n\n"
            "Your job:\n"
            "1. Identify the single most interesting, dramatic, funny, or important story of the day.\n"
            "2. Write a SHORT punchy market recap (3-5 sentences, flowing prose, no bullet points).\n"
            "3. Create a vivid, creative, exaggerated image description capturing this story visually.\n"
            "   - Symbolic, funny, dramatic, or surprising. NOT a literal chart or graph.\n"
            "   - Include real people or brands if central to the story.\n"
            "   - Mood matches the market: euphoric, panicked, boring, chaotic, triumphant, absurd.\n"
            "   - Bold and creative. This image should stop people scrolling on Instagram.\n"
            "   - The image MUST be executed faithfully in the specified art style. No shortcuts.\n"
            "4. Write a punchy Instagram caption:\n"
            "   - Strong hook line at the start\n"
            "   - 2-3 short witty sentences\n"
            "   - End with 5-8 hashtags on a new line, EVERY single hashtag MUST start with the # symbol\n"
            "   - Max 150 words total\n\n"
            f"Market Data:\n{market_data_str}\n\n"
            f"News Headlines:\n{news_text}\n\n"
            f"Art Style to execute with full technical commitment:\n{art_style}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            "{\n"
            '  "recap": "3-5 sentence daily market recap.",\n'
            '  "image_prompt": "Detailed visual image description with full art style technical execution.",\n'
            '  "ig_caption": "Punchy IG caption with hook + hashtags."\n'
            "}"
        )
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
        image_prompt = f"A dramatic stock market scene. {art_style}. Masterpiece, ultra detailed."
        ig_caption = "The market never sleeps. 📈\n#StockMarket #WallStreet #Investing"
        return recap, image_prompt, ig_caption

# ====================== GEMINI: WEEKLY STORY ======================
def generate_weekly_story(core_data, dynamic_data, news_items, art_style):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, weekly=True)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        hk_now = get_hk_time()
        week_start = (hk_now - timedelta(days=6)).strftime('%B %d')
        week_end = hk_now.strftime('%B %d, %Y')
        prompt = (
            "You are a creative financial art director for a viral weekly market storytelling project.\n"
            f"This is the WEEKLY RECAP for the week of {week_start} - {week_end} (Hong Kong Time).\n\n"
            "Your job:\n"
            "1. Identify the 2-3 biggest themes or stories that defined this week in markets.\n"
            "2. Write a punchy weekly market narrative (5-7 sentences, flowing prose, no bullet points).\n"
            "   Capture the arc of the week: how did it start, what happened, how did it end?\n"
            "3. Create a vivid, creative, exaggerated image description capturing the essence of this week.\n"
            "   - Think of it as a weekly movie poster: bold, symbolic, dramatic.\n"
            "   - Include real people, companies, or events that defined the week.\n"
            "   - Be creative, funny, or dramatic. Make it shareable.\n"
            "   - The image MUST be executed faithfully in the specified art style. No shortcuts.\n"
            "4. Write a punchy Instagram caption for the weekly recap:\n"
            "   - Open with a strong Week in Review hook\n"
            "   - 3-4 short witty sentences summarising the week\n"
            "   - End with 6-10 hashtags on a new line, EVERY single hashtag MUST start with the # symbol\n"
            "   - Max 200 words total\n\n"
            f"Weekly Market Data (Mon-Fri performance):\n{market_data_str}\n\n"
            f"This Week's Key Headlines:\n{news_text}\n\n"
            f"Art Style to execute with full technical commitment:\n{art_style}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            "{\n"
            '  "recap": "5-7 sentence weekly market narrative.",\n'
            '  "image_prompt": "Detailed weekly movie poster visual description with full art style technical execution.",\n'
            '  "ig_caption": "Weekly recap IG caption with hook + hashtags."\n'
            "}"
        )
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
        image_prompt = f"A dramatic weekly stock market scene. {art_style}. Masterpiece, ultra detailed."
        ig_caption = "Another week on Wall Street in the books. 📊\n#WeeklyRecap #StockMarket #WallStreet"
        return recap, image_prompt, ig_caption

# ====================== GENERATE IMAGE ======================
async def generate_image(image_prompt):
    print(f"🎨 Image prompt: {image_prompt[:150]}...")
    full_prompt = (
        "Create a stunning high-resolution vertical digital painting.\n"
        "Edge-to-edge, no white borders, no padding, no frames, full bleed.\n"
        "Vertical 3:4 portrait orientation.\n\n"
        "CRITICAL: Execute the art style with absolute technical faithfulness. "
        "Do NOT default to generic cartoon or digital illustration. "
        "Commit fully to the specific medium, technique, and aesthetic described. "
        "If the style calls for ink on paper, show ink on paper. "
        "If it calls for impasto oil paint, show thick textured oil paint. "
        "If it calls for woodblock print, show the grain and ink of a woodblock print.\n\n"
        f"{image_prompt}\n\n"
        "Masterpiece quality. Ultra detailed. Professional museum-worthy execution."
    )
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
        print(f"🎨 Art style selected: {art_style[:80]}...")

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

        tg_caption = (
            f"{header}\n\n"
            f"{recap}\n\n"
            f"{market_data_str}\n\n"
            "#MarketMuseum #StockMarket #WallStreet"
        )
        if len(tg_caption) > 1024:
            tg_caption = tg_caption[:1020] + "..."

        # 9. Send photo
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=open(image_path, 'rb'),
            caption=tg_caption
        )

        # 10. Fix hashtags and send IG caption
        ig_caption = fix_hashtags(ig_caption)
        ig_label = (
            "📱 *IG Caption (Weekly) — copy & paste ready:*"
            if sunday else
            "📱 *IG Caption — copy & paste ready:*"
        )
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
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
