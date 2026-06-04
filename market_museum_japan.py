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

# ====================== JAPAN ART STYLES ======================
ART_STYLES = [

    # --- 浮世繪 Ukiyo-e ---
    (
        "Katsushika Hokusai ukiyo-e woodblock print masterpiece: "
        "hand-carved woodblock outlines — confident, slightly irregular, never digital-smooth — "
        "flat Prussian blue and vermillion with zero shading or gradients, "
        "bold diagonal composition suggesting violent natural force like a crashing wave or storm, "
        "Mount Fuji or a torii gate visible as a distant symbol of permanence, "
        "decorative wave or wind pattern as central visual element with foam tips like grasping claws, "
        "the graphic power of an image printed ten thousand times on washi paper, "
        "visible paper grain texture, traditional bokashi gradation in sky only, "
        "NO digital effects, NO photography, pure woodblock print aesthetic"
    ),
    (
        "Utagawa Hiroshige ukiyo-e woodblock print: "
        "Tokaido road series atmospheric travel scene, "
        "diagonal rain rendered as parallel fine lines across the entire composition, "
        "misty landscape dissolving at edges using bokashi gradation technique, "
        "figures bent against weather in traditional travel clothing, "
        "deep atmospheric perspective using pale ink wash and color fading, "
        "warm amber lantern light against cool blue rain, "
        "traditional Japanese seasonal beauty — wabi-sabi impermanence, "
        "flat color areas with delicate hand-carved detail lines, "
        "the melancholy poetry of journeys and changing weather"
    ),

    # --- Manga: Inoue Takehiko ---
    (
        "Inoue Takehiko sumi-e manga masterpiece in the style of Vagabond: "
        "explosive gestural sumi ink brushstrokes on raw washi paper texture, "
        "dramatic tonal range from jet black pooling ink to ghost-pale grey wash, "
        "visible bristle marks, ink bleed and splatter intentionally left as part of the art, "
        "single powerful figure rendered in five bold decisive strokes, "
        "80 percent negative white space — emptiness is the subject, "
        "lightning-fast mark-making conveying both explosive motion and zen inner stillness simultaneously, "
        "NO color, NO digital smoothing, RAW traditional ink on paper, "
        "the kind of brushwork that requires thirty years to master, "
        "monochrome only — jet black, mid grey, pale silver, white"
    ),

    # --- Manga: Araki / JoJo ---
    (
        "Araki Hirohiko JoJo's Bizarre Adventure manga art style: "
        "impossibly dramatic contrapposto pose defying human anatomy entirely for maximum visual impact, "
        "heavy baroque cross-hatching and fine stippling in shadow areas, "
        "fashion illustration meets Italian Renaissance painting meets shounen manga, "
        "intense screaming facial expression with highly detailed musculature, "
        "fingers splayed wide, fabric rippling, hair defying gravity, "
        "surreal gradient background shifting from deep magenta to electric teal, "
        "ornate decorative framing elements — stars, geometric patterns, speed lines, "
        "over-the-top masculine energy wrapped in high fashion sensibility, "
        "bold ZA WARUDO energy — time itself feels frozen in this image"
    ),

    # --- Manga: Demon Slayer / 鬼滅の刃 ---
    (
        "Koyoharu Gotoge Demon Slayer Kimetsu no Yaiba manga art style: "
        "bold geometric wisteria and checked patterns (ichimatsu, asanoha) covering clothing and backgrounds, "
        "dramatic action poses mid-combat with sword trails and elemental breath technique effects, "
        "Total Concentration Breathing rendered as swirling elemental energy — fire, water, thunder, wind, "
        "highly expressive large eyes with detailed iris reflections, "
        "washi paper texture visible beneath ink lines, "
        "traditional Japanese textile patterns used as compositional elements, "
        "rich jewel-tone color palette: crimson, deep indigo, gold, forest green, "
        "emotional intensity — tears and determination simultaneously, "
        "tears sparkling like crystals, demon blood rendered in dramatic black ink splatter"
    ),

    # --- Manga: Naruto / 火影 ---
    (
        "Masashi Kishimoto Naruto manga art style: "
        "extreme dynamic action pose with chakra energy exploding outward from the figure, "
        "speed lines radiating from central figure creating explosive kinetic energy, "
        "Rasengan or Chidori energy ball rendered as swirling blue-white electrical plasma, "
        "bold thick black outlines with precise detail in facial expressions — determination and intensity, "
        "headband forehead protector with village symbol rendered with care, "
        "dramatic perspective foreshortening — fist or jutsu hand seal rushing toward viewer, "
        "shadow clone jutsu duplication effect creating multiple overlapping silhouettes, "
        "orange and blue color palette with electric white energy highlights, "
        "the raw energy of someone who never gives up — BELIEVE IT"
    ),

    # --- Manga: Dragon Ball / 龍珠 ---
    (
        "Akira Toriyama Dragon Ball manga art style: "
        "clean confident ink lines with precise weight variation — thick outlines, thin interior detail lines, "
        "Super Saiyan transformation with electric golden aura crackling around the entire figure, "
        "extreme power-up pose: legs planted wide, muscles bulging, screaming skyward, "
        "energy ki aura rendered as bold radiating light beams and crackling electricity, "
        "perfectly balanced figure design — Toriyama's iconic character proportions, "
        "dramatic sky background — storm clouds parting, lightning, distant mountains, "
        "bold primary color palette: gold, orange, blue sky, "
        "the visual grammar of pure unrestrained power — Kamehameha wave charging, "
        "clean and readable even at small size — the master of clear action storytelling"
    ),

    # --- Manga: Doraemon ---
    (
        "Fujiko F. Fujio Doraemon manga art style: "
        "perfectly rounded smooth forms — circles and gentle curves, zero sharp edges, "
        "clean simple ink outlines with consistent weight — the classic clear shounen children's style, "
        "playful gadget from the 4D pocket featured prominently — hovering, glowing, magical, "
        "warm gentle humor in facial expressions — wide innocent eyes, open mouths of surprise, "
        "classic blue tanuki robot cat with round face, white belly, red pouch, "
        "simple background suggesting everyday Japanese school or home life, "
        "primary color palette: blue, red, yellow, white — clear and joyful, "
        "the art style that defined childhood imagination for generations across Asia, "
        "wholesome charm with a hint of melancholy about time and friendship"
    ),

    # --- Manga: Jujutsu Kaisen / 呪術 ---
    (
        "Gege Akutami Jujutsu Kaisen manga art style: "
        "cursed energy technique domain expansion — black void background with ritual pattern emerging, "
        "ink splatter and distortion effects representing cursed energy corruption, "
        "dramatic black ink flooding large areas of the panel — cursed spirits rendered in dark organic forms, "
        "Infinity technique rendered as translucent barrier distorting space itself, "
        "expressive character faces alternating between casual humor and absolute horror, "
        "Gojo Satoru six eyes — blindfold or revealed eyes with snowflake star iris pattern, "
        "bold character designs with technical detail in cursed technique effects, "
        "dark horror atmosphere: blood, shadow, supernatural violence, "
        "the contrast of modern Tokyo streets against ancient cursed supernatural horror"
    ),

    # --- Manga: Attack on Titan / 進擊の巨人 ---
    (
        "Hajime Isayama Attack on Titan manga art style: "
        "deliberately rough scratchy ink line quality — imperfect, raw, emotionally charged, "
        "massive titan figure looming against the sky — grotesque body proportions, uncanny smile, empty eyes, "
        "ODM gear cables slicing diagonally across dramatic sky compositions, "
        "Wall Maria or Wall Rose architecture — massive medieval stone fortification, "
        "Survey Corps scouts in green cloaks, Wings of Freedom emblem, "
        "extreme contrast between small human figures and enormous titan scale, "
        "gritty despair and existential dread in every composition — humanity on the edge of extinction, "
        "rough cross-hatching in dark areas, heavy black shadows, "
        "the art style of a creator pouring raw anguish directly onto the page"
    ),

    # --- Animation: Miyazaki / Ghibli ---
    (
        "Hayao Miyazaki Studio Ghibli hand-painted animation background art style: "
        "soft luminous watercolour washes — greens and blues glowing with inner light, "
        "lush detailed natural environments: ancient forest, rolling hills, sky castle floating in clouds, "
        "warm afternoon sunlight filtering through leaves rendered as dappled pools of gold, "
        "hand-painted texture in every surface — visible brushwork, no digital smoothness, "
        "magical spirit creatures partially visible in natural elements, "
        "vintage European and Japanese architectural hybrid — Meiji-era town, moving castle, airship, "
        "the sky as protagonist — clouds with volume and personality, golden hour light, "
        "deep love for the natural world conveyed in every blade of grass, "
        "nostalgic warmth — the feeling of a summer afternoon that existed before you were born"
    ),

    # --- Game Art: Pokémon ---
    (
        "Ken Sugimori original Pokemon Red and Blue era art style: "
        "clean confident pen and ink outlines with flat watercolour fills — no gradients, "
        "creature design combining two or three natural animals or objects into one new being, "
        "simple bold silhouette readable at tiny Game Boy sprite size, "
        "limited color palette — three to four colors maximum per creature, "
        "the precise technical illustration of a natural history field guide applied to fantasy creatures, "
        "white background with single creature in three-quarter view pose, "
        "early digital-era color printing limitations visible — slight color separation, "
        "the nostalgic warmth of a trading card from 1996, "
        "bold cute immediately iconic designed to be drawn by children"
    ),

    # --- Game Art: Mario / Nintendo ---
    (
        "Nintendo Super Mario Bros. official art style: "
        "bold cel-shaded 3D render with clean outlines — the modern Nintendo art direction, "
        "primary color palette: pure red, blue, yellow — saturated and joyful, "
        "isometric platformer perspective showing multiple levels of a colorful world, "
        "Mario in red cap and overalls mid-jump fist raised, "
        "gold coins scattered, question mark blocks floating, green pipes emerging from ground, "
        "Mushroom Kingdom architecture — rolling green hills, blue sky with white puffy clouds, "
        "power-up mushroom or star glowing nearby, "
        "the visual language of pure joy and play — every element inviting touch and interaction, "
        "clean smooth surfaces no dirt or grit perfectly friendly world"
    ),

    # --- Contemporary: Yoshitomo Nara ---
    (
        "Yoshitomo Nara contemporary art style: "
        "single lone big-eyed child figure occupying center of canvas — deceptively innocent face, "
        "eyes slightly asymmetric, one eyebrow raised — hidden defiance and dark emotion beneath cute surface, "
        "flat matte acrylic paint with deliberate rough brushwork — anti-perfectionist texture, "
        "limited pastel palette: pale yellow, dusty pink, soft blue with ONE jarring dark accent color, "
        "minimal background — flat color or simple ground line only, "
        "child holding something unexpected: knife, cigarette, sign, wilted flower, "
        "the tension between innocent childhood imagery and adult emotional complexity, "
        "NO gradients, NO realism, deliberately naive and childlike yet deeply unsettling, "
        "raw emotional honesty that bypasses intellectual defenses"
    ),

    # --- Contemporary: Murakami ---
    (
        "Takashi Murakami superflat contemporary art style: "
        "hyper-flat zero-perspective composition — no shadows, no depth, pure 2D graphic surface, "
        "explosive psychedelic color palette: hot pink, electric yellow, acid green, cobalt blue, "
        "smiling flower characters with smiley-face centers repeated across background like wallpaper, "
        "manga-influenced character mixed with Japanese fine art tradition, "
        "obsessive symmetric pattern repetition consuming entire canvas, "
        "high-gloss lacquer finish aesthetic — the surface quality of a luxury brand collaboration, "
        "pop culture and centuries of Japanese art history colliding in one image, "
        "DOB character or Kaikai Kiki creatures floating in psychedelic space, "
        "the flattening of all hierarchies: high art and consumer culture perfectly equal"
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
    "Nikkei 225": "^N225",
    "TOPIX":      "^TOPX",
    "USD/JPY":    "JPY=X",
}

# Fallback tickers — only used if news extraction returns nothing
JAPAN_FALLBACK_TICKERS = [
    {"name": "Toyota",          "ticker": "7203.T"},
    {"name": "SoftBank Group",  "ticker": "9984.T"},
    {"name": "Sony",            "ticker": "6758.T"},
    {"name": "Nintendo",        "ticker": "7974.T"},
    {"name": "Tokyo Electron",  "ticker": "8035.T"},
]

# News sources — indices + liquid names to seed headlines
NEWS_SEED_SYMBOLS = [
    "^N225", "^TOPX",
    "7203.T",  # Toyota
    "9984.T",  # SoftBank
    "6758.T",  # Sony
    "8035.T",  # Tokyo Electron
    "9983.T",  # Fast Retailing
    "7974.T",  # Nintendo
    "6861.T",  # Keyence
    "8306.T",  # Mitsubishi UFJ
]

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

def get_japan_news(weekly=False):
    """Scrape headlines from seed symbols. More sources on Sunday."""
    news_items = []
    seen_titles = set()
    limit = 30 if weekly else 20
    fetch_per = 5 if weekly else 4
    for symbol in NEWS_SEED_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news or []
            for item in news[:fetch_per]:
                title = item.get('content', {}).get('title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    news_items.append(title)
        except Exception as e:
            print(f"  ⚠️ News fetch failed for {symbol}: {e}")
        if len(news_items) >= limit:
            break
    return news_items[:limit]

def extract_japan_tickers_from_news(news_items):
    """
    Ask Gemini to pull tickers from today's headlines.
    Instructs it to use .T suffix for TSE stocks.
    """
    try:
        news_text = "\n".join(f"- {n}" for n in news_items)
        prompt = (
            "From the following Japan financial news headlines, extract all companies or assets mentioned.\n"
            "Return ONLY a valid JSON array of objects with 'name' and 'ticker' fields.\n"
            "Rules for ticker symbols:\n"
            "  - Japanese stocks listed on TSE use numeric code + .T suffix "
            "(e.g. Toyota = '7203.T', Sony = '6758.T', SoftBank = '9984.T', "
            "Nintendo = '7974.T', Fast Retailing = '9983.T', Tokyo Electron = '8035.T', "
            "Keyence = '6861.T', Mitsubishi UFJ = '8306.T', Honda = '7267.T', "
            "Panasonic = '6752.T', Recruit = '6098.T', KDDI = '9433.T').\n"
            "  - US stocks mentioned keep their normal ticker (e.g. Apple = 'AAPL', Nvidia = 'NVDA').\n"
            "  - Skip market indices like Nikkei or TOPIX.\n"
            "  - If unsure of the ticker, skip that company.\n"
            "Limit to the 10 most prominently mentioned companies.\n"
            "Return only JSON, no explanation, no markdown.\n\n"
            f"Headlines:\n{news_text}\n\n"
            'Example: [{"name": "Toyota", "ticker": "7203.T"}, {"name": "Nvidia", "ticker": "NVDA"}]'
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        extracted = json.loads(raw)
        print(f"  Gemini extracted {len(extracted)} tickers from news")
        return extracted
    except Exception as e:
        print(f"  ⚠️ Ticker extraction failed: {e}")
        return []

def get_dynamic_stock_data(extracted_tickers, weekly=False):
    """Fetch price data for Gemini-extracted tickers. Falls back if empty."""
    period = "5d" if weekly else "2d"
    tickers_to_use = extracted_tickers if extracted_tickers else JAPAN_FALLBACK_TICKERS
    if not extracted_tickers:
        print("  ℹ️ No tickers extracted — using fallback list")
    results = {}
    for item in tickers_to_use:
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
    lines.append(f"📊 Japan Indices ({label}):")
    for name, d in core_data.items():
        arrow = "▲" if d['change_pct'] > 0 else "▼"
        if name == "USD/JPY":
            lines.append(f"  {arrow} {name}: ¥{d['price']:,}  ({d['change_pct']:+.2f}%)")
        else:
            lines.append(f"  {arrow} {name}: {d['price']:,}  ({d['change_pct']:+.2f}%)")
    if dynamic_data:
        lines.append("")
        lines.append("🏢 Stocks In The News (TSE):")
        sorted_stocks = sorted(
            dynamic_data.items(),
            key=lambda x: abs(x[1]['change_pct']),
            reverse=True
        )
        for name, d in sorted_stocks:
            arrow = "▲" if d['change_pct'] > 0 else "▼"
            lines.append(f"  {arrow} {name}: ¥{d['price']:,}  ({d['change_pct']:+.2f}%)")
    return "\n".join(lines)

# ====================== GEMINI: DAILY STORY ======================
def generate_daily_story(core_data, dynamic_data, news_items, art_style):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, weekly=False)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        prompt = (
            "You are a creative financial art director for a viral daily Japan market storytelling project.\n"
            f"Today is {get_hk_time().strftime('%A, %B %d, %Y')} (Hong Kong Time). This is a DAILY recap of the Tokyo Stock Exchange.\n\n"
            "Your job:\n"
            "1. Identify the single most interesting, dramatic, funny, or important story of the day.\n"
            "   Look beyond just the indices — consider: big individual stock moves, yen rate impact, "
            "BOJ policy signals, notable earnings, sector themes, global macro hitting Japan, "
            "anything quirky or surprising in the headlines. Be flexible and creative.\n"
            "2. Write a SHORT punchy Japan market recap (3-5 sentences, flowing prose, no bullet points).\n"
            "   Mention specific companies, the yen, and what it means for Japan's economy where relevant.\n"
            "   If a stock moved a lot, say so and why. If it was a macro/yen day, say that instead.\n"
            "3. Create a vivid, creative, exaggerated image description capturing this story visually.\n"
            "   - Symbolic, funny, dramatic, or surprising. NOT a literal chart.\n"
            "   - Use Japanese cultural imagery naturally — Mount Fuji, bullet trains, Tokyo skyline, "
            "cherry blossoms, samurai, anime energy, neon Shibuya, sumo, onsen, ramen — when it fits the story.\n"
            "   - Include real companies or brands if they are the story.\n"
            "   - Mood matches the market: euphoric, panicked, boring, chaotic, triumphant, absurd.\n"
            "   - The image MUST be executed faithfully in the specified Japanese art style.\n"
            "4. Write a punchy Instagram caption:\n"
            "   - Strong hook line at the start\n"
            "   - 2-3 short witty sentences with Japan market flavor\n"
            "   - End with 5-8 hashtags on a new line, EVERY hashtag MUST start with #\n"
            "   - Include at least 2 Japan-specific hashtags (e.g. #Nikkei #TokyoStocks #日経平均)\n"
            "   - Max 150 words total\n\n"
            f"Market Data:\n{market_data_str}\n\n"
            f"News Headlines:\n{news_text}\n\n"
            f"Art Style (execute with full technical commitment):\n{art_style}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            "{\n"
            '  "recap": "3-5 sentence Japan market recap.",\n'
            '  "image_prompt": "Detailed visual image description with full Japanese art style execution.",\n'
            '  "ig_caption": "Punchy IG caption with hook + Japan hashtags."\n'
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
        recap = "Tokyo markets moved today with notable activity across major indices."
        image_prompt = f"A dramatic Tokyo stock exchange scene with Mount Fuji in background. {art_style}."
        ig_caption = "Tokyo never sleeps. 📈\n#Nikkei #TokyoStocks #日経平均 #JapanMarkets"
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
            "You are a creative financial art director for a viral weekly Japan market storytelling project.\n"
            f"This is the WEEKLY RECAP for the Tokyo Stock Exchange, week of {week_start} - {week_end}.\n\n"
            "Your job:\n"
            "1. Identify the 2-3 biggest themes or stories that defined this week in Japan markets.\n"
            "   Consider: BOJ policy signals, yen trend for the week, Nikkei arc, key earnings, "
            "notable individual stock moves, global macro impact on Japan, any surprising developments.\n"
            "2. Write a punchy weekly Japan market narrative (5-7 sentences, flowing prose, no bullet points).\n"
            "   Capture the arc of the week — how did it start, what happened, how did it end?\n"
            "3. Create a vivid, creative weekly recap image — think Japanese weekly magazine cover.\n"
            "   - Bold, symbolic, dramatic. Use Japanese cultural imagery naturally.\n"
            "   - Cover the week's biggest theme visually.\n"
            "   - The image MUST be executed faithfully in the specified Japanese art style.\n"
            "4. Write a punchy Instagram weekly recap caption:\n"
            "   - Open with a strong Week in Review hook with Japan flavor\n"
            "   - 3-4 short witty sentences summarising the week\n"
            "   - End with 6-10 hashtags, EVERY hashtag MUST start with #\n"
            "   - Include Japan-specific hashtags\n"
            "   - Max 200 words total\n\n"
            f"Weekly Market Data:\n{market_data_str}\n\n"
            f"This Week's Key Headlines:\n{news_text}\n\n"
            f"Art Style (execute with full technical commitment):\n{art_style}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            "{\n"
            '  "recap": "5-7 sentence weekly Japan market narrative.",\n'
            '  "image_prompt": "Detailed weekly visual description with full Japanese art style execution.",\n'
            '  "ig_caption": "Weekly recap IG caption with hook + Japan hashtags."\n'
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
        recap = "It was an eventful week on the Tokyo Stock Exchange."
        image_prompt = f"A dramatic weekly Japan market scene. {art_style}. Masterpiece, ultra detailed."
        ig_caption = "Another week in Tokyo in the books. 📊\n#WeeklyRecap #Nikkei #JapanStocks #日経平均"
        return recap, image_prompt, ig_caption

# ====================== GENERATE IMAGE ======================
async def generate_image(image_prompt):
    print(f"🎨 Image prompt: {image_prompt[:150]}...")
    full_prompt = (
        "Create a stunning high-resolution vertical digital painting.\n"
        "Edge-to-edge, no white borders, no padding, no frames, full bleed.\n"
        "Vertical 3:4 portrait orientation.\n\n"
        "CRITICAL: Execute the Japanese art style with absolute technical faithfulness. "
        "Do NOT default to generic cartoon or digital illustration. "
        "Commit fully to the specific medium, technique, and aesthetic described. "
        "If the style calls for woodblock print, show the grain and flat color of a real woodblock print. "
        "If it calls for sumi ink on washi paper, show raw ink texture on paper grain. "
        "If it calls for anime cel animation, show clean outlines and flat color areas. "
        "The cultural authenticity of the Japanese art form is paramount.\n\n"
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
    image_path = "market_museum_japan_today.jpg"
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
        print(f"[{hk_time.strftime('%Y-%m-%d %H:%M')} HKT] 🗾 Japan Market Museum Started — {mode}")

        # 1. Core index data
        print("📈 Fetching Japan index data...")
        core_data = get_core_market_data(weekly=sunday)

        # 2. News first — drives everything
        print("📰 Fetching Japan market news...")
        news_items = get_japan_news(weekly=sunday)
        print(f"  Got {len(news_items)} headlines")

        # 3. Extract tickers dynamically from the news
        print("🔍 Extracting tickers from news...")
        extracted_tickers = extract_japan_tickers_from_news(news_items)

        # 4. Fetch price data for those tickers (fallback if empty)
        print("📊 Fetching stock data...")
        dynamic_data = get_dynamic_stock_data(extracted_tickers, weekly=sunday)

        # 5. Random Japanese art style
        art_style = get_random_style()
        print(f"🎨 Art style: {art_style[:80]}...")

        # 6. Generate story
        print("✍️ Generating Japan market story...")
        if sunday:
            recap, image_prompt, ig_caption = generate_weekly_story(
                core_data, dynamic_data, news_items, art_style
            )
        else:
            recap, image_prompt, ig_caption = generate_daily_story(
                core_data, dynamic_data, news_items, art_style
            )
        print(f"  Recap: {recap[:100]}...")

        # 7. Generate image
        image_path = await generate_image(image_prompt)
        if not image_path:
            print("❌ No image returned")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ Japan: No image generated today.")
            return

        # 8. Build Telegram caption
        market_data_str = format_market_data(core_data, dynamic_data, weekly=sunday)
        date_str = hk_time.strftime('%B %d, %Y')
        header = (
            f"🗾 Japan Weekly Recap • {date_str}"
            if sunday else
            f"🗾 Japan Market Museum • {date_str}"
        )
        tg_caption = (
            f"{header}\n\n"
            f"{recap}\n\n"
            f"{market_data_str}\n\n"
            "#MarketMuseum #Nikkei #JapanStocks"
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
            "📱 *IG Caption (Japan Weekly) — copy & paste ready:*"
            if sunday else
            "📱 *IG Caption (Japan) — copy & paste ready:*"
        )
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"{ig_label}\n\n{ig_caption}",
            parse_mode="Markdown"
        )

        print(f"✅ Success! Japan {mode} sent to Telegram.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=f"⚠️ Japan Market Museum Error: {str(e)[:300]}"
            )
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
