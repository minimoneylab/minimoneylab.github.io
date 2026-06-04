import os
import random
import json
import math
from google import genai
from google.genai import types
from telegram import Bot, InputMediaPhoto
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

# ====================== ART STYLES ======================
ART_STYLES = [
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
    (
        "Inoue Takehiko sumi-e masterpiece in the style of Vagabond manga: "
        "dramatic black sumi ink on raw white washi paper, "
        "visible bristle marks and ink bleed into paper grain, "
        "heavy ink pooling in deep shadows fading to ghost-light grey washes, "
        "lightning gestural brushstrokes conveying explosive motion and inner stillness, "
        "80 percent negative white space, zero color, "
        "NO digital smoothing, RAW traditional ink media texture"
    ),
    (
        "Inoue Takehiko real style ink painting: loose expressive sumi-e, "
        "monochrome ink wash with dramatic tonal range from jet black to pale silver grey, "
        "ink splatter and drip marks intentionally left, "
        "single powerful figure rendered in 5 bold strokes, "
        "zen emptiness surrounding the subject, "
        "rough uneven paper texture visible, deeply emotional and raw"
    ),
    (
        "Araki Hirohiko JoJo's Bizarre Adventure style: "
        "impossibly dramatic contrapposto pose defying anatomy for maximum impact, "
        "heavy baroque cross-hatching and stippling for shadows, "
        "fashion illustration meets Italian Renaissance meets manga, "
        "intense screaming facial expression with detailed musculature, "
        "surreal color gradient background in magenta and teal, "
        "ornate decorative framing elements, over-the-top masculine energy with high fashion sensibility"
    ),
    (
        "Banksy stencil street art: razor-sharp high-contrast stencil spray paint on rough concrete wall, "
        "stark black silhouette against white with ONE single bold accent color, "
        "subversive political message embedded in apparently simple image, "
        "photorealistic stencil technique, "
        "gritty urban texture of weathered wall visible through paint, "
        "wit and dark irony in every element"
    ),
    (
        "Vincent van Gogh oil painting: thick impasto paint applied with palette knife and bristle brush, "
        "every inch of canvas covered in swirling directional brushstrokes, "
        "electric cobalt blue and cadmium yellow dominate, "
        "sky and background in hypnotic cyclone swirls, "
        "raw emotional intensity in every mark, "
        "visible paint texture you could reach out and touch"
    ),
    (
        "Leonardo da Vinci Renaissance oil painting: "
        "sfumato technique with no hard edges, forms emerging from smoky atmospheric haze, "
        "warm amber and raw umber palette of Renaissance masters, "
        "anatomically perfect figures with psychological depth in their gaze, "
        "golden ratio composition, soft chiaroscuro modeling of form, "
        "craquelure texture of 500-year-old oil paint"
    ),
    (
        "Rembrandt van Rijn Dutch Golden Age oil painting: "
        "single dramatic shaft of warm candlelight piercing absolute darkness, "
        "rich impasto paint surface with decades of glazing, "
        "psychological intensity in illuminated face emerging from deep shadow, "
        "burnt sienna and raw umber with gold ochre light, "
        "the lighting of a Dutch master who understood human suffering"
    ),
    (
        "Johannes Vermeer Dutch Golden Age oil painting: "
        "cool pearl-like northern light from single left window, "
        "incredibly precise photorealistic detail in fabric and surface texture, "
        "calm domestic intimacy frozen in perfect moment, "
        "lapis lazuli blue and warm yellow ochre color harmony, "
        "stillness and silence you can almost hear"
    ),
    (
        "Michelangelo Sistine Chapel fresco style: "
        "heroic muscular figures in twisting contrapposto poses, "
        "divine light from upper left casting dramatic shadows, "
        "Renaissance fresco color palette of terracotta, azure and gold, "
        "monumental scale and grandeur, figures straining with the weight of human destiny"
    ),
    (
        "Claude Monet Impressionist oil painting: "
        "rapid broken brushstrokes capturing light not form, "
        "canvas surface alive with dabs and flecks of pure unmixed color, "
        "soft atmospheric haze dissolving hard edges, "
        "complementary color vibration of orange and blue, violet and yellow, "
        "the feeling of standing in a garden at 8am in summer light"
    ),
    (
        "Gustav Klimt Art Nouveau oil and gold leaf painting: "
        "real gold leaf mosaic patterns consuming the background entirely, "
        "ornate Byzantine and Egyptian decorative motifs, "
        "figures emerging from abstract pattern like figures from wallpaper, "
        "rich jewel-tone palette of gold emerald sapphire and crimson, "
        "erotic symbolism wrapped in opulent surface beauty"
    ),
    (
        "Katsushika Hokusai ukiyo-e woodblock print: "
        "bold confident outlines of hand-carved woodblock, "
        "flat areas of Prussian blue and vermillion with zero shading, "
        "dynamic diagonal composition suggesting violent natural force, "
        "Mount Fuji as eternal witness in background, "
        "the graphic power of an image printed 10,000 times"
    ),
    (
        "Song Dynasty Chinese ink brush painting guohua style: "
        "sparse elegant brushwork leaving vast empty space as active element, "
        "mountain mist rendered in pale ink wash dissolving into white silk, "
        "three tonal values only: dark ink, mid wash, white ground, "
        "single gnarled pine or bamboo as focal point, "
        "the philosophy of emptiness made visible"
    ),
]

