import os
import random
import json
import math
import requests
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

# ====================== PHOTOGRAPHY STYLES ======================
PHOTO_STYLES = [
    (
        "High-fashion editorial photography by Tim Walker: "
        "surreal fantastical set design with impossible scale — giant objects, tiny people, "
        "dreamlike color-saturated world that feels like stepping inside a painting, "
        "couture-level styling on every element, dramatic theatrical lighting, "
        "Vogue Italia double-page spread energy, shot on medium format film, "
        "every surface textured, every shadow deliberate, absurdly beautiful"
    ),
    (
        "Cinematic film still in the style of Denis Villeneuve and Roger Deakins: "
        "anamorphic widescreen framing with shallow depth of field, "
        "single dominant color wash — teal, amber, or desaturated blue — grading the entire frame, "
        "silhouetted figure against vast atmospheric landscape or architecture, "
        "volumetric fog or dust particles catching directional light, "
        "IMAX-scale grandeur compressed into a still frame, "
        "the feeling of an epic sci-fi film frozen at its most pivotal moment"
    ),
    (
        "Surrealist conceptual photography by Erik Johansson: "
        "photorealistic impossible scene — physics-defying architecture, gravity reversed, "
        "objects transforming mid-air into something else entirely, "
        "seamless compositing so perfect you question reality, "
        "golden hour natural light making the impossible feel mundane, "
        "clean Scandinavian aesthetic — minimal clutter, maximum impact, "
        "the kind of image that takes 30 seconds to understand and then blows your mind"
    ),
    (
        "Cyberpunk neon street photography — Tokyo meets Taipei at 2am: "
        "rain-slicked streets reflecting neon Chinese and Japanese signage, "
        "deep teal shadows and hot pink / electric magenta highlights, "
        "lone figure in silhouette against wall of glowing advertisements, "
        "steam rising from street vents, bokeh orbs from distant lights, "
        "shot on 35mm f/1.4 wide open — razor-thin focus plane, "
        "Blade Runner meets night market energy"
    ),
    (
        "High-speed frozen motion studio photography: "
        "object captured at the exact moment of explosion, shatter, or splash — "
        "fragments suspended in mid-air with crystalline sharpness, "
        "pure black background, single strobe flash from 45 degrees, "
        "every droplet, shard, and particle frozen in time, "
        "hyper-real detail impossible to see with the naked eye, "
        "the violence of destruction made beautiful and precise"
    ),
    (
        "Macro extreme close-up photography — semiconductor and circuit board aesthetic: "
        "microscopic world of silicon wafers, gold wire bonds, chip die surfaces, "
        "iridescent rainbow refraction patterns on semiconductor surfaces, "
        "depth of field measured in microns — razor-sharp subject dissolving into creamy bokeh, "
        "clinical precision lighting revealing textures invisible to the human eye, "
        "the hidden beauty of the technology that powers the world, "
        "shot at 5:1 magnification with focus stacking"
    ),
    (
        "Annie Leibovitz dramatic portrait photography: "
        "single powerful figure lit by one dominant light source — Rembrandt triangle on cheek, "
        "rich deep shadows consuming three-quarters of the frame, "
        "subject's expression carrying the entire emotional weight — intensity, exhaustion, triumph, "
        "environmental portrait with carefully chosen symbolic props and setting, "
        "medium format film grain visible at full resolution, "
        "the kind of portrait that defines a person's legacy"
    ),
    (
        "Double exposure composite photography — analog film technique: "
        "two exposures blended in-camera — a human silhouette filled with cityscape, "
        "or a face dissolving into nature, machinery, or data visualization, "
        "ethereal transparency where two worlds overlap, "
        "moody desaturated color palette with one accent color bleeding through, "
        "organic film grain and light leak artifacts adding warmth, "
        "the poetic collision of two realities in one frame"
    ),
    (
        "Wes Anderson symmetrical composition photography: "
        "obsessively centered framing with perfect bilateral symmetry, "
        "pastel color palette — dusty pink, mint green, pale yellow, powder blue, "
        "miniature-like quality with deep depth of field showing every detail equally sharp, "
        "retro-futurist set design mixing 1960s and 2030s aesthetics, "
        "deadpan subjects posed like museum exhibits, "
        "whimsical precision that feels both absurd and deeply intentional"
    ),
    (
        "Dark moody product photography — luxury brand campaign aesthetic: "
        "single object on reflective black surface, "
        "dramatic rim lighting creating glowing edges against pure darkness, "
        "smoke, mist, or particles floating in controlled beams of light, "
        "obsessive attention to surface texture — metal, glass, liquid, fabric, "
        "shot with a 100mm macro at f/2.8 for buttery background separation, "
        "the object feels like it costs ten thousand dollars"
    ),
    (
        "Long exposure light painting photography at night: "
        "trails of colored light sweeping through darkness in choreographed patterns, "
        "steel wool sparks creating golden spiral trails, "
        "moving LED lights writing words or shapes in mid-air, "
        "star trails or car headlight streaks showing the passage of time, "
        "tripod-sharp static elements contrasting with fluid light motion, "
        "30-second exposure turning chaos into ethereal beauty"
    ),
    (
        "Tilt-shift miniature effect photography: "
        "real city scene or landscape photographed to look like a tiny model — "
        "extreme selective focus creating narrow band of sharpness, "
        "oversaturated toylike colors, people looking like figurines, "
        "aerial or elevated vantage point looking down at the scene, "
        "the uncanny feeling of gods looking down at a diorama, "
        "shot with Lensbaby or TS-E 24mm tilt-shift lens"
    ),
]

