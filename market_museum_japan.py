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

# ====================== JAPAN ART STYLES ======================
ART_STYLES = [
    (
        "Katsushika Hokusai ukiyo-e woodblock print masterpiece: "
        "hand-carved woodblock outlines — confident, slightly irregular, never digital-smooth — "
        "flat Prussian blue and vermillion with zero shading or gradients, "
        "bold diagonal composition suggesting violent natural force like a crashing wave or storm, "
        "Mount Fuji or a torii gate visible as a distant symbol of permanence, "
        "decorative wave or wind pattern as central visual element with foam tips like grasping claws, "
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
        "NO color, NO digital smoothing, RAW traditional ink on paper, "
        "monochrome only — jet black, mid grey, pale silver, white"
    ),
    (
        "Araki Hirohiko JoJo's Bizarre Adventure manga art style: "
        "impossibly dramatic contrapposto pose defying human anatomy for maximum visual impact, "
        "heavy baroque cross-hatching and fine stippling in shadow areas, "
        "fashion illustration meets Italian Renaissance painting meets shounen manga, "
        "intense screaming facial expression with highly detailed musculature, "
        "surreal gradient background shifting from deep magenta to electric teal, "
        "ornate decorative framing elements — stars, geometric patterns, speed lines"
    ),
    (
        "Osamu Tezuka Black Jack manga art style — mature era: "
        "bold confident ink lines with dramatic weight variation — thick silhouettes, razor-thin detail lines, "
        "stark chiaroscuro lighting — single harsh light source carving faces from darkness, "
        "the scarred face of Black Jack rendered with unflinching medical realism, "
        "surgical scenes depicted with clinical precision and visceral honesty, "
        "mid-century manga composition: dynamic panel energy compressed into single image, "
        "moral ambiguity written into every character's expression, "
        "Tezuka's mastery of human emotion — grief, rage, compassion in pure ink line"
    ),
    (
        "Katsuya Terada loose painterly illustration style: "
        "explosive gestural brushwork — ink and paint applied at speed, controlled chaos, "
        "figures built from overlapping transparent washes and decisive dark marks, "
        "anatomy deliberately distorted for visual power — elongated limbs, exaggerated gesture, "
        "rich layered color: deep crimson over raw sienna over black ink wash, "
        "the energy of the mark-making IS the subject — process visible in every stroke, "
        "adult dark fantasy aesthetic — powerful, raw, not for children, "
        "the confidence of someone who has drawn ten thousand figures and stopped caring about perfection"
    ),
    (
        "Katsuhiro Otomo AKIRA manga art style: "
        "hyper-detailed dystopian Neo-Tokyo cityscape — thousands of windows, "
        "highways spiraling into megacity darkness, neon kanji signs on wet rain-slicked streets, "
        "cinematic wide-angle shot of overwhelming urban scale under oppressive sky, "
        "psychic energy explosion as concentric rings of pure force obliterating matter, "
        "meticulous crosshatch shading building photorealistic depth from pure ink, "
        "every background figure individually drawn — no shortcuts, no repeats, "
        "the weight of a civilisation that built too fast and too carelessly"
    ),
    (
        "Kazuo Umezu Drifting Classroom manga horror art style: "
        "extreme close-up faces frozen in absolute primal terror — mouth wide open screaming, "
        "eyes bulging with whites fully visible, every facial muscle contorted, "
        "thick confident ink lines with heavy black shadow areas, "
        "children or figures in apocalyptic wasteland environments — collapsed structures, "
        "burning skies, desolate horizons stretching to nothing, "
        "the visual language of civilisation collapsing in real time, "
        "raw visceral horror that comes from situation not monster — existential dread made visible, "
        "stark high-contrast black and white with isolated areas of intense shadow"
    ),
    (
        "Junji Ito horror manga art style: "
        "obsessive spiral patterns consuming architecture, faces, and bodies — Uzumaki curse made visible, "
        "photorealistic ink rendering of ordinary scenes contaminated by one impossible wrongness, "
        "faces elongated and distorted by supernatural forces — jaw unhinged, eyes multiplied, "
        "extreme fine-line crosshatching creating skin texture of almost photographic quality, "
        "ordinary Japanese suburban setting — telephone poles, narrow streets, wooden houses — "
        "made unbearable by one detail that should not exist, "
        "the horror of transformation: bodies becoming geometry, geometry becoming hunger, "
        "black ink used with surgical precision to make the impossible look inevitable"
    ),
    (
        "Naoki Urasawa Monster and 20th Century Boys manga art style: "
        "cinematic realistic portraiture — faces drawn with actor-level psychological specificity, "
        "every wrinkle and shadow tells a story of what this person has survived, "
        "thriller composition: extreme close-up eye reflecting something terrible, "
        "dramatic noir lighting — single source casting half the face into darkness, "
        "European city environments rendered with architectural precision — "
        "rain-wet cobblestones, gothic hospital corridors, Cold War apartment blocks, "
        "the tension of a scene where nothing has happened yet but everything is about to, "
        "restrained ink line quality — realism over expressionism, "
        "the most frightening thing is a human face you cannot read"
    ),
    (
        "Yoshitaka Amano Final Fantasy concept art style: "
        "ethereal figures dissolving at edges into trails of gold ink and watercolour wash, "
        "extreme elongation of human form — impossibly tall and thin, draped in flowing fabric, "
        "loose gestural ink lines that suggest rather than define — a figure implied not stated, "
        "real gold leaf or metallic ink areas catching light against dark atmospheric washes, "
        "art nouveau decorative elements: organic curves, feathers, crystals, celestial motifs, "
        "deep jewel-tone background washes — midnight blue, deep violet, burnt amber, "
        "the boundary between figure and background intentionally dissolved, "
        "museum-quality fine art that happens to depict fantasy — not illustration, painting"
    ),
    (
        "Hayao Miyazaki Studio Ghibli hand-painted animation background art style: "
        "soft luminous watercolour washes — greens and blues glowing with inner light, "
        "lush natural environments: ancient forest, rolling hills, sky castle in clouds, "
        "warm afternoon sunlight filtering through leaves as dappled pools of gold, "
        "hand-painted texture — visible brushwork, no digital smoothness, "
        "the sky as protagonist — clouds with volume and personality, golden hour light, "
        "nostalgic warmth — the feeling of a summer afternoon that existed before you were born"
    ),
    (
        "Yoshitomo Nara contemporary art style: "
        "single lone big-eyed child figure — deceptively innocent face hiding dark emotion, "
        "flat matte acrylic paint with deliberate rough brushwork, "
        "limited pastel palette with ONE jarring dark accent color, "
        "child holding something unexpected: knife, cigarette, sign, wilted flower, "
        "NO gradients, NO realism, deliberately naive yet deeply unsettling"
    ),
    (
        "Takashi Murakami superflat contemporary art style: "
        "hyper-flat zero-perspective composition — no shadows, no depth, pure 2D, "
        "explosive psychedelic palette: hot pink, electric yellow, acid green, cobalt blue, "
        "smiling flower characters with smiley-face centers repeated like wallpaper, "
        "obsessive symmetric pattern repetition consuming entire canvas, "
        "pop culture and centuries of Japanese art history colliding in one image"
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
        "name": "rising_sun",
        "BG": (10, 10, 18), "PANEL": (20, 22, 35), "BORDER": (40, 44, 68),
        "ACCENT": (220, 40, 40), "GOLD": (255, 200, 60),
        "MUTED": (140, 145, 170), "DIVIDER": (35, 38, 58),
    },
    {
        "name": "tokyo_neon",
        "BG": (5, 8, 28), "PANEL": (12, 16, 42), "BORDER": (30, 40, 90),
        "ACCENT": (60, 120, 255), "GOLD": (100, 220, 255),
        "MUTED": (100, 120, 180), "DIVIDER": (20, 28, 70),
    },
    {
        "name": "sakura",
        "BG": (18, 10, 16), "PANEL": (32, 18, 28), "BORDER": (72, 38, 58),
        "ACCENT": (220, 100, 140), "GOLD": (255, 180, 200),
        "MUTED": (160, 120, 140), "DIVIDER": (50, 28, 42),
    },
    {
        "name": "forest_ink",
        "BG": (8, 16, 14), "PANEL": (14, 28, 24), "BORDER": (28, 60, 50),
        "ACCENT": (40, 180, 120), "GOLD": (160, 240, 180),
        "MUTED": (100, 150, 130), "DIVIDER": (20, 45, 38),
    },
    {
        "name": "edo_gold",
        "BG": (16, 12, 6), "PANEL": (28, 22, 10), "BORDER": (70, 54, 20),
        "ACCENT": (220, 160, 30), "GOLD": (255, 210, 80),
        "MUTED": (160, 140, 90), "DIVIDER": (50, 38, 14),
    },
]