def get_random_style():
    return random.choice(ART_STYLES)

# ====================== HELPERS ======================
def is_sunday_hk():
    return (datetime.utcnow() + timedelta(hours=8)).weekday() == 6

def get_hk_time():
    return datetime.utcnow() + timedelta(hours=8)

def fix_hashtags(caption):
    lines = caption.strip().split('\n')
    fixed_lines = []
    for line in lines:
        words = line.split()
        if not any(w.startswith('#') for w in words):
            fixed_lines.append(line)
            continue
        fixed_words = []
        for word in words:
            clean = word.strip('.,!?')
            if (len(clean) > 1 and not clean.startswith('#')
                    and not clean.startswith('@')
                    and clean[0].isupper() and clean.isalnum()):
                fixed_words.append('#' + word)
            else:
                fixed_words.append(word)
        fixed_lines.append(' '.join(fixed_words))
    return '\n'.join(fixed_lines)

# ====================== INFOGRAPHIC PALETTES & TEXTURES ======================
PALETTES = [
    {
        "name": "wall_street",
        "BG": (8, 10, 16), "PANEL": (16, 20, 30), "BORDER": (36, 42, 62),
        "ACCENT": (40, 180, 100), "GOLD": (255, 210, 60),
        "MUTED": (130, 140, 165), "DIVIDER": (28, 34, 52),
    },
    {
        "name": "bull_run",
        "BG": (6, 14, 8), "PANEL": (12, 26, 16), "BORDER": (24, 60, 32),
        "ACCENT": (60, 220, 100), "GOLD": (180, 255, 120),
        "MUTED": (100, 160, 110), "DIVIDER": (16, 40, 22),
    },
    {
        "name": "bear_cave",
        "BG": (14, 8, 8), "PANEL": (28, 14, 14), "BORDER": (65, 28, 28),
        "ACCENT": (220, 70, 70), "GOLD": (255, 160, 100),
        "MUTED": (160, 110, 110), "DIVIDER": (45, 20, 20),
    },
    {
        "name": "midnight_blue",
        "BG": (5, 8, 28), "PANEL": (12, 16, 42), "BORDER": (30, 40, 90),
        "ACCENT": (80, 140, 255), "GOLD": (120, 200, 255),
        "MUTED": (100, 120, 180), "DIVIDER": (20, 28, 70),
    },
    {
        "name": "gold_standard",
        "BG": (16, 12, 6), "PANEL": (28, 22, 10), "BORDER": (70, 54, 20),
        "ACCENT": (220, 170, 40), "GOLD": (255, 215, 80),
        "MUTED": (160, 140, 90), "DIVIDER": (50, 38, 14),
    },
]

def _texture_circuit(draw, W, H, accent):
    rng = random.Random(13)
    for _ in range(120):
        x, y = rng.randint(0, W), rng.randint(0, H)
        length = rng.randint(20, 80)
        horiz = rng.random() > 0.5
        x2 = x + (length if horiz else 0)
        y2 = y + (0 if horiz else length)
        draw.line([(x, y), (x2, y2)], fill=(*accent, 14), width=1)
        draw.ellipse([x2-3, y2-3, x2+3, y2+3], fill=(*accent, 20))