def get_random_style():
    return random.choice(PHOTO_STYLES)

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
# Taiwan-specific palettes — teal/cyan tech-forward, different from US/Japan
PALETTES = [
    {
        "name": "tsmc_teal",
        "BG": (4, 16, 22), "PANEL": (8, 28, 36), "BORDER": (16, 60, 78),
        "ACCENT": (0, 200, 200), "GOLD": (80, 255, 220),
        "MUTED": (80, 140, 155), "DIVIDER": (10, 40, 52),
    },
    {
        "name": "taipei_violet",
        "BG": (14, 6, 22), "PANEL": (24, 12, 38), "BORDER": (54, 28, 80),
        "ACCENT": (160, 80, 240), "GOLD": (200, 150, 255),
        "MUTED": (130, 100, 165), "DIVIDER": (36, 18, 56),
    },
    {
        "name": "silicon_mint",
        "BG": (6, 18, 16), "PANEL": (10, 30, 26), "BORDER": (24, 66, 56),
        "ACCENT": (50, 220, 160), "GOLD": (120, 255, 200),
        "MUTED": (80, 150, 130), "DIVIDER": (14, 44, 36),
    },
    {
        "name": "night_market",
        "BG": (18, 8, 4), "PANEL": (32, 16, 8), "BORDER": (75, 35, 15),
        "ACCENT": (255, 120, 40), "GOLD": (255, 180, 80),
        "MUTED": (170, 120, 80), "DIVIDER": (52, 26, 10),
    },
    {
        "name": "ocean_deep",
        "BG": (4, 10, 24), "PANEL": (8, 18, 44), "BORDER": (18, 40, 96),
        "ACCENT": (40, 120, 255), "GOLD": (100, 180, 255),
        "MUTED": (80, 110, 180), "DIVIDER": (12, 26, 68),
    },
]

def _texture_chipboard(draw, W, H, accent):
    """Circuit board / semiconductor traces."""
    rng = random.Random(77)
    for _ in range(150):
        x, y = rng.randint(0, W), rng.randint(0, H)
        length = rng.randint(15, 60)
        horiz = rng.random() > 0.5
        x2 = x + (length if horiz else 0)
        y2 = y + (0 if horiz else length)
        draw.line([(x, y), (x2, y2)], fill=(*accent, 16), width=1)
        if rng.random() > 0.6:
            draw.rectangle([x2-2, y2-2, x2+2, y2+2], fill=(*accent, 22))