def _texture_washi(draw, W, H, accent):
    rng = random.Random(42)
    for _ in range(600):
        x, y = rng.randint(0, W), rng.randint(0, H)
        length = rng.randint(8, 40)
        angle = rng.uniform(0, math.pi)
        x2 = int(x + length * math.cos(angle))
        y2 = int(y + length * math.sin(angle))
        draw.line([(x, y), (x2, y2)], fill=(*accent, rng.randint(6, 18)), width=1)

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

def _texture_ink(draw, W, H, accent):
    rng = random.Random(7)
    for _ in range(18):
        x, y = rng.randint(-100, W), rng.randint(-100, H + 100)
        length = rng.randint(80, 300)
        draw.line(
            [(x, y), (int(x + length * 0.7), int(y + length))],
            fill=(*accent, rng.randint(10, 28)),
            width=rng.randint(1, 4)
        )

TEXTURES = [_texture_washi, _texture_grid, _texture_dots, _texture_ink]

# ====================== INFOGRAPHIC ======================
def make_infographic(core_data, dynamic_data, date_str, one_liner="", weekly=False):
    W, H = 1080, 1440
    PAD = 60

    # Seed by date so palette/texture are consistent if re-run same day
    seed = int(get_hk_time().strftime("%Y%m%d"))
    rng = random.Random(seed)
    palette = rng.choice(PALETTES)
    texture_fn = rng.choice(TEXTURES)
    print(f"  🎨 Infographic: palette={palette['name']}")

    BG, PANEL, BORDER = palette["BG"], palette["PANEL"], palette["BORDER"]
    ACCENT, GOLD, MUTED, DIVIDER = palette["ACCENT"], palette["GOLD"], palette["MUTED"], palette["DIVIDER"]
    WHITE = (255, 255, 255)
    RED_UP, BLUE_DOWN = (255, 80, 80), (80, 160, 255)  # Japan: red=up, blue=down

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

    # Rising sun
    scx, scy, sr = W // 2, 90, 38
    for i in range(12):
        a = math.radians(i * 30)
        draw.line(
            [(scx + int((sr+10)*math.cos(a)), scy + int((sr+10)*math.sin(a))),
             (scx + int((sr+26)*math.cos(a)), scy + int((sr+26)*math.sin(a)))],
            fill=ACCENT, width=2
        )
    draw.ellipse([scx-sr, scy-sr, scx+sr, scy+sr], fill=ACCENT)

    # Header
    y = 148
    mode_label = "WEEKLY RECAP" if weekly else "DAILY RECAP"
    f22 = font(22)
    draw.text((cx(mode_label, f22), y), mode_label, font=f22, fill=MUTED)

    y += 38
    f54b = font(54, bold=True)
    draw.text((cx("JAPAN MARKET", f54b), y), "JAPAN MARKET", font=f54b, fill=WHITE)

    y += 62
    f26 = font(26)
    draw.text((cx(date_str, f26), y), date_str, font=f26, fill=MUTED)

    # One-liner
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

    # Accent divider
    y += 14
    draw.rectangle([PAD, y, W-PAD, y+2], fill=ACCENT)

    # Indices
    y += 24
    f22s = font(22)
    draw.text((PAD, y), "INDICES", font=f22s, fill=GOLD)
    y += 34

    f32b = font(32, bold=True)
    f28  = font(28)
    f36b = font(36, bold=True)

    for name, d in core_data.items():
        pct = d['change_pct']
        color = RED_UP if pct >= 0 else BLUE_DOWN
        arrow = "▲" if pct >= 0 else "▼"
        pct_str = f"{arrow} {abs(pct):.2f}%"
        draw.rounded_rectangle([PAD, y, W-PAD, y+80], radius=12, fill=PANEL, outline=BORDER, width=1)
        draw.text((PAD+24, y+14), name, font=f32b, fill=WHITE)
        price_str = f"¥{d['price']:,.2f}" if name == "USD/JPY" else f"{d['price']:,.0f}"
        draw.text((PAD+24, y+48), price_str, font=f28, fill=MUTED)
        draw.text((rx(pct_str, f36b, W-PAD-24), y+26), pct_str, font=f36b, fill=color)
        y += 88

    # Divider
    y += 10
    draw.rectangle([PAD, y, W-PAD, y+1], fill=DIVIDER)
    y += 22

    # Stocks in the news
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
            color = RED_UP if pct >= 0 else BLUE_DOWN
            arrow = "▲" if pct >= 0 else "▼"
            pct_str = f"{arrow} {abs(pct):.2f}%"
            bar_w = max(int(bar_max * (abs(pct) / max_abs)), 8)

            draw.rounded_rectangle([PAD, y, W-PAD, y+66], radius=10, fill=PANEL, outline=BORDER, width=1)

            # Tinted fill bar — always red=up, blue=down (Japan convention)
            bar_fill = (80, 20, 20) if pct >= 0 else (10, 30, 70)
            draw.rounded_rectangle([PAD, y, PAD+bar_w+60, y+66], radius=10, fill=bar_fill)

            short_name = name[:18] + ("…" if len(name) > 18 else "")
            draw.text((PAD+18, y+10), short_name, font=f28b, fill=WHITE)
            draw.text((PAD+18, y+40), f"¥{d['price']:,.0f}", font=f22r, fill=MUTED)
            draw.text((rx(pct_str, f28b, W-PAD-18), y+20), pct_str, font=f28b, fill=color)
            y += 72

    # Wave strip
    wave_y = H - 110
    draw.rectangle([0, wave_y, W, wave_y+2], fill=DIVIDER)
    pts = [(int(i*W/60), wave_y+18+int(12*math.sin(i*math.pi*4/60))) for i in range(61)]
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=ACCENT, width=2)

    # Watermark
    f26b = font(26, bold=True)
    draw.text((cx("@mini_money.lab", f26b), H-56), "@mini_money.lab", font=f26b, fill=MUTED)

    path = "market_museum_japan_infographic.jpg"
    img.save(path, "JPEG", quality=95)
    print(f"✅ Infographic saved ({palette['name']})")
    return path

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