def _texture_grid(draw, W, H, accent):
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(*accent, 12), width=1)
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(*accent, 12), width=1)

def _texture_dots(draw, W, H, accent):
    rng = random.Random(99)
    for x in range(30, W, 60):
        for y in range(30, H, 60):
            jx, jy = rng.randint(-8, 8), rng.randint(-8, 8)
            r = rng.randint(2, 5)
            draw.ellipse([x+jx-r, y+jy-r, x+jx+r, y+jy+r], fill=(*accent, 18))

def _texture_ticker(draw, W, H, accent):
    rng = random.Random(55)
    for _ in range(400):
        x = rng.randint(-100, W)
        y = rng.randint(0, H)
        length = rng.randint(30, 120)
        draw.line([(x, y), (x+length, y+length)], fill=(*accent, rng.randint(6, 16)), width=1)

TEXTURES = [_texture_circuit, _texture_grid, _texture_dots, _texture_ticker]

# ====================== INFOGRAPHIC ======================
def make_infographic(core_data, dynamic_data, date_str, one_liner="", weekly=False):
    W, H = 1080, 1440
    PAD = 60

    seed = int(get_hk_time().strftime("%Y%m%d"))
    rng = random.Random(seed)
    palette = rng.choice(PALETTES)
    texture_fn = rng.choice(TEXTURES)
    print(f"  🎨 Infographic: palette={palette['name']}")

    BG, PANEL, BORDER = palette["BG"], palette["PANEL"], palette["BORDER"]
    ACCENT, GOLD, MUTED, DIVIDER = palette["ACCENT"], palette["GOLD"], palette["MUTED"], palette["DIVIDER"]
    WHITE = (255, 255, 255)
    GREEN_UP = (60, 220, 100)   # US: green = up
    RED_DOWN  = (220, 70, 70)   # US: red = down

    img = Image.new("RGBA", (W, H), (*BG, 255))
    draw = ImageDraw.Draw(img)
    texture_fn(draw, W, H, ACCENT)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

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

    def cx(text, fnt, x1=0, x2=W):
        bb = draw.textbbox((0, 0), text, font=fnt)
        return x1 + (x2 - x1 - (bb[2] - bb[0])) // 2

    def rx(text, fnt, x2):
        bb = draw.textbbox((0, 0), text, font=fnt)
        return x2 - (bb[2] - bb[0])

    # ── Bull / bear triangle icon ─────────────────────────────────
    sp = core_data.get("S&P 500")
    market_up = sp['change_pct'] >= 0 if sp else True
    icon_color = GREEN_UP if market_up else RED_DOWN
    icx, icy, ir = W // 2, 85, 36
    if market_up:
        pts = [(icx, icy-ir), (icx-ir, icy+ir), (icx+ir, icy+ir)]
    else:
        pts = [(icx, icy+ir), (icx-ir, icy-ir), (icx+ir, icy-ir)]
    draw.polygon(pts, fill=icon_color)

    # ── Header ────────────────────────────────────────────────────
    y = 148
    mode_label = "WEEKLY RECAP" if weekly else "DAILY RECAP"
    f22 = font(22)
    draw.text((cx(mode_label, f22), y), mode_label, font=f22, fill=MUTED)

    y += 38
    f54b = font(54, bold=True)
    draw.text((cx("US MARKET", f54b), y), "US MARKET", font=f54b, fill=WHITE)

    y += 62
    f26 = font(26)
    draw.text((cx(date_str, f26), y), date_str, font=f26, fill=MUTED)

    # ── One-liner ─────────────────────────────────────────────────
    y += 48
    if one_liner:
        words = one_liner.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if len(test) <= 36:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        f30b = font(30, bold=True)
        for line in lines[:2]:
            draw.text((cx(line, f30b), y), line, font=f30b, fill=GOLD)
            y += 38
    else:
        y += 10

    # ── Accent divider ────────────────────────────────────────────
    y += 14
    draw.rectangle([PAD, y, W-PAD, y+2], fill=ACCENT)

    # ── Indices ───────────────────────────────────────────────────
    y += 24
    f22s = font(22)
    f32b = font(32, bold=True)
    f28  = font(28)
    f36b = font(36, bold=True)

    draw.text((PAD, y), "INDICES", font=f22s, fill=GOLD)
    y += 34

    for name, d in core_data.items():
        pct = d['change_pct']
        color = GREEN_UP if pct >= 0 else RED_DOWN
        arrow = "▲" if pct >= 0 else "▼"
        pct_str = f"{arrow} {abs(pct):.2f}%"

        draw.rounded_rectangle([PAD, y, W-PAD, y+80], radius=12, fill=PANEL, outline=BORDER, width=1)
        draw.text((PAD+24, y+14), name, font=f32b, fill=WHITE)
        price_str = f"{d['price']:.2f}" if name == "VIX" else f"{d['price']:,.0f}"
        draw.text((PAD+24, y+48), price_str, font=f28, fill=MUTED)
        draw.text((rx(pct_str, f36b, W-PAD-24), y+26), pct_str, font=f36b, fill=color)
        y += 88

    # ── Divider ───────────────────────────────────────────────────
    y += 10
    draw.rectangle([PAD, y, W-PAD, y+1], fill=DIVIDER)
    y += 22

    # ── Stocks in the news ────────────────────────────────────────
    if dynamic_data:
        draw.text((PAD, y), "STOCKS IN THE NEWS", font=f22s, fill=GOLD)
        y += 34

        sorted_stocks = sorted(
            dynamic_data.items(),
            key=lambda x: abs(x[1]['change_pct']),
            reverse=True
        )[:6]

        max_abs = max(abs(d['change_pct']) for _, d in sorted_stocks) or 1
        f28b = font(28, bold=True)
        f22r = font(22)
        bar_max = W - PAD*2 - 200

        for name, d in sorted_stocks:
            pct = d['change_pct']
            color = GREEN_UP if pct >= 0 else RED_DOWN
            arrow = "▲" if pct >= 0 else "▼"
            pct_str = f"{arrow} {abs(pct):.2f}%"
            bar_w = max(int(bar_max * (abs(pct) / max_abs)), 8)

            draw.rounded_rectangle([PAD, y, W-PAD, y+66], radius=10, fill=PANEL, outline=BORDER, width=1)
            bar_fill = (10, 50, 20) if pct >= 0 else (50, 10, 10)
            draw.rounded_rectangle([PAD, y, PAD+bar_w+60, y+66], radius=10, fill=bar_fill)

            short_name = name[:18] + ("…" if len(name) > 18 else "")
            draw.text((PAD+18, y+10), short_name, font=f28b, fill=WHITE)
            draw.text((PAD+18, y+40), f"${d['price']:,.2f}", font=f22r, fill=MUTED)
            draw.text((rx(pct_str, f28b, W-PAD-18), y+20), pct_str, font=f28b, fill=color)
            y += 72

    # ── Wave strip ────────────────────────────────────────────────
    wave_y = H - 110
    draw.rectangle([0, wave_y, W, wave_y+2], fill=DIVIDER)
    pts = [(int(i*W/60), wave_y+18+int(12*math.sin(i*math.pi*4/60))) for i in range(61)]
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=ACCENT, width=2)

    # ── Watermark ─────────────────────────────────────────────────
    f26b = font(26, bold=True)
    draw.text((cx("@mini_money.lab", f26b), H-56), "@mini_money.lab", font=f26b, fill=MUTED)

    path = "market_museum_infographic.jpg"
    img.save(path, "JPEG", quality=95)
    print(f"✅ Infographic saved ({palette['name']})")
    return path

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
            prev, last = hist['Close'].iloc[0], hist['Close'].iloc[-1]
            return {"price": round(last, 2), "change_pct": round((last-prev)/prev*100, 2)}
    except Exception:
        pass
    return None