def _texture_wave(draw, W, H, accent):
    """Ocean wave lines — Taiwan island feel."""
    rng = random.Random(33)
    for i in range(20):
        y_base = rng.randint(0, H)
        pts = []
        for x in range(0, W, 8):
            y = y_base + int(15 * math.sin((x + i * 40) * math.pi / 120))
            pts.append((x, y))
        for j in range(len(pts) - 1):
            draw.line([pts[j], pts[j+1]], fill=(*accent, 10), width=1)

def _texture_hex(draw, W, H, accent):
    """Hexagonal grid — tech/data aesthetic."""
    rng = random.Random(44)
    size = 36
    for row in range(0, H + size, int(size * 1.5)):
        offset = size if (row // int(size * 1.5)) % 2 else 0
        for col in range(offset, W + size, int(size * 1.73)):
            cx_h, cy_h = col, row
            pts = []
            for k in range(6):
                angle = math.radians(60 * k - 30)
                pts.append((cx_h + int(size * 0.5 * math.cos(angle)),
                            cy_h + int(size * 0.5 * math.sin(angle))))
            if rng.random() > 0.5:
                for k in range(len(pts)):
                    draw.line([pts[k], pts[(k+1)%6]], fill=(*accent, 12), width=1)

def _texture_rain(draw, W, H, accent):
    """Diagonal rain lines — Taipei monsoon feel."""
    rng = random.Random(88)
    for _ in range(300):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        length = rng.randint(12, 45)
        draw.line([(x, y), (x + length//3, y + length)],
                  fill=(*accent, rng.randint(8, 18)), width=1)

TEXTURES = [_texture_chipboard, _texture_wave, _texture_hex, _texture_rain]

# ====================== INFOGRAPHIC ======================
# Common Taiwan stocks — English + Chinese names for display
STOCK_NAMES_ZH = {
    "TSMC": "台積電",
    "Taiwan Semiconductor": "台積電",
    "Hon Hai": "鴻海",
    "Foxconn": "鴻海",
    "MediaTek": "聯發科",
    "Delta Electronics": "台達電",
    "Delta": "台達電",
    "Cathay Financial": "國泰金",
    "Cathay": "國泰金",
    "Fubon Financial": "富邦金",
    "Fubon": "富邦金",
    "CTBC Financial": "中信金",
    "CTBC": "中信金",
    "Mega Financial": "兆豐金",
    "Uni-President": "統一",
    "Formosa Plastics": "台塑",
    "Nan Ya Plastics": "南亞",
    "ASE Technology": "日月光",
    "ASE": "日月光",
    "Quanta Computer": "廣達",
    "Quanta": "廣達",
    "Pegatron": "和碩",
    "Largan Precision": "大立光",
    "Largan": "大立光",
    "Novatek": "聯詠",
    "Realtek": "瑞昱",
    "Wistron": "緯創",
    "Inventec": "英業達",
    "Compal": "仁寶",
    "Acer": "宏碁",
    "ASUS": "華碩",
    "Evergreen Marine": "長榮海運",
    "Evergreen": "長榮海運",
    "China Steel": "中鋼",
    "UMC": "聯電",
    "Powerchip": "力積電",
    "Nanya Technology": "南亞科",
    "Nanya": "南亞科",
    "Winbond": "華邦電",
    "E.SUN Financial": "玉山金",
    "E.SUN": "玉山金",
    "SinoPac Financial": "永豐金",
    "SinoPac": "永豐金",
    "Chunghwa Telecom": "中華電",
    "Far EasTone": "遠傳",
    "Taiwan Mobile": "台灣大",
    "Shin Kong Financial": "新光金",
    "Yuanta Financial": "元大金",
    "First Financial": "第一金",
    "Hua Nan Financial": "華南金",
    "Taishin Financial": "台新金",
}

def get_zh_name(name):
    """Fuzzy lookup — check if any dict key appears inside the stock name."""
    # Exact match first
    if name in STOCK_NAMES_ZH:
        return STOCK_NAMES_ZH[name]
    # Check if stock name contains any key (longest match first)
    for key in sorted(STOCK_NAMES_ZH.keys(), key=len, reverse=True):
        if key.lower() in name.lower():
            return STOCK_NAMES_ZH[key]
    return ""

def make_infographic(core_data, dynamic_data, foreign_flow_str, date_str, one_liner="", weekly=False):
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
    GREEN_UP = (60, 220, 100)
    RED_DOWN  = (220, 70, 70)

    img = Image.new("RGBA", (W, H), (*BG, 255))
    draw = ImageDraw.Draw(img)
    texture_fn(draw, W, H, ACCENT)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    def font(size, bold=False):
        # CJK fonts first (for Chinese characters), then Latin fallbacks
        candidates = (
            ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
             "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Bold.otf",
             "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
            if bold else
            ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
             "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
             "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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

    # ── Taiwan diamond icon (semiconductor shape) ─────────────────
    dcx, dcy, dr = W // 2, 82, 32
    draw.polygon([(dcx, dcy-dr), (dcx+dr, dcy), (dcx, dcy+dr), (dcx-dr, dcy)], fill=ACCENT)
    # small inner diamond
    draw.polygon([(dcx, dcy-dr//2), (dcx+dr//2, dcy), (dcx, dcy+dr//2), (dcx-dr//2, dcy)],
                 fill=BG, outline=ACCENT, width=1)

    # ── Header ────────────────────────────────────────────────────
    y = 138
    mode_label = "WEEKLY RECAP" if weekly else "DAILY RECAP"
    f22 = font(22)
    draw.text((cx(mode_label, f22), y), mode_label, font=f22, fill=MUTED)

    y += 36
    f50b = font(50, bold=True)
    draw.text((cx("TAIWAN MARKET", f50b), y), "TAIWAN MARKET", font=f50b, fill=WHITE)

    y += 56
    f26 = font(26)
    draw.text((cx(date_str, f26), y), date_str, font=f26, fill=MUTED)

    # ── One-liner ─────────────────────────────────────────────────
    y += 44
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
        f28b = font(28, bold=True)
        for line in lines[:2]:
            draw.text((cx(line, f28b), y), line, font=f28b, fill=GOLD)
            y += 36
    else:
        y += 8

    # ── Accent divider ────────────────────────────────────────────
    y += 12
    draw.rectangle([PAD, y, W-PAD, y+2], fill=ACCENT)

    # ── Indices ───────────────────────────────────────────────────
    y += 22
    f22s = font(22)
    f30b = font(30, bold=True)
    f24  = font(24)
    f34b = font(34, bold=True)

    draw.text((PAD, y), "INDICES", font=f22s, fill=GOLD)
    y += 32

    for name, d in core_data.items():
        pct = d['change_pct']
        color = GREEN_UP if pct >= 0 else RED_DOWN
        arrow = "▲" if pct >= 0 else "▼"
        pct_str = f"{arrow} {abs(pct):.2f}%"

        draw.rounded_rectangle([PAD, y, W-PAD, y+74], radius=12, fill=PANEL, outline=BORDER, width=1)
        draw.text((PAD+24, y+12), name, font=f30b, fill=WHITE)
        draw.text((PAD+24, y+44), f"{d['price']:,.0f}", font=f24, fill=MUTED)
        draw.text((rx(pct_str, f34b, W-PAD-24), y+22), pct_str, font=f34b, fill=color)
        y += 82

    # ── Foreign flow (外資買賣) ────────────────────────────────────
    if foreign_flow_str:
        y += 6
        draw.rounded_rectangle([PAD, y, W-PAD, y+50], radius=10, fill=PANEL, outline=BORDER, width=1)
        f24b = font(24, bold=True)
        draw.text((PAD+24, y+14), foreign_flow_str, font=f24b, fill=GOLD)
        y += 58

    # ── Divider ───────────────────────────────────────────────────
    y += 8
    draw.rectangle([PAD, y, W-PAD, y+1], fill=DIVIDER)
    y += 18

    # ── Stocks in the news (English + Chinese) ────────────────────
    if dynamic_data:
        draw.text((PAD, y), "STOCKS IN THE NEWS", font=f22s, fill=GOLD)
        y += 32

        sorted_stocks = sorted(
            dynamic_data.items(),
            key=lambda x: abs(x[1]['change_pct']),
            reverse=True
        )[:6]

        max_abs = max(abs(d['change_pct']) for _, d in sorted_stocks) or 1
        f24b = font(24, bold=True)
        f20  = font(20)
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

            # Line 1: English name (bold)
            draw.text((PAD+18, y+8), name, font=f24b, fill=WHITE)
            # Line 2: Chinese name + price
            zh_name = get_zh_name(name)
            sub_text = f"{zh_name}  NT${d['price']:,.0f}" if zh_name else f"NT${d['price']:,.0f}"
            draw.text((PAD+18, y+38), sub_text, font=f20, fill=MUTED)
            # Pct right-aligned
            draw.text((rx(pct_str, f24b, W-PAD-18), y+20), pct_str, font=f24b, fill=color)
            y += 72

    # ── Wave strip ────────────────────────────────────────────────
    wave_y = H - 110
    draw.rectangle([0, wave_y, W, wave_y+2], fill=DIVIDER)
    pts = [(int(i*W/60), wave_y+18+int(12*math.sin(i*math.pi*4/60))) for i in range(61)]
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=ACCENT, width=2)

    # ── Watermark ─────────────────────────────────────────────────
    f26bw = font(26, bold=True)
    draw.text((cx("@mini_money.lab", f26bw), H-56), "@mini_money.lab", font=f26bw, fill=MUTED)

    path = "market_museum_taiwan_infographic.jpg"
    img.save(path, "JPEG", quality=95)
    print(f"✅ Infographic saved ({palette['name']})")
    return path

# ====================== MARKET DATA ======================
CORE_TICKERS = {
    "TAIEX 加權指數":  "^TWII",
}

TAIWAN_FALLBACK_TICKERS = [
    {"name": "TSMC",            "ticker": "2330.TW"},
    {"name": "Hon Hai",         "ticker": "2317.TW"},
    {"name": "MediaTek",        "ticker": "2454.TW"},
    {"name": "Delta Electronics","ticker": "2308.TW"},
    {"name": "Cathay Financial", "ticker": "2882.TW"},
]

NEWS_SEED_SYMBOLS = [
    "^TWII",
    "2330.TW",  # TSMC
    "2317.TW",  # Hon Hai
    "2454.TW",  # MediaTek
    "2308.TW",  # Delta
    "2882.TW",  # Cathay Financial
    "2881.TW",  # Fubon Financial
    "2412.TW",  # Chunghwa Telecom
    "3711.TW",  # ASE
    "2382.TW",  # Quanta
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

def get_foreign_flow():
    """Attempt to get TWSE foreign investor buy/sell data."""
    try:
        today = get_hk_time()
        date_str = today.strftime("%Y%m%d")
        url = "https://www.twse.com.tw/en/fund/BFI82U"
        r = requests.get(url, params={"response": "json", "dayDate": date_str}, timeout=10)
        data = r.json()
        if data.get("stat") == "OK" and data.get("data"):
            # Last row is total: [type, buy, sell, diff]
            for row in data["data"]:
                if "Foreign" in row[0] or "foreign" in row[0]:
                    buy = int(row[1].replace(",", ""))
                    sell = int(row[2].replace(",", ""))
                    net = buy - sell
                    net_b = net / 1e8  # convert to 億
                    direction = "Net Buy 買超" if net > 0 else "Net Sell 賣超"
                    return f"外資 {direction} NT${abs(net_b):,.1f}億"
        return ""
    except Exception as e:
        print(f"  ⚠️ Foreign flow fetch failed: {e}")
        return ""

def get_taiwan_news(weekly=False):
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

def extract_taiwan_tickers_from_news(news_items):
    try:
        prompt = (
            "From these Taiwan financial news headlines, extract ONLY Taiwanese-listed companies.\n"
            "Return ONLY valid JSON array with 'name' and 'ticker' fields.\n"
            "IMPORTANT: Only include stocks listed on TWSE/TPEx with .TW or .TWO suffix.\n"
            "Do NOT include US stocks like Nvidia, Apple, etc — even if mentioned.\n"
            "Common TWSE tickers: TSMC=2330.TW, Hon Hai=2317.TW, MediaTek=2454.TW, "
            "Delta Electronics=2308.TW, Cathay Financial=2882.TW, Fubon Financial=2881.TW, "
            "CTBC Financial=2891.TW, Quanta Computer=2382.TW, Pegatron=4938.TW, "
            "Largan Precision=3008.TW, Novatek=3034.TW, Realtek=2379.TW, "
            "ASUS=2357.TW, Acer=2353.TW, UMC=2303.TW, ASE Technology=3711.TW, "
            "Wistron=3231.TW, Compal=2324.TW, Evergreen Marine=2603.TW, "
            "China Steel=2002.TW, Mega Financial=2886.TW, E.SUN Financial=2884.TW.\n"
            "Skip indices. Max 10. Return only JSON.\n\n"
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
    tickers_to_use = extracted_tickers or TAIWAN_FALLBACK_TICKERS
    if not extracted_tickers:
        print("  ℹ️ Using fallback tickers")
    results = {}
    for item in tickers_to_use:
        name, symbol = item.get("name"), item.get("ticker")
        if not name or not symbol:
            continue
        if not symbol.endswith(".TW") and not symbol.endswith(".TWO"):
            print(f"  ⏭️ Skipped non-TWSE: {name} ({symbol})")
            continue
        data = fetch_ticker_data(symbol, period=period)
        if data:
            results[name] = data
            print(f"  ✅ {name}: {data['change_pct']:+.2f}%")
        else:
            print(f"  ⚠️ Skipped {name}")
    return results

def format_market_data(core_data, dynamic_data, foreign_flow_str="", weekly=False):
    label = "Weekly Change" if weekly else "Daily Change"
    lines = [f"📊 Taiwan Indices ({label}):"]
    for name, d in core_data.items():
        arrow = "▲" if d['change_pct'] > 0 else "▼"
        lines.append(f"  {arrow} {name}: {d['price']:,.0f}  ({d['change_pct']:+.2f}%)")
    if foreign_flow_str:
        lines.append(f"  💰 {foreign_flow_str}")
    if dynamic_data:
        lines.append("")
        lines.append("🏢 Stocks In The News (TWSE):")
        for name, d in sorted(dynamic_data.items(), key=lambda x: abs(x[1]['change_pct']), reverse=True):
            arrow = "▲" if d['change_pct'] > 0 else "▼"
            zh = get_zh_name(name)
            label = f"{name} {zh}" if zh else name
            lines.append(f"  {arrow} {label}: NT${d['price']:,.0f}  ({d['change_pct']:+.2f}%)")
    return "\n".join(lines)

# ====================== GEMINI: STORIES ======================
def generate_daily_story(core_data, dynamic_data, news_items, photo_style, foreign_flow_str=""):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, foreign_flow_str)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        prompt = (
            "You are a creative director for a viral daily Taiwan stock market storytelling project.\n"
            f"Today is {get_hk_time().strftime('%A, %B %d, %Y')} HKT. DAILY recap of TWSE.\n\n"
            "1. Find the most interesting story — TSMC, foreign flow, earnings, macro, anything notable.\n"
            "2. Write a SHORT punchy Taiwan market recap (3-5 sentences, prose, no bullets).\n"
            "   Reference specific companies by English AND Chinese name where relevant.\n"
            "3. Write ONE punchy one-liner (max 8 words) capturing today's mood.\n"
            "   Examples: 'TSMC held. The island exhaled.' / 'Foreign money fled. Taiwan shrugged.'\n"
            "4. Create a vivid PHOTOGRAPHY description — NOT a painting:\n"
            "   - The SUBJECT must be the day's main story — conceptual, symbolic, dramatic.\n"
            "   - Think editorial fashion shoot meets financial drama.\n"
            "   - Examples: 'A silicon wafer shattering into a thousand fragments mid-air against black, "
            "each shard reflecting stock tickers — shot in high-speed frozen motion'. "
            "'A lone trader standing in an empty Taipei 101 lobby at dawn, golden light streaming through "
            "glass, shot in cinematic Deakins style'.\n"
            "   - Make it eye-catching and stylish, something people would say 'wow' to.\n"
            "   - NOT a generic news photo. NOT realistic documentary. CONCEPTUAL and ARTISTIC.\n"
            "   - The photography style specified MUST be followed faithfully.\n"
            "5. Instagram caption: strong hook, 2-3 witty sentences, 5-8 hashtags (all #), "
            "at least 2 Taiwan hashtags (e.g. #TAIEX #台股 #TSMC #台積電), max 150 words.\n\n"
            f"Market Data:\n{market_data_str}\n\n"
            f"News:\n{news_text}\n\n"
            f"Photography Style:\n{photo_style}\n\n"
            'Return ONLY valid JSON: {"recap":"...","one_liner":"...","image_prompt":"...","ig_caption":"..."}'
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        r = json.loads(raw)
        return r.get("recap",""), r.get("one_liner",""), r.get("image_prompt",""), r.get("ig_caption","")
    except Exception as e:
        print(f"⚠️ Daily story failed: {e}")
        return (
            "Taiwan markets moved today with notable activity.",
            "TSMC carries the island.",
            f"Dramatic conceptual photograph of silicon wafer. {photo_style}.",
            "Taiwan never sleeps. 📈\n#TAIEX #台股 #TSMC #台積電"
        )

def generate_weekly_story(core_data, dynamic_data, news_items, photo_style, foreign_flow_str=""):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, foreign_flow_str, weekly=True)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        hk_now = get_hk_time()
        week_start = (hk_now - timedelta(days=6)).strftime('%B %d')
        week_end = hk_now.strftime('%B %d, %Y')
        prompt = (
            "You are a creative director for a viral weekly Taiwan market project.\n"
            f"WEEKLY RECAP for TWSE, {week_start} - {week_end}.\n\n"
            "1. Identify 2-3 biggest themes of the week.\n"
            "2. Write a punchy weekly narrative (5-7 sentences, prose, no bullets).\n"
            "3. ONE punchy one-liner (max 8 words).\n"
            "4. Vivid PHOTOGRAPHY description (conceptual, dramatic, NOT a painting).\n"
            "   Style the week as a magazine cover shoot — bold, specific, unmistakably this week.\n"
            "5. Weekly IG caption: strong hook, 3-4 witty sentences, 6-10 hashtags, Taiwan hashtags.\n\n"
            f"Weekly Data:\n{market_data_str}\n\n"
            f"Headlines:\n{news_text}\n\n"
            f"Photography Style:\n{photo_style}\n\n"
            'Return ONLY valid JSON: {"recap":"...","one_liner":"...","image_prompt":"...","ig_caption":"..."}'
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        r = json.loads(raw)
        return r.get("recap",""), r.get("one_liner",""), r.get("image_prompt",""), r.get("ig_caption","")
    except Exception as e:
        print(f"⚠️ Weekly story failed: {e}")
        return (
            "It was an eventful week on the TWSE.",
            "Seven days of silicon dreams.",
            f"Dramatic weekly Taiwan conceptual photo. {photo_style}.",
            "Another week in Taipei. 📊\n#WeeklyRecap #TAIEX #台股 #TSMC"
        )

# ====================== GENERATE PHOTO ======================
async def generate_image(image_prompt):
    print(f"📸 Generating photo...")
    full_prompt = (
        "Create a stunning high-resolution vertical PHOTOGRAPH.\n"
        "Edge-to-edge, no white borders, no padding, no frames, full bleed.\n"
        "Vertical 3:4 portrait orientation.\n\n"
        "CRITICAL: This must look like a real PHOTOGRAPH, not a painting or illustration. "
        "Execute the specified photography style with absolute commitment. "
        "Realistic camera optics: depth of field, bokeh, lens flare, film grain where specified. "
        "Lighting must feel like real studio or natural light, not flat digital rendering. "
        "The image should look like it was shot by a world-class photographer for a high-end magazine. "
        "It should make people stop scrolling and say 'wow'. "
        "Conceptual and artistic — NOT a generic news photo.\n\n"
        f"{image_prompt}\n\n"
        "Ultra high resolution. Professional magazine-quality photography."
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=full_prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    image_path = "market_museum_taiwan_today.jpg"
    for part in response.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(image_path, "JPEG", quality=95)
            print(f"✅ Photo saved: {image.size}")
            return image_path
    return None

# ====================== MAIN ======================
async def main():
    try:
        hk_time = get_hk_time()
        sunday = is_sunday_hk()
        mode = "📅 WEEKLY RECAP" if sunday else "📰 DAILY RECAP"
        print(f"[{hk_time.strftime('%Y-%m-%d %H:%M')} HKT] 🇹🇼 Taiwan Market Museum — {mode}")

        print("📈 Fetching index data...")
        core_data = get_core_market_data(weekly=sunday)

        print("💰 Fetching foreign flow (外資)...")
        foreign_flow_str = get_foreign_flow()
        if foreign_flow_str:
            print(f"  {foreign_flow_str}")
        else:
            print("  ⚠️ No foreign flow data today")

        print("📰 Fetching news...")
        news_items = get_taiwan_news(weekly=sunday)
        print(f"  Got {len(news_items)} headlines")

        print("🔍 Extracting tickers...")
        extracted_tickers = extract_taiwan_tickers_from_news(news_items)

        print("📊 Fetching stock data...")
        dynamic_data = get_dynamic_stock_data(extracted_tickers, weekly=sunday)

        photo_style = get_random_style()
        print(f"📸 Photo style: {photo_style[:80]}...")

        print("✍️ Generating story...")
        if sunday:
            recap, one_liner, image_prompt, ig_caption = generate_weekly_story(
                core_data, dynamic_data, news_items, photo_style, foreign_flow_str
            )
        else:
            recap, one_liner, image_prompt, ig_caption = generate_daily_story(
                core_data, dynamic_data, news_items, photo_style, foreign_flow_str
            )
        print(f"  One-liner: {one_liner}")

        # Image 1 — Conceptual photo
        ai_image_path = await generate_image(image_prompt)
        if not ai_image_path:
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ Taiwan: No image generated.")
            return

        # Image 2 — Infographic
        print("📊 Generating infographic...")
        date_str = hk_time.strftime('%B %d, %Y')
        infographic_path = make_infographic(
            core_data, dynamic_data, foreign_flow_str, date_str, one_liner, weekly=sunday
        )

        # Telegram caption
        market_data_str = format_market_data(core_data, dynamic_data, foreign_flow_str, weekly=sunday)
        header = f"🇹🇼 Taiwan Weekly Recap • {date_str}" if sunday else f"🇹🇼 Taiwan Market Museum • {date_str}"
        tg_caption = f"{header}\n\n{recap}\n\n{market_data_str}\n\n#MarketMuseum #TAIEX #台股"
        if len(tg_caption) > 1024:
            tg_caption = tg_caption[:1020] + "..."

        await bot.send_media_group(
            chat_id=CHAT_ID,
            media=[
                InputMediaPhoto(media=open(ai_image_path, 'rb'), caption=tg_caption),
                InputMediaPhoto(media=open(infographic_path, 'rb')),
            ]
        )

        ig_caption = fix_hashtags(ig_caption)
        ig_label = (
            "📱 *IG Caption (Taiwan Weekly) — copy & paste ready:*"
            if sunday else
            "📱 *IG Caption (Taiwan) — copy & paste ready:*"
        )
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"{ig_label}\n\n{ig_caption}",
            parse_mode="Markdown"
        )

        print(f"✅ Taiwan {mode} — 2 images sent.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Taiwan Error: {str(e)[:300]}")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