def get_japan_news(weekly=False):
    news_items, seen = [], set()
    limit, fetch_per = (30, 5) if weekly else (20, 4)
    for symbol in NEWS_SEED_SYMBOLS:
        try:
            for item in (yf.Ticker(symbol).news or [])[:fetch_per]:
                title = item.get('content', {}).get('title', '')
                if title and title not in seen:
                    seen.add(title)
                    news_items.append(title)
        except Exception as e:
            print(f"  ⚠️ News failed for {symbol}: {e}")
        if len(news_items) >= limit:
            break
    return news_items[:limit]

def extract_japan_tickers_from_news(news_items):
    try:
        prompt = (
            "From these Japan financial news headlines, extract ONLY Japanese-listed companies.\n"
            "Return ONLY valid JSON array with 'name' and 'ticker' fields.\n"
            "IMPORTANT: Only include stocks listed on the Tokyo Stock Exchange (TSE) with .T suffix.\n"
            "Do NOT include US stocks like Nvidia, Tesla, Apple, etc — even if mentioned in the headlines.\n"
            "Common TSE tickers: Toyota=7203.T, Sony=6758.T, SoftBank=9984.T, Nintendo=7974.T, "
            "Fast Retailing=9983.T, Tokyo Electron=8035.T, Keyence=6861.T, "
            "Mitsubishi UFJ=8306.T, Honda=7267.T, Panasonic=6752.T, KDDI=9433.T, "
            "Hitachi=6501.T, Renesas=6723.T, Shin-Etsu=4063.T, Daikin=6367.T, "
            "Recruit=6098.T, Sumitomo Mitsui=8316.T, Mizuho=8411.T, Tokio Marine=8766.T.\n"
            "Skip indices. Skip if ticker unknown. Max 10. Return only JSON.\n\n"
            f"Headlines:\n" + "\n".join(f"- {n}" for n in news_items)
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        extracted = json.loads(raw)
        print(f"  Extracted {len(extracted)} tickers")
        return extracted
    except Exception as e:
        print(f"  ⚠️ Ticker extraction failed: {e}")
        return []

def get_dynamic_stock_data(extracted_tickers, weekly=False):
    period = "5d" if weekly else "2d"
    tickers_to_use = extracted_tickers or JAPAN_FALLBACK_TICKERS
    if not extracted_tickers:
        print("  ℹ️ Using fallback tickers")
    results = {}
    for item in tickers_to_use:
        name, symbol = item.get("name"), item.get("ticker")
        if not name or not symbol:
            continue
        # Safety: skip non-TSE stocks (US stocks that slipped through)
        if not symbol.endswith(".T") and symbol not in [t["ticker"] for t in JAPAN_FALLBACK_TICKERS]:
            print(f"  ⏭️ Skipped non-TSE: {name} ({symbol})")
            continue
        data = fetch_ticker_data(symbol, period=period)
        if data:
            results[name] = data
            print(f"  ✅ {name}: {data['change_pct']:+.2f}%")
        else:
            print(f"  ⚠️ Skipped {name}")
    return results

def format_market_data(core_data, dynamic_data, weekly=False):
    label = "Weekly Change" if weekly else "Daily Change"
    lines = [f"📊 Japan Indices ({label}):"]
    for name, d in core_data.items():
        arrow = "▲" if d['change_pct'] > 0 else "▼"
        price = f"¥{d['price']:,.2f}" if name == "USD/JPY" else f"{d['price']:,.0f}"
        lines.append(f"  {arrow} {name}: {price}  ({d['change_pct']:+.2f}%)")
    if dynamic_data:
        lines.append("")
        lines.append("🏢 Stocks In The News (TSE):")
        for name, d in sorted(dynamic_data.items(), key=lambda x: abs(x[1]['change_pct']), reverse=True):
            arrow = "▲" if d['change_pct'] > 0 else "▼"
            lines.append(f"  {arrow} {name}: ¥{d['price']:,.0f}  ({d['change_pct']:+.2f}%)")
    return "\n".join(lines)

# ====================== GEMINI: STORIES ======================
def generate_daily_story(core_data, dynamic_data, news_items, art_style):
    try:
        prompt = (
            "You are a creative financial art director for a viral daily Japan market project.\n"
            f"Today is {get_hk_time().strftime('%A, %B %d, %Y')} HKT. DAILY recap of TSE.\n\n"
            "1. Find the most interesting story — stock move, yen, BOJ, earnings, anything notable.\n"
            "2. Write a SHORT punchy Japan market recap (3-5 sentences, prose, no bullets).\n"
            "3. Write ONE punchy one-liner (max 8 words) capturing today's market mood. "
            "Witty and sharp — like a fortune cookie for traders. "
            "Examples: 'The yen blinked and Toyota didn't.' / 'SoftBank dreamed. Markets listened.'\n"
            "4. Create a vivid creative image description:\n"
            "   - The SUBJECT must be the main company, person, or market event of the day. "
            "Always name the subject explicitly — e.g. 'SoftBank's Masayoshi Son', 'a Toyota factory', "
            "'the Bank of Japan governor', 'a Nintendo game cartridge raining from the sky'. "
            "The market story IS the image. Do not replace it with a generic landscape or abstract scene.\n"
            "   - Then wrap the art style around that subject. The style serves the story, not the other way around.\n"
            "   - Japanese cultural setting is welcome when it fits naturally — "
            "Tokyo skyline, Mount Fuji, bullet train, neon Shibuya — but only as backdrop, not the main focus.\n"
            "   - Be dramatic, funny, or symbolic. Make it unmistakably about today's market event.\n"
            "5. Instagram caption: strong hook, 2-3 witty sentences, 5-8 hashtags (all #), "
            "at least 2 Japan hashtags, max 150 words.\n\n"
            f"Market Data:\n{format_market_data(core_data, dynamic_data)}\n\n"
            f"News:\n" + "\n".join(f"- {n}" for n in news_items) + f"\n\n"
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
            "Tokyo markets moved today with notable activity.",
            "Tokyo never sleeps.",
            f"Dramatic Tokyo stock market scene. {art_style}.",
            "Tokyo never sleeps. 📈\n#Nikkei #TokyoStocks #日経平均"
        )

def generate_weekly_story(core_data, dynamic_data, news_items, art_style):
    try:
        hk_now = get_hk_time()
        week_start = (hk_now - timedelta(days=6)).strftime('%B %d')
        week_end = hk_now.strftime('%B %d, %Y')
        prompt = (
            "You are a creative financial art director for a viral weekly Japan market project.\n"
            f"WEEKLY RECAP for TSE, {week_start} - {week_end}.\n\n"
            "1. Identify the 2-3 biggest themes of the week.\n"
            "2. Write a punchy weekly Japan narrative (5-7 sentences, prose, no bullets).\n"
            "3. Write ONE punchy one-liner (max 8 words) capturing this week's mood.\n"
            "4. Create a vivid weekly image:\n"
            "   - The SUBJECT must be the dominant company, person, or theme of the week. "
            "Name it explicitly — e.g. 'Toyota vs the rising yen', 'SoftBank's rollercoaster week', "
            "'the Bank of Japan shaking the market'. The week's story IS the image.\n"
            "   - Wrap the art style around that subject. Style serves the story.\n"
            "   - Japanese cultural setting welcome as backdrop but not the main focus.\n"
            "   - Think Japanese weekly magazine cover — bold, specific, unmistakably this week.\n"
            "5. Weekly IG caption: strong hook, 3-4 witty sentences, 6-10 hashtags (all #), "
            "Japan hashtags included, max 200 words.\n\n"
            f"Weekly Data:\n{format_market_data(core_data, dynamic_data, weekly=True)}\n\n"
            f"Headlines:\n" + "\n".join(f"- {n}" for n in news_items) + f"\n\n"
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
            "It was an eventful week on the Tokyo Stock Exchange.",
            "Seven days. Zero chill.",
            f"Dramatic weekly Japan market scene. {art_style}.",
            "Another week in Tokyo. 📊\n#WeeklyRecap #Nikkei #JapanStocks #日経平均"
        )

# ====================== GENERATE AI IMAGE ======================
async def generate_image(image_prompt):
    print(f"🎨 Generating AI image...")
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

        print("📈 Fetching index data...")
        core_data = get_core_market_data(weekly=sunday)

        print("📰 Fetching news...")
        news_items = get_japan_news(weekly=sunday)
        print(f"  Got {len(news_items)} headlines")

        print("🔍 Extracting tickers from news...")
        extracted_tickers = extract_japan_tickers_from_news(news_items)

        print("📊 Fetching stock data...")
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
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ Japan: No AI image generated.")
            return

        # Image 2 — Infographic
        print("📊 Generating infographic...")
        date_str = hk_time.strftime('%B %d, %Y')
        infographic_path = make_infographic(
            core_data, dynamic_data, date_str, one_liner, weekly=sunday
        )

        # Telegram caption
        market_data_str = format_market_data(core_data, dynamic_data, weekly=sunday)
        header = f"🗾 Japan Weekly Recap • {date_str}" if sunday else f"🗾 Japan Market Museum • {date_str}"
        tg_caption = f"{header}\n\n{recap}\n\n{market_data_str}\n\n#MarketMuseum #Nikkei #JapanStocks"
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
            "📱 *IG Caption (Japan Weekly) — copy & paste ready:*"
            if sunday else
            "📱 *IG Caption (Japan) — copy & paste ready:*"
        )
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"{ig_label}\n\n{ig_caption}",
            parse_mode="Markdown"
        )

        # Send style + scene prompt info
        style_short = art_style[:100] + "..." if len(art_style) > 100 else art_style
        await bot.send_message(
            chat_id=CHAT_ID,
            text=(
                f"🎨 Japan Style Used:\n{style_short}\n\n"
                f"🎬 Scene Prompt:\n{image_prompt}"
            )
        )

        print(f"✅ Japan {mode} — 2 images sent.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Japan Error: {str(e)[:300]}")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