def get_core_market_data(weekly=False):
    period = "5d" if weekly else "2d"
    return {
        name: data
        for name, sym in CORE_TICKERS.items()
        if (data := fetch_ticker_data(sym, period))
    }

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
            'Example: [{"name": "Apple", "ticker": "AAPL"}, {"name": "Tesla", "ticker": "TSLA"}]'
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️ Ticker extraction failed: {e}")
        return []

def get_dynamic_stock_data(extracted_tickers, weekly=False):
    period = "5d" if weekly else "2d"
    results = {}
    for item in extracted_tickers:
        name, symbol = item.get("name"), item.get("ticker")
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
    lines = [f"📊 Major Indices ({label}):"]
    for name, d in core_data.items():
        arrow = "▲" if d['change_pct'] > 0 else "▼"
        lines.append(f"  {arrow} {name}: {d['price']:,}  ({d['change_pct']:+.2f}%)")
    if dynamic_data:
        lines.append("")
        lines.append("🏢 Stocks In The News:")
        for name, d in sorted(dynamic_data.items(), key=lambda x: abs(x[1]['change_pct']), reverse=True):
            arrow = "▲" if d['change_pct'] > 0 else "▼"
            lines.append(f"  {arrow} {name}: ${d['price']:,}  ({d['change_pct']:+.2f}%)")
    return "\n".join(lines)

