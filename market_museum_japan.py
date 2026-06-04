import os
import random
import json
import math
from google import genai
from google.genai import types
from telegram import Bot
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
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
        "warm amber lantern light against cool blue rain, "
        "traditional Japanese seasonal beauty — wabi-sabi impermanence, "
        "flat color areas with delicate hand-carved detail lines, "
        "the melancholy poetry of journeys and changing weather"
    ),
    (
        "Inoue Takehiko sumi-e manga masterpiece in the style of Vagabond: "
        "explosive gestural sumi ink brushstrokes on raw washi paper texture, "
        "dramatic tonal range from jet black pooling ink to ghost-pale grey wash, "
        "visible bristle marks, ink bleed and splatter intentionally left as part of the art, "
        "single powerful figure rendered in five bold decisive strokes, "
        "80 percent negative white space — emptiness is the subject, "
        "lightning-fast mark-making conveying both explosive motion and zen inner stillness simultaneously, "
        "NO color, NO digital smoothing, RAW traditional ink on paper, "
        "monochrome only — jet black, mid grey, pale silver, white"
    ),
    (
        "Araki Hirohiko JoJo's Bizarre Adventure manga art style: "
        "impossibly dramatic contrapposto pose defying human anatomy entirely for maximum visual impact, "
        "heavy baroque cross-hatching and fine stippling in shadow areas, "
        "fashion illustration meets Italian Renaissance painting meets shounen manga, "
        "intense screaming facial expression with highly detailed musculature, "
        "surreal gradient background shifting from deep magenta to electric teal, "
        "ornate decorative framing elements — stars, geometric patterns, speed lines, "
        "over-the-top masculine energy wrapped in high fashion sensibility"
    ),
    (
        "Koyoharu Gotoge Demon Slayer Kimetsu no Yaiba manga art style: "
        "bold geometric wisteria and checked patterns (ichimatsu, asanoha) covering clothing and backgrounds, "
        "dramatic action poses mid-combat with sword trails and elemental breath technique effects, "
        "Total Concentration Breathing rendered as swirling elemental energy — fire, water, thunder, wind, "
        "highly expressive large eyes with detailed iris reflections, "
        "washi paper texture visible beneath ink lines, "
        "rich jewel-tone color palette: crimson, deep indigo, gold, forest green"
    ),
    (
        "Masashi Kishimoto Naruto manga art style: "
        "extreme dynamic action pose with chakra energy exploding outward from the figure, "
        "speed lines radiating from central figure creating explosive kinetic energy, "
        "Rasengan or Chidori energy ball rendered as swirling blue-white electrical plasma, "
        "bold thick black outlines with precise detail in facial expressions — determination and intensity, "
        "dramatic perspective foreshortening — fist or jutsu hand seal rushing toward viewer, "
        "orange and blue color palette with electric white energy highlights"
    ),
    (
        "Akira Toriyama Dragon Ball manga art style: "
        "clean confident ink lines with precise weight variation — thick outlines, thin interior detail lines, "
        "Super Saiyan transformation with electric golden aura crackling around the entire figure, "
        "extreme power-up pose: legs planted wide, muscles bulging, screaming skyward, "
        "energy ki aura rendered as bold radiating light beams and crackling electricity, "
        "dramatic sky background — storm clouds parting, lightning, distant mountains, "
        "bold primary color palette: gold, orange, blue sky"
    ),
    (
        "Fujiko F. Fujio Doraemon manga art style: "
        "perfectly rounded smooth forms — circles and gentle curves, zero sharp edges, "
        "clean simple ink outlines with consistent weight, "
        "playful gadget from the 4D pocket featured prominently — hovering, glowing, magical, "
        "warm gentle humor in facial expressions — wide innocent eyes, open mouths of surprise, "
        "primary color palette: blue, red, yellow, white — clear and joyful, "
        "wholesome charm with a hint of melancholy about time and friendship"
    ),
    (
        "Gege Akutami Jujutsu Kaisen manga art style: "
        "cursed energy technique domain expansion — black void background with ritual pattern emerging, "
        "ink splatter and distortion effects representing cursed energy corruption, "
        "dramatic black ink flooding large areas — cursed spirits rendered in dark organic forms, "
        "expressive character faces alternating between casual humor and absolute horror, "
        "Gojo Satoru six eyes — blindfold or revealed eyes with snowflake star iris pattern, "
        "dark horror atmosphere: blood, shadow, supernatural violence"
    ),
    (
        "Hajime Isayama Attack on Titan manga art style: "
        "deliberately rough scratchy ink line quality — imperfect, raw, emotionally charged, "
        "massive titan figure looming against the sky — grotesque body proportions, uncanny smile, empty eyes, "
        "ODM gear cables slicing diagonally across dramatic sky compositions, "
        "extreme contrast between small human figures and enormous titan scale, "
        "gritty despair and existential dread in every composition, "
        "rough cross-hatching in dark areas, heavy black shadows"
    ),
    (
        "Hayao Miyazaki Studio Ghibli hand-painted animation background art style: "
        "soft luminous watercolour washes — greens and blues glowing with inner light, "
        "lush detailed natural environments: ancient forest, rolling hills, sky castle floating in clouds, "
        "warm afternoon sunlight filtering through leaves rendered as dappled pools of gold, "
        "hand-painted texture in every surface — visible brushwork, no digital smoothness, "
        "the sky as protagonist — clouds with volume and personality, golden hour light, "
        "nostalgic warmth — the feeling of a summer afternoon that existed before you were born"
    ),
    (
        "Ken Sugimori original Pokemon Red and Blue era art style: "
        "clean confident pen and ink outlines with flat watercolour fills — no gradients, "
        "creature design combining natural animals into one new being, "
        "simple bold silhouette readable at tiny Game Boy sprite size, "
        "limited color palette — three to four colors maximum, "
        "the precise technical illustration of a natural history field guide applied to fantasy creatures, "
        "the nostalgic warmth of a trading card from 1996"
    ),
    (
        "Nintendo Super Mario Bros. official art style: "
        "bold cel-shaded 3D render with clean outlines — the modern Nintendo art direction, "
        "primary color palette: pure red, blue, yellow — saturated and joyful, "
        "Mario in red cap and overalls mid-jump fist raised, "
        "gold coins scattered, question mark blocks floating, green pipes emerging from ground, "
        "Mushroom Kingdom architecture — rolling green hills, blue sky with white puffy clouds, "
        "the visual language of pure joy and play"
    ),
    (
        "Yoshitomo Nara contemporary art style: "
        "single lone big-eyed child figure occupying center of canvas — deceptively innocent face, "
        "eyes slightly asymmetric, one eyebrow raised — hidden defiance and dark emotion beneath cute surface, "
        "flat matte acrylic paint with deliberate rough brushwork — anti-perfectionist texture, "
        "limited pastel palette with ONE jarring dark accent color, "
        "child holding something unexpected: knife, cigarette, sign, wilted flower, "
        "NO gradients, NO realism, deliberately naive yet deeply unsettling"
    ),
    (
        "Takashi Murakami superflat contemporary art style: "
        "hyper-flat zero-perspective composition — no shadows, no depth, pure 2D graphic surface, "
        "explosive psychedelic color palette: hot pink, electric yellow, acid green, cobalt blue, "
        "smiling flower characters with smiley-face centers repeated across background like wallpaper, "
        "obsessive symmetric pattern repetition consuming entire canvas, "
        "high-gloss lacquer finish aesthetic, "
        "pop culture and centuries of Japanese art history colliding in one image"
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

JAPAN_FALLBACK_TICKERS = [
    {"name": "Toyota",         "ticker": "7203.T"},
    {"name": "SoftBank Group", "ticker": "9984.T"},
    {"name": "Sony",           "ticker": "6758.T"},
    {"name": "Nintendo",       "ticker": "7974.T"},
    {"name": "Tokyo Electron", "ticker": "8035.T"},
]

NEWS_SEED_SYMBOLS = [
    "^N225", "^TOPX",
    "7203.T", "9984.T", "6758.T",
    "8035.T", "9983.T", "7974.T",
    "6861.T", "8306.T",
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
    try:
        news_text = "\n".join(f"- {n}" for n in news_items)
        prompt = (
            "From the following Japan financial news headlines, extract all companies or assets mentioned.\n"
            "Return ONLY a valid JSON array of objects with 'name' and 'ticker' fields.\n"
            "Rules:\n"
            "  - Japanese stocks on TSE use numeric code + .T suffix "
            "(e.g. Toyota = '7203.T', Sony = '6758.T', SoftBank = '9984.T', "
            "Nintendo = '7974.T', Fast Retailing = '9983.T', Tokyo Electron = '8035.T', "
            "Keyence = '6861.T', Mitsubishi UFJ = '8306.T', Honda = '7267.T', "
            "Panasonic = '6752.T', Recruit = '6098.T', KDDI = '9433.T').\n"
            "  - US stocks keep their normal ticker (e.g. Nvidia = 'NVDA').\n"
            "  - Skip indices. Skip if ticker unknown.\n"
            "Limit to 10 most prominent. Return only JSON, no markdown.\n\n"
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

# ====================== INFOGRAPHIC ======================
def make_infographic(core_data, dynamic_data, date_str, weekly=False):
    """
    Generate a portrait 3:4 infographic (1080x1440px).
    Dark background, Japan-accented, @mini_money.lab watermark.
    """
    W, H = 1080, 1440
    PAD = 60

    # --- Color palette ---
    BG          = (10, 10, 18)        # near-black navy
    PANEL       = (20, 22, 35)        # slightly lighter panel
    BORDER      = (40, 44, 68)        # subtle border
    WHITE       = (255, 255, 255)
    MUTED       = (140, 145, 170)
    RED_UP      = (255, 75, 75)       # gain red (Japan convention: red = up)
    BLUE_DOWN   = (80, 160, 255)      # loss blue (Japan convention: blue = down)
    ACCENT      = (220, 40, 40)       # Japan red accent
    GOLD        = (255, 200, 60)
    DIVIDER     = (35, 38, 58)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- Font loader (falls back gracefully) ---
    def font(size, bold=False):
        candidates = (
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
            if bold else
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
        )
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def centered_x(text, fnt, x1, x2):
        bbox = draw.textbbox((0, 0), text, font=fnt)
        tw = bbox[2] - bbox[0]
        return x1 + (x2 - x1 - tw) // 2

    def right_x(text, fnt, x2):
        bbox = draw.textbbox((0, 0), text, font=fnt)
        tw = bbox[2] - bbox[0]
        return x2 - tw

    # ── Rising sun decoration (top centre) ──────────────────────
    sun_cx, sun_cy = W // 2, 90
    sun_r = 38
    # rays
    for i in range(12):
        angle = math.radians(i * 30)
        x1 = sun_cx + int((sun_r + 10) * math.cos(angle))
        y1 = sun_cy + int((sun_r + 10) * math.sin(angle))
        x2 = sun_cx + int((sun_r + 26) * math.cos(angle))
        y2 = sun_cy + int((sun_r + 26) * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=(180, 30, 30, 120), width=2)
    draw.ellipse(
        [sun_cx - sun_r, sun_cy - sun_r, sun_cx + sun_r, sun_cy + sun_r],
        fill=ACCENT
    )

    # ── Header ───────────────────────────────────────────────────
    y = 148
    mode_label = "WEEKLY RECAP" if weekly else "DAILY RECAP"
    label_fnt = font(22)
    lw = draw.textbbox((0,0), mode_label, font=label_fnt)[2]
    draw.text(((W - lw) // 2, y), mode_label, font=label_fnt, fill=MUTED)

    y += 38
    title_fnt = font(54, bold=True)
    title = "JAPAN MARKET"
    draw.text((centered_x(title, title_fnt, 0, W), y), title, font=title_fnt, fill=WHITE)

    y += 62
    date_fnt = font(26)
    draw.text((centered_x(date_str, date_fnt, 0, W), y), date_str, font=date_fnt, fill=MUTED)

    # ── Thin red divider line ─────────────────────────────────────
    y += 46
    draw.rectangle([PAD, y, W - PAD, y + 2], fill=ACCENT)

    # ── Indices section ───────────────────────────────────────────
    y += 28
    section_fnt = font(22)
    draw.text((PAD, y), "INDICES", font=section_fnt, fill=GOLD)
    y += 34

    index_name_fnt = font(32, bold=True)
    index_val_fnt  = font(30)
    index_pct_fnt  = font(36, bold=True)
    row_h = 88

    for name, d in core_data.items():
        pct = d['change_pct']
        color = RED_UP if pct >= 0 else BLUE_DOWN
        arrow = "▲" if pct >= 0 else "▼"
        pct_str = f"{arrow} {abs(pct):.2f}%"

        # panel background
        draw.rounded_rectangle(
            [PAD, y, W - PAD, y + row_h - 8],
            radius=12, fill=PANEL, outline=BORDER, width=1
        )

        # name
        draw.text((PAD + 24, y + 14), name, font=index_name_fnt, fill=WHITE)

        # price
        if name == "USD/JPY":
            price_str = f"¥{d['price']:,.2f}"
        else:
            price_str = f"{d['price']:,.0f}"
        draw.text((PAD + 24, y + 48), price_str, font=index_val_fnt, fill=MUTED)

        # pct — right aligned
        rx = right_x(pct_str, index_pct_fnt, W - PAD - 24)
        draw.text((rx, y + 26), pct_str, font=index_pct_fnt, fill=color)

        y += row_h

    # ── Divider ───────────────────────────────────────────────────
    y += 10
    draw.rectangle([PAD, y, W - PAD, y + 1], fill=DIVIDER)
    y += 22

    # ── Stocks in the news ────────────────────────────────────────
    if dynamic_data:
        draw.text((PAD, y), "STOCKS IN THE NEWS", font=section_fnt, fill=GOLD)
        y += 34

        sorted_stocks = sorted(
            dynamic_data.items(),
            key=lambda x: abs(x[1]['change_pct']),
            reverse=True
        )[:6]  # max 6 stocks

        max_abs = max(abs(d['change_pct']) for _, d in sorted_stocks) or 1
        bar_fnt  = font(28, bold=True)
        bar_sub  = font(22)
        bar_h    = 72
        bar_max  = W - PAD * 2 - 200  # max bar width

        for name, d in sorted_stocks:
            pct = d['change_pct']
            color = RED_UP if pct >= 0 else BLUE_DOWN
            arrow = "▲" if pct >= 0 else "▼"
            pct_str = f"{arrow} {abs(pct):.2f}%"
            bar_w = int(bar_max * (abs(pct) / max_abs))
            bar_w = max(bar_w, 8)

            # row background
            draw.rounded_rectangle(
                [PAD, y, W - PAD, y + bar_h - 6],
                radius=10, fill=PANEL, outline=BORDER, width=1
            )

            # colored bar fill (subtle)
            bar_color = (80, 20, 20) if pct >= 0 else (10, 30, 70)
            draw.rounded_rectangle(
                [PAD, y, PAD + bar_w + 60, y + bar_h - 6],
                radius=10, fill=bar_color
            )

            # name + price
            short_name = name[:18] + ("…" if len(name) > 18 else "")
            draw.text((PAD + 18, y + 10), short_name, font=bar_fnt, fill=WHITE)
            draw.text((PAD + 18, y + 42), f"¥{d['price']:,.0f}", font=bar_sub, fill=MUTED)

            # pct right
            rx = right_x(pct_str, bar_fnt, W - PAD - 18)
            draw.text((rx, y + 22), pct_str, font=bar_fnt, fill=color)

            y += bar_h

    # ── Bottom: wave pattern strip ────────────────────────────────
    wave_y = H - 110
    draw.rectangle([0, wave_y, W, wave_y + 2], fill=(30, 33, 55))
    # simple wave using short segments
    pts = []
    steps = 60
    for i in range(steps + 1):
        wx = int(i * W / steps)
        wy = wave_y + 18 + int(12 * math.sin(i * math.pi * 4 / steps))
        pts.append((wx, wy))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=(60, 65, 100), width=2)

    # ── Watermark ─────────────────────────────────────────────────
    wm_fnt = font(26, bold=True)
    wm_sub = font(20)
    wm = "@mini_money.lab"
    wm_x = centered_x(wm, wm_fnt, 0, W)
    draw.text((wm_x, H - 72), wm, font=wm_fnt, fill=MUTED)
    tag = "Japan Market Museum"
    draw.text((centered_x(tag, wm_sub, 0, W), H - 42), tag, font=wm_sub, fill=(70, 75, 100))

    path = "market_museum_japan_infographic.jpg"
    img.save(path, "JPEG", quality=95)
    print(f"✅ Infographic saved: {W}x{H}")
    return path

# ====================== GEMINI STORY ======================
def generate_daily_story(core_data, dynamic_data, news_items, art_style):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, weekly=False)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        prompt = (
            "You are a creative financial art director for a viral daily Japan market storytelling project.\n"
            f"Today is {get_hk_time().strftime('%A, %B %d, %Y')} (Hong Kong Time). DAILY recap of the Tokyo Stock Exchange.\n\n"
            "1. Identify the single most interesting, dramatic, or important story of the day.\n"
            "   Look beyond just indices — big stock moves, yen rate, BOJ signals, earnings, sector themes, "
            "anything surprising in the headlines.\n"
            "2. Write a SHORT punchy Japan market recap (3-5 sentences, flowing prose, no bullets).\n"
            "   Mention specific companies, the yen, what it means for Japan where relevant.\n"
            "3. Create a vivid, creative image description capturing this story visually.\n"
            "   - Symbolic, funny, dramatic — NOT a literal chart.\n"
            "   - Use Japanese cultural imagery naturally: Mount Fuji, bullet trains, Tokyo skyline, "
            "cherry blossoms, samurai, neon Shibuya, sumo, ramen — when it fits the story.\n"
            "   - Include real companies or brands if they are the story.\n"
            "   - Mood matches the market: euphoric, panicked, chaotic, triumphant, absurd.\n"
            "   - The image MUST be executed faithfully in the specified Japanese art style.\n"
            "4. Write a punchy Instagram caption:\n"
            "   - Strong hook line\n"
            "   - 2-3 short witty sentences with Japan market flavor\n"
            "   - 5-8 hashtags, EVERY hashtag MUST start with #\n"
            "   - At least 2 Japan hashtags (e.g. #Nikkei #日経平均 #TokyoStocks)\n"
            "   - Max 150 words\n\n"
            f"Market Data:\n{market_data_str}\n\n"
            f"News Headlines:\n{news_text}\n\n"
            f"Art Style:\n{art_style}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            '{"recap":"...","image_prompt":"...","ig_caption":"..."}'
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result.get("recap",""), result.get("image_prompt",""), result.get("ig_caption","")
    except Exception as e:
        print(f"⚠️ Daily story failed: {e}")
        return (
            "Tokyo markets moved today with notable activity across major indices.",
            f"A dramatic Tokyo stock exchange scene with Mount Fuji. {art_style}.",
            "Tokyo never sleeps. 📈\n#Nikkei #TokyoStocks #日経平均 #JapanMarkets"
        )

def generate_weekly_story(core_data, dynamic_data, news_items, art_style):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, weekly=True)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        hk_now = get_hk_time()
        week_start = (hk_now - timedelta(days=6)).strftime('%B %d')
        week_end = hk_now.strftime('%B %d, %Y')
        prompt = (
            "You are a creative financial art director for a viral weekly Japan market project.\n"
            f"WEEKLY RECAP for Tokyo Stock Exchange, week of {week_start} - {week_end}.\n\n"
            "1. Identify the 2-3 biggest themes that defined this week.\n"
            "2. Write a punchy weekly Japan narrative (5-7 sentences, flowing prose, no bullets).\n"
            "3. Create a vivid weekly recap image — Japanese weekly magazine cover.\n"
            "   Bold, symbolic, dramatic. Japanese cultural imagery. Full art style commitment.\n"
            "4. Weekly IG caption:\n"
            "   - Strong Week in Review hook\n"
            "   - 3-4 witty sentences\n"
            "   - 6-10 hashtags, ALL starting with #, include Japan hashtags\n"
            "   - Max 200 words\n\n"
            f"Weekly Market Data:\n{market_data_str}\n\n"
            f"Headlines:\n{news_text}\n\n"
            f"Art Style:\n{art_style}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            '{"recap":"...","image_prompt":"...","ig_caption":"..."}'
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result.get("recap",""), result.get("image_prompt",""), result.get("ig_caption","")
    except Exception as e:
        print(f"⚠️ Weekly story failed: {e}")
        return (
            "It was an eventful week on the Tokyo Stock Exchange.",
            f"A dramatic weekly Japan market scene. {art_style}.",
            "Another week in Tokyo. 📊\n#WeeklyRecap #Nikkei #JapanStocks #日経平均"
        )

# ====================== GENERATE AI IMAGE ======================
async def generate_image(image_prompt):
    print(f"🎨 Image prompt: {image_prompt[:150]}...")
    full_prompt = (
        "Create a stunning high-resolution vertical digital painting.\n"
        "Edge-to-edge, no white borders, no padding, no frames, full bleed.\n"
        "Vertical 3:4 portrait orientation.\n\n"
        "CRITICAL: Execute the Japanese art style with absolute technical faithfulness. "
        "Do NOT default to generic cartoon or digital illustration. "
        "Commit fully to the specific medium, technique, and aesthetic described. "
        "The cultural authenticity of the Japanese art form is paramount.\n\n"
        f"{image_prompt}\n\n"
        "Masterpiece quality. Ultra detailed. Professional museum-worthy execution."
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=full_prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    image_path = "market_museum_japan_today.jpg"
    for part in response.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(image_path, "JPEG", quality=95)
            print(f"✅ AI image saved: {image.size}")
            return image_path
    return None

# ====================== MAIN ======================
async def main():
    try:
        hk_time = get_hk_time()
        sunday = is_sunday_hk()
        mode = "📅 WEEKLY RECAP" if sunday else "📰 DAILY RECAP"
        print(f"[{hk_time.strftime('%Y-%m-%d %H:%M')} HKT] 🗾 Japan Market Museum — {mode}")

        # 1. Core index data
        print("📈 Fetching Japan index data...")
        core_data = get_core_market_data(weekly=sunday)

        # 2. News first
        print("📰 Fetching Japan market news...")
        news_items = get_japan_news(weekly=sunday)
        print(f"  Got {len(news_items)} headlines")

        # 3. Extract tickers dynamically from news
        print("🔍 Extracting tickers from news...")
        extracted_tickers = extract_japan_tickers_from_news(news_items)

        # 4. Fetch price data (fallback if empty)
        print("📊 Fetching stock data...")
        dynamic_data = get_dynamic_stock_data(extracted_tickers, weekly=sunday)

        # 5. Random Japanese art style
        art_style = get_random_style()
        print(f"🎨 Art style: {art_style[:80]}...")

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

        # 7. Generate AI artwork (Image 1)
        ai_image_path = await generate_image(image_prompt)
        if not ai_image_path:
            print("❌ No AI image returned")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ Japan: No AI image generated today.")
            return

        # 8. Generate infographic (Image 2)
        print("📊 Generating infographic...")
        date_str = hk_time.strftime('%B %d, %Y')
        infographic_path = make_infographic(core_data, dynamic_data, date_str, weekly=sunday)

        # 9. Build Telegram caption
        market_data_str = format_market_data(core_data, dynamic_data, weekly=sunday)
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

        # 10. Send both images as a media group
        from telegram import InputMediaPhoto
        media = [
            InputMediaPhoto(
                media=open(ai_image_path, 'rb'),
                caption=tg_caption
            ),
            InputMediaPhoto(
                media=open(infographic_path, 'rb')
            ),
        ]
        await bot.send_media_group(chat_id=CHAT_ID, media=media)

        # 11. Send IG caption separately
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

        print(f"✅ Success! Japan {mode} — 2 images sent to Telegram.")

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