# ====================== NEWS ======================
def get_daily_news():
    news_items, seen = [], set()
    watch = ["^GSPC", "^IXIC", "NVDA", "AAPL", "MSFT", "TSLA", "META", "AMZN", "GOOGL"]
    for symbol in watch:
        try:
            for item in (yf.Ticker(symbol).news or [])[:4]:
                title = item.get('content', {}).get('title', '')
                if title and title not in seen:
                    seen.add(title)
                    news_items.append(title)
        except Exception as e:
            print(f"⚠️ News failed for {symbol}: {e}")
        if len(news_items) >= 20:
            break
    return news_items[:20]

def get_weekly_news():
    news_items, seen = [], set()
    watch = ["^GSPC", "^IXIC", "^DJI", "NVDA", "AAPL", "MSFT", "TSLA",
             "META", "AMZN", "GOOGL", "JPM", "GS", "BRK-B", "IBIT", "AMD", "NFLX", "DIS"]
    for symbol in watch:
        try:
            for item in (yf.Ticker(symbol).news or [])[:5]:
                title = item.get('content', {}).get('title', '')
                if title and title not in seen:
                    seen.add(title)
                    news_items.append(title)
        except Exception as e:
            print(f"⚠️ News failed for {symbol}: {e}")
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
            f"Today is {get_hk_time().strftime('%A, %B %d, %Y')} (Hong Kong Time). DAILY recap.\n\n"
            "1. Identify the single most interesting, dramatic, or important story of the day.\n"
            "2. Write a SHORT punchy market recap (3-5 sentences, flowing prose, no bullets).\n"
            "3. Write ONE punchy one-liner (max 8 words) capturing today's market mood. "
            "Witty and sharp — like a fortune cookie for traders. "
            "Examples: 'Nvidia sneezed. The whole market caught a cold.' / "
            "'Powell spoke. Bulls listened. Bears laughed.' / "
            "'Tesla crashed. Elon tweeted. Repeat.'\n"
            "4. Create a vivid creative image description:\n"
            "   - The SUBJECT must be the main company, person, or market event of the day. "
            "Name it explicitly — e.g. 'Jensen Huang holding a glowing GPU like a trophy', "
            "'the Federal Reserve building cracking open like an egg', "
            "'Elon Musk riding a Tesla rocket into a storm cloud'. "
            "The market story IS the image. Do not replace it with a generic abstract scene.\n"
            "   - Wrap the art style around that subject. Style serves the story.\n"
            "   - Mood matches the market: euphoric, panicked, chaotic, triumphant, absurd.\n"
            "   - NOT a literal chart. Symbolic, dramatic, or funny.\n"
            "5. Instagram caption: strong hook, 2-3 witty sentences, "
            "5-8 hashtags all starting with #, max 150 words.\n\n"
            f"Market Data:\n{market_data_str}\n\n"
            f"News:\n{news_text}\n\n"
            f"Art Style:\n{art_style}\n\n"
            'Return ONLY valid JSON: {"recap":"...","one_liner":"...","image_prompt":"...","ig_caption":"..."}'
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        r = json.loads(raw)
        return r.get("recap",""), r.get("one_liner",""), r.get("image_prompt",""), r.get("ig_caption","")
    except Exception as e:
        print(f"⚠️ Daily story failed: {e}")
        return (
            "Markets moved today with notable activity across major indices.",
            "Wall Street never sleeps.",
            f"A dramatic stock market scene. {art_style}.",
            "The market never sleeps. 📈\n#StockMarket #WallStreet #Investing"
        )

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
            f"WEEKLY RECAP for the week of {week_start} - {week_end} (Hong Kong Time).\n\n"
            "1. Identify the 2-3 biggest themes that defined this week.\n"
            "2. Write a punchy weekly market narrative (5-7 sentences, prose, no bullets). "
            "Capture the arc: how did it start, what happened, how did it end?\n"
            "3. Write ONE punchy one-liner (max 8 words) capturing this week's mood.\n"
            "4. Create a vivid weekly image — think movie poster for this week on Wall Street:\n"
            "   - The SUBJECT must be the dominant company, person, or theme of the week. Name it explicitly.\n"
            "   - Wrap the art style around that subject. Bold, symbolic, dramatic, shareable.\n"
            "5. Weekly IG caption: strong hook, 3-4 witty sentences, "
            "6-10 hashtags all starting with #, max 200 words.\n\n"
            f"Weekly Data:\n{market_data_str}\n\n"
            f"Headlines:\n{news_text}\n\n"
            f"Art Style:\n{art_style}\n\n"
            'Return ONLY valid JSON: {"recap":"...","one_liner":"...","image_prompt":"...","ig_caption":"..."}'
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        r = json.loads(raw)
        return r.get("recap",""), r.get("one_liner",""), r.get("image_prompt",""), r.get("ig_caption","")
    except Exception as e:
        print(f"⚠️ Weekly story failed: {e}")
        return (
            "It was an eventful week on Wall Street.",
            "Seven days. Zero chill.",
            f"A dramatic weekly stock market scene. {art_style}.",
            "Another week on Wall Street in the books. 📊\n#WeeklyRecap #StockMarket #WallStreet"
        )

# ====================== GENERATE AI IMAGE ======================
async def generate_image(image_prompt):
    print(f"🎨 Generating AI image...")
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
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    image_path = "market_museum_today.jpg"
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
        print(f"[{hk_time.strftime('%Y-%m-%d %H:%M')} HKT] 🚀 Market Museum — {mode}")

        print("📈 Fetching core market data...")
        core_data = get_core_market_data(weekly=sunday)

        print("📰 Fetching news...")
        news_items = get_weekly_news() if sunday else get_daily_news()
        print(f"  Got {len(news_items)} headlines")

        print("🔍 Extracting tickers from news...")
        extracted_tickers = extract_tickers_from_news(news_items)
        print(f"  Found {len(extracted_tickers)} companies")

        print("📊 Fetching dynamic stock data...")
        dynamic_data = get_dynamic_stock_data(extracted_tickers, weekly=sunday)

        art_style = get_random_style()
        print(f"🎨 Art style: {art_style[:80]}...")

        print("✍️ Generating story...")
        if sunday:
            recap, one_liner, image_prompt, ig_caption = generate_weekly_story(
                core_data, dynamic_data, news_items, art_style
            )
        else:
            recap, one_liner, image_prompt, ig_caption = generate_daily_story(
                core_data, dynamic_data, news_items, art_style
            )
        print(f"  One-liner: {one_liner}")
        print(f"  Recap: {recap[:80]}...")

        # Image 1 — AI artwork
        ai_image_path = await generate_image(image_prompt)
        if not ai_image_path:
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ No image generated today.")
            return

        # Image 2 — Infographic
        print("📊 Generating infographic...")
        date_str = hk_time.strftime('%B %d, %Y')
        infographic_path = make_infographic(
            core_data, dynamic_data, date_str, one_liner, weekly=sunday
        )

        # Telegram caption
        market_data_str = format_market_data(core_data, dynamic_data, weekly=sunday)
        header = f"🗓 Weekly Recap • {date_str}" if sunday else f"🎨 Market Museum Daily • {date_str}"
        tg_caption = (
            f"{header}\n\n{recap}\n\n{market_data_str}\n\n"
            "#MarketMuseum #StockMarket #WallStreet"
        )
        if len(tg_caption) > 1024:
            tg_caption = tg_caption[:1020] + "..."

        # Send both images as carousel
        await bot.send_media_group(
            chat_id=CHAT_ID,
            media=[
                InputMediaPhoto(media=open(ai_image_path, 'rb'), caption=tg_caption),
                InputMediaPhoto(media=open(infographic_path, 'rb')),
            ]
        )

        # IG caption as separate message
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

        print(f"✅ Success! {mode} — 2 images sent.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Error: {str(e)[:300]}")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
