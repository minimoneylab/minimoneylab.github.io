import os
import random
import json
import math
import time
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

# ====================== K-DRAMA / K-POP PHOTOGRAPHY STYLES ======================
PHOTO_STYLES = [
    (
        "Korean drama romance scene cinematography — Crash Landing on You / Goblin aesthetic: "
        "golden hour backlight streaming through the subject's hair creating a halo glow, "
        "shallow depth of field on 85mm f/1.4 — background dissolved into warm amber bokeh, "
        "single beautiful Korean figure in impeccably styled outfit looking wistfully into distance, "
        "soft warm color grading — lifted shadows, peachy skin tones, desaturated greens, "
        "the exact lighting of a K-drama confession scene where time slows down, "
        "shot on ARRI Alexa with anamorphic lens flare"
    ),
    (
        "K-pop music video still — BLACKPINK / aespa level production: "
        "hyper-stylized set with neon lighting in hot pink, electric blue, and violet, "
        "sharp confident pose — one figure commanding the frame with attitude, "
        "glossy reflective surfaces, chrome and glass, futuristic minimal set design, "
        "dramatic rim lighting creating glowing silhouette edges, "
        "hair and fabric frozen in motion by high-speed flash, "
        "the production value of a 10-million-dollar music video — every pixel expensive"
    ),
    (
        "Korean historical drama Sageuk cinematography — Dae Jang Geum / Kingdom style: "
        "richly detailed Joseon Dynasty hanbok in jewel tones — deep crimson, royal blue, gold thread, "
        "atmospheric morning mist rolling across a traditional palace courtyard, "
        "naturalistic side lighting from paper lanterns creating warm pools of amber, "
        "exquisite attention to textile texture — silk sheen, brocade pattern, jade ornaments, "
        "the epic grandeur of Korean period drama — every frame a painting, "
        "wide establishing shot showing architecture and figure in epic proportion"
    ),
    (
        "Korean noir thriller cinematography — Parasite / Oldboy style: "
        "stark high-contrast lighting — single harsh overhead or side source, deep black shadows, "
        "unsettling composition with dutch angle or extreme low angle, "
        "desaturated cold color palette with sickly green or yellow tint, "
        "subject's face half-lit half-hidden — moral ambiguity in every shadow, "
        "rain-wet surfaces reflecting distorted neon, "
        "the Bong Joon-ho energy of beautiful images hiding ugly truths, "
        "shot on wide 21mm lens distorting perspective subtly"
    ),
    (
        "K-pop concept photo — BTS / SEVENTEEN album jacket aesthetic: "
        "clean minimal studio with one bold color backdrop — powder blue, mint, lilac, or peach, "
        "perfectly styled Korean figure with editorial-level hair and fashion, "
        "flat even lighting from large softbox creating flawless skin, "
        "one dramatic prop or visual element breaking the minimalism — floating flowers, "
        "shattered mirror, cascading water, or geometric shapes, "
        "the deliberate perfection of a K-pop comeback concept photo, "
        "medium format digital clarity — every pore and thread visible"
    ),
    (
        "Korean street fashion photography — Gangnam / Hongdae at night: "
        "stylish figure in oversized Korean streetwear walking through neon-lit alley, "
        "mixed lighting: warm tungsten from shop signs + cool blue from LED + magenta neon, "
        "35mm street photography feel — slightly off-center composition, motion blur on edges, "
        "reflection puddles on asphalt doubling the neon colors, "
        "steam rising from street food carts adding atmospheric depth, "
        "the energy of Seoul after midnight — fashion-forward and electric"
    ),
    (
        "Korean food cinematography — elegant banchan spread or luxury Korean BBQ: "
        "overhead flat-lay shot of perfectly arranged dishes on dark stone surface, "
        "each dish a masterpiece of color: kimchi red, japchae brown, namul green, rice white, "
        "soft directional window light from upper left creating gentle shadows, "
        "steam rising from a sizzling dish catching the light, "
        "extreme detail on texture — the glisten of sesame oil, the crack of crispy skin, "
        "the visual language of Korean food culture applied to financial storytelling"
    ),
    (
        "Korean webtoon brought to life — Tower of God / Solo Leveling live-action style: "
        "dramatic hero pose with supernatural energy effect — glowing aura, particle effects, "
        "split-lighting creating half-bright half-shadow face, "
        "saturated color grading pushed to comic-book levels — deep teals and hot magentas, "
        "VFX-enhanced reality — real person with impossible lighting and energy effects, "
        "the aesthetic of a webtoon panel made photorealistic, "
        "epic scale and intensity dialed to eleven"
    ),
    (
        "Korean winter drama scene — Winter Sonata / snowscape romance: "
        "softly falling snow catching warm streetlamp light against blue twilight sky, "
        "lone figure in elegant Korean winter coat — long scarf flowing, "
        "telephoto compression at 200mm stacking snowflakes into dreamy bokeh layers, "
        "muted pastel color palette — powder blue, silver, soft white, blush pink, "
        "the melancholic beauty of Korean winter romance, "
        "every snowflake individually lit like a tiny star"
    ),
    (
        "Korean horror aesthetic — Train to Busan / The Wailing style: "
        "desaturated grey-green color grade with isolated red accent, "
        "wide-angle lens distortion creating claustrophobic spaces, "
        "motion blur on running figures suggesting panic and chaos, "
        "fluorescent overhead lighting casting unflattering green-white on skin, "
        "empty urban spaces that should be crowded — uncanny absence, "
        "the visceral dread of Korean horror — grounded in reality, not fantasy"
    ),
    (
        "Korean luxury brand campaign — Samsung / Hyundai premium tier aesthetic: "
        "sleek product-forward composition on reflective dark surface, "
        "razor-sharp focus with gradient lighting revealing form and material, "
        "cool blue-silver color palette suggesting technology and precision, "
        "single object elevated to art — lit from multiple angles with surgical precision, "
        "negative space dominating the frame — luxury through restraint, "
        "the visual language of Korean chaebol corporate power"
    ),
    (
        "Korean indie film cinematography — Burning / Poetry style: "
        "naturalistic available light only — golden afternoon sun through dusty windows, "
        "long lens observation of subject from a distance — voyeuristic intimacy, "
        "earth tones and muted palette — ochre, olive, warm grey, faded blue, "
        "unhurried composition with vast empty space and small human figure, "
        "the quiet contemplative beauty of Korean arthouse cinema, "
        "16mm film grain visible, slightly soft focus adding dreamlike quality"
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
PALETTES = [
    {
        "name": "hallyu_blue",
        "BG": (6, 8, 22), "PANEL": (12, 16, 38), "BORDER": (28, 36, 78),
        "ACCENT": (60, 100, 255), "GOLD": (140, 180, 255),
        "MUTED": (90, 110, 170), "DIVIDER": (18, 24, 58),
    },
    {
        "name": "gangnam_pink",
        "BG": (18, 6, 16), "PANEL": (32, 12, 28), "BORDER": (72, 28, 60),
        "ACCENT": (255, 80, 150), "GOLD": (255, 160, 200),
        "MUTED": (170, 100, 140), "DIVIDER": (48, 18, 40),
    },
    {
        "name": "joseon_gold",
        "BG": (14, 12, 6), "PANEL": (26, 22, 10), "BORDER": (62, 50, 18),
        "ACCENT": (200, 160, 40), "GOLD": (255, 210, 80),
        "MUTED": (155, 135, 85), "DIVIDER": (44, 36, 12),
    },
    {
        "name": "seoul_neon",
        "BG": (8, 4, 18), "PANEL": (16, 8, 34), "BORDER": (40, 20, 80),
        "ACCENT": (180, 60, 255), "GOLD": (220, 140, 255),
        "MUTED": (130, 90, 170), "DIVIDER": (28, 14, 54),
    },
    {
        "name": "hangang_teal",
        "BG": (4, 14, 18), "PANEL": (8, 24, 32), "BORDER": (16, 52, 68),
        "ACCENT": (30, 190, 190), "GOLD": (100, 230, 220),
        "MUTED": (70, 140, 150), "DIVIDER": (10, 36, 46),
    },
]

def _texture_hangeul(draw, W, H, accent):
    """Subtle angular strokes inspired by Korean Hangeul characters."""
    rng = random.Random(22)
    for _ in range(200):
        x, y = rng.randint(0, W), rng.randint(0, H)
        style = rng.randint(0, 2)
        if style == 0:  # horizontal + vertical (ㄱ shape)
            draw.line([(x, y), (x+rng.randint(15, 40), y)], fill=(*accent, 14), width=1)
            draw.line([(x+20, y), (x+20, y+rng.randint(15, 35))], fill=(*accent, 14), width=1)
        elif style == 1:  # circle (ㅇ shape)
            r = rng.randint(6, 12)
            draw.ellipse([x-r, y-r, x+r, y+r], outline=(*accent, 12), width=1)
        else:  # vertical line (ㅣ shape)
            draw.line([(x, y), (x, y+rng.randint(15, 45))], fill=(*accent, 14), width=1)

def _texture_grid(draw, W, H, accent):
    for x in range(0, W, 48):
        draw.line([(x, 0), (x, H)], fill=(*accent, 12), width=1)
    for y in range(0, H, 48):
        draw.line([(0, y), (W, y)], fill=(*accent, 12), width=1)

def _texture_wave(draw, W, H, accent):
    rng = random.Random(33)
    for i in range(20):
        y_base = rng.randint(0, H)
        pts = []
        for x in range(0, W, 8):
            y = y_base + int(15 * math.sin((x + i * 40) * math.pi / 120))
            pts.append((x, y))
        for j in range(len(pts) - 1):
            draw.line([pts[j], pts[j+1]], fill=(*accent, 10), width=1)

def _texture_stars(draw, W, H, accent):
    """K-pop star sparkle pattern."""
    rng = random.Random(77)
    for _ in range(80):
        x, y = rng.randint(0, W), rng.randint(0, H)
        size = rng.randint(2, 8)
        # 4-point star
        draw.line([(x-size, y), (x+size, y)], fill=(*accent, rng.randint(12, 24)), width=1)
        draw.line([(x, y-size), (x, y+size)], fill=(*accent, rng.randint(12, 24)), width=1)

TEXTURES = [_texture_hangeul, _texture_grid, _texture_wave, _texture_stars]

# ====================== INFOGRAPHIC ======================
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
    RED_UP     = (255, 80, 80)    # Korea: red = up
    BLUE_DOWN  = (80, 160, 255)   # Korea: blue = down

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

    # ── Taegeuk-inspired icon (circle halves) ─────────────────────
    tcx, tcy, tr = W // 2, 82, 32
    draw.ellipse([tcx-tr, tcy-tr, tcx+tr, tcy+tr], fill=ACCENT)
    draw.ellipse([tcx-tr//2, tcy-tr//2, tcx+tr//2, tcy+tr//2], fill=BG)

    # ── Header ────────────────────────────────────────────────────
    y = 138
    mode_label = "WEEKLY RECAP" if weekly else "DAILY RECAP"
    f22 = font(22)
    draw.text((cx(mode_label, f22), y), mode_label, font=f22, fill=MUTED)

    y += 36
    f50b = font(50, bold=True)
    draw.text((cx("KOREA MARKET", f50b), y), "KOREA MARKET", font=f50b, fill=WHITE)

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
        color = RED_UP if pct >= 0 else BLUE_DOWN
        arrow = "▲" if pct >= 0 else "▼"
        pct_str = f"{arrow} {abs(pct):.2f}%"

        draw.rounded_rectangle([PAD, y, W-PAD, y+74], radius=12, fill=PANEL, outline=BORDER, width=1)
        draw.text((PAD+24, y+12), name, font=f30b, fill=WHITE)
        draw.text((PAD+24, y+44), f"{d['price']:,.0f}", font=f24, fill=MUTED)
        draw.text((rx(pct_str, f34b, W-PAD-24), y+22), pct_str, font=f34b, fill=color)
        y += 82

    # ── Divider ───────────────────────────────────────────────────
    y += 8
    draw.rectangle([PAD, y, W-PAD, y+1], fill=DIVIDER)
    y += 18

    # ── Stocks in the news ────────────────────────────────────────
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
            color = RED_UP if pct >= 0 else BLUE_DOWN
            arrow = "▲" if pct >= 0 else "▼"
            pct_str = f"{arrow} {abs(pct):.2f}%"
            bar_w = max(int(bar_max * (abs(pct) / max_abs)), 8)

            draw.rounded_rectangle([PAD, y, W-PAD, y+66], radius=10, fill=PANEL, outline=BORDER, width=1)
            bar_fill = (50, 10, 10) if pct >= 0 else (10, 20, 50)
            draw.rounded_rectangle([PAD, y, PAD+bar_w+60, y+66], radius=10, fill=bar_fill)

            draw.text((PAD+18, y+10), name, font=f24b, fill=WHITE)
            draw.text((PAD+18, y+40), f"KRW {d['price']:,.0f}", font=f20, fill=MUTED)
            draw.text((rx(pct_str, f24b, W-PAD-18), y+20), pct_str, font=f24b, fill=color)
            y += 72

    # ── FINI aggregate (bottom) ───────────────────────────────────
    if foreign_flow_str:
        y += 8
        draw.rectangle([PAD, y, W-PAD, y+1], fill=DIVIDER)
        y += 16
        is_buy = "Buy" in foreign_flow_str
        fini_color = RED_UP if is_buy else BLUE_DOWN
        fini_label = "FINI Net Buy" if is_buy else "FINI Net Sell"
        fini_amt = "KRW " + foreign_flow_str.split("KRW ")[-1] if "KRW " in foreign_flow_str else ""
        draw.rounded_rectangle([PAD, y, W-PAD, y+44], radius=10, fill=PANEL, outline=BORDER, width=1)
        f24b_fini = font(24, bold=True)
        draw.text((PAD+24, y+12), fini_label, font=f24b_fini, fill=fini_color)
        if fini_amt:
            draw.text((rx(fini_amt, f24b_fini, W-PAD-24), y+12), fini_amt, font=f24b_fini, fill=fini_color)
        y += 52

    # ── Wave strip ────────────────────────────────────────────────
    wave_y = H - 110
    draw.rectangle([0, wave_y, W, wave_y+2], fill=DIVIDER)
    pts = [(int(i*W/60), wave_y+18+int(12*math.sin(i*math.pi*4/60))) for i in range(61)]
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=ACCENT, width=2)

    # ── Watermark ─────────────────────────────────────────────────
    f26b = font(26, bold=True)
    draw.text((cx("@mini_money.lab", f26b), H-56), "@mini_money.lab", font=f26b, fill=MUTED)

    path = "market_museum_korea_infographic.jpg"
    img.save(path, "JPEG", quality=95)
    print(f"✅ Infographic saved ({palette['name']})")
    return path

# ====================== MARKET DATA ======================
CORE_TICKERS = {
    "KOSPI":  "^KS11",
    "KOSDAQ": "^KQ11",
}

KOREA_FALLBACK_TICKERS = [
    {"name": "Samsung Electronics", "ticker": "005930.KS"},
    {"name": "SK Hynix",           "ticker": "000660.KS"},
    {"name": "Hyundai Motor",      "ticker": "005380.KS"},
    {"name": "Naver",              "ticker": "035420.KS"},
    {"name": "Kakao",              "ticker": "035720.KS"},
]

NEWS_SEED_SYMBOLS = [
    "^KS11", "^KQ11",
    "005930.KS",  # Samsung Electronics
    "000660.KS",  # SK Hynix
    "005380.KS",  # Hyundai Motor
    "035420.KS",  # Naver
    "035720.KS",  # Kakao
    "373220.KS",  # LG Energy Solution
    "006400.KS",  # Samsung SDI
    "005490.KS",  # POSCO Holdings
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
    results = {}
    for name, sym in CORE_TICKERS.items():
        data = fetch_ticker_data(sym, period)
        if data:
            results[name] = data
    return results

def _krx_session():
    """Create a session for KRX data requests."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/125.0.0.0 Safari/537.36",
        "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
        "Accept": "application/json",
    })
    return s

def get_foreign_flow():
    """Get aggregate FINI (foreign investor) net buy/sell from KRX."""
    today = get_hk_time()
    date_str = today.strftime("%Y%m%d")
    session = _krx_session()

    try:
        # KRX investor trading trend endpoint
        r = session.post(
            "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
            data={
                "bld": "dbms/MDC/STAT/standard/MDCSTAT02401",
                "locale": "en",
                "searchType": "1",
                "mktId": "ALL",
                "trdDd": date_str,
                "money": "1",
                "csvxls_is498": "false",
            },
            timeout=15
        )
        print(f"  → KRX status={r.status_code}")
        data = r.json()
        rows = data.get("output", [])
        for row in rows:
            inv_type = row.get("INVST_TP_NM", "")
            if "Foreign" in inv_type or "외국인" in inv_type:
                net_str = row.get("NETBID_TRDVAL", "0").replace(",", "")
                net = int(float(net_str))
                net_bn = net / 1e9  # billions of KRW
                direction = "FINI Net Buy" if net > 0 else "FINI Net Sell"
                result = f"{direction} KRW {abs(net_bn):,.2f}bn"
                print(f"  ✅ {result}")
                return result
    except Exception as e:
        print(f"  ⚠️ KRX FINI failed: {e}")

    # Fallback: try yfinance-based estimation
    print("  ⚠️ No KRX FINI data available")
    return ""

def get_korea_news(weekly=False):
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

def extract_korea_tickers_from_news(news_items):
    try:
        prompt = (
            "From these Korea financial news headlines, extract ONLY Korean-listed companies.\n"
            "Return ONLY valid JSON array with 'name' and 'ticker' fields.\n"
            "IMPORTANT: Only include stocks on KRX (KOSPI/KOSDAQ) with .KS or .KQ suffix.\n"
            "Do NOT include US stocks even if mentioned.\n"
            "Common KRX tickers: Samsung Electronics=005930.KS, SK Hynix=000660.KS, "
            "Hyundai Motor=005380.KS, Naver=035420.KS, Kakao=035720.KS, "
            "LG Energy Solution=373220.KS, Samsung SDI=006400.KS, POSCO Holdings=005490.KS, "
            "Kia=000270.KS, LG Chem=051910.KS, Samsung Biologics=207940.KS, "
            "Celltrion=068270.KS, KB Financial=105560.KS, Shinhan Financial=055550.KS, "
            "Korean Air=003490.KS, SK Telecom=017670.KS, Hyundai Mobis=012330.KS, "
            "Hana Financial=086790.KS, Samsung SDS=018260.KS, SK Innovation=096770.KS.\n"
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
    tickers_to_use = extracted_tickers or KOREA_FALLBACK_TICKERS
    if not extracted_tickers:
        print("  ℹ️ Using fallback tickers")
    results = {}
    for item in tickers_to_use:
        name, symbol = item.get("name"), item.get("ticker")
        if not name or not symbol:
            continue
        if not symbol.endswith(".KS") and not symbol.endswith(".KQ"):
            print(f"  ⏭️ Skipped non-KRX: {name} ({symbol})")
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
    lines = [f"📊 Korea Indices ({label}):"]
    for name, d in core_data.items():
        arrow = "▲" if d['change_pct'] > 0 else "▼"
        lines.append(f"  {arrow} {name}: {d['price']:,.0f}  ({d['change_pct']:+.2f}%)")
    if foreign_flow_str:
        lines.append(f"  💰 {foreign_flow_str}")
    if dynamic_data:
        lines.append("")
        lines.append("🏢 Stocks In The News (KRX):")
        for name, d in sorted(dynamic_data.items(), key=lambda x: abs(x[1]['change_pct']), reverse=True):
            arrow = "▲" if d['change_pct'] > 0 else "▼"
            lines.append(f"  {arrow} {name}: KRW {d['price']:,.0f}  ({d['change_pct']:+.2f}%)")
    return "\n".join(lines)

# ====================== GEMINI: STORIES ======================
def generate_daily_story(core_data, dynamic_data, news_items, photo_style, foreign_flow_str=""):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, foreign_flow_str)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        prompt = (
            "You are a creative director for a viral daily Korea stock market storytelling project.\n"
            f"Today is {get_hk_time().strftime('%A, %B %d, %Y')} HKT. DAILY recap of KRX.\n\n"
            "1. Find the most interesting story — Samsung, SK Hynix, FINI flow, earnings, macro.\n"
            "2. Write a SHORT punchy Korea market recap (3-5 sentences, prose, no bullets).\n"
            "3. Write ONE punchy one-liner (max 8 words) capturing today's mood.\n"
            "   Examples: 'Samsung fell. Korea held its breath.' / 'Hynix rallied. Memory is money.'\n"
            "4. Create a vivid K-DRAMA / K-POP PHOTOGRAPHY description:\n"
            "   STEP A — Pick a visual concept. The photo must tell today's market story through "
            "Korean cultural aesthetics. Think of it as casting a K-drama scene:\n"
            "   • A devastatingly handsome Korean man in a Samsung exec suit looking defeated at his desk\n"
            "   • A fierce K-pop girl group posing victoriously atop a pile of gold semiconductor chips\n"
            "   • A Joseon Dynasty scholar studying a scroll that unfurls into a modern stock chart\n"
            "   • A Korean chef slicing a golden wafer like premium sashimi in a luxury restaurant\n"
            "   • A couple in matching Hyundai uniforms sharing an umbrella in the rain outside a factory\n"
            "   • A webtoon hero figure surrounded by crumbling stock tickers like falling buildings\n"
            "   DO NOT default to generic city skyline. The SUBJECT must be a person or people in a scene.\n"
            "   STEP B — Describe the specific scene: lighting, camera angle, mood, styling, what makes it wow.\n"
            "   Follow the photography style faithfully.\n"
            "5. Instagram caption: strong hook, 2-3 witty sentences, 5-8 hashtags (all #), "
            "at least 2 Korea hashtags (#KOSPI #KoreaStocks #Samsung etc), max 150 words.\n\n"
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
            "Korea markets moved today with notable activity.",
            "Seoul never sleeps.",
            f"Dramatic K-drama style photo of Korean markets. {photo_style}.",
            "Seoul never sleeps. 📈\n#KOSPI #KoreaStocks #Samsung"
        )

def generate_weekly_story(core_data, dynamic_data, news_items, photo_style, foreign_flow_str=""):
    try:
        market_data_str = format_market_data(core_data, dynamic_data, foreign_flow_str, weekly=True)
        news_text = "\n".join(f"- {n}" for n in news_items) if news_items else "No major news."
        hk_now = get_hk_time()
        week_start = (hk_now - timedelta(days=6)).strftime('%B %d')
        week_end = hk_now.strftime('%B %d, %Y')
        prompt = (
            "You are a creative director for a viral weekly Korea market project.\n"
            f"WEEKLY RECAP for KRX, {week_start} - {week_end}.\n\n"
            "1. Identify 2-3 biggest themes of the week.\n"
            "2. Write a punchy weekly narrative (5-7 sentences, prose, no bullets).\n"
            "3. ONE punchy one-liner (max 8 words).\n"
            "4. K-DRAMA / K-POP style PHOTOGRAPHY description — cast a scene with Korean people, "
            "not a generic cityscape. Pick a concept: K-drama romance, K-pop MV, Sageuk historical, "
            "Korean noir, luxury brand shoot, etc. Describe subject, lighting, camera, wow factor.\n"
            "5. Weekly IG caption: strong hook, 3-4 witty sentences, 6-10 hashtags, Korea hashtags.\n\n"
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
            "It was an eventful week on the KRX.",
            "Five days of K-drama.",
            f"Dramatic weekly Korea photo. {photo_style}.",
            "Another week in Seoul. 📊\n#WeeklyRecap #KOSPI #KoreaStocks"
        )

# ====================== GENERATE PHOTO ======================
async def generate_image(image_prompt):
    print(f"📸 Generating photo...")
    full_prompt = (
        "Create a stunning high-resolution vertical PHOTOGRAPH.\n"
        "Edge-to-edge, no white borders, no padding, no frames, full bleed.\n"
        "Vertical 3:4 portrait orientation.\n\n"
        "CRITICAL: This must look like a real PHOTOGRAPH from a Korean drama or K-pop production. "
        "NOT a painting, NOT an illustration. Real camera optics: depth of field, bokeh, film grain. "
        "The subject must be Korean-looking people in a scene that tells a financial story. "
        "Think: the production quality of a Netflix K-drama or a SM Entertainment music video. "
        "Cinematic, stylish, emotionally charged. Make people stop scrolling.\n\n"
        f"{image_prompt}\n\n"
        "Ultra high resolution. Professional Korean entertainment industry production quality."
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-image",
        contents=full_prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )
    image_path = "market_museum_korea_today.jpg"
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
        print(f"[{hk_time.strftime('%Y-%m-%d %H:%M')} HKT] 🇰🇷 Korea Market Museum — {mode}")

        print("📈 Fetching index data...")
        core_data = get_core_market_data(weekly=sunday)

        print("💰 Fetching FINI data...")
        foreign_flow_str = get_foreign_flow()
        if foreign_flow_str:
            print(f"  {foreign_flow_str}")
        else:
            print("  ⚠️ No FINI data today")

        print("📰 Fetching news...")
        news_items = get_korea_news(weekly=sunday)
        print(f"  Got {len(news_items)} headlines")

        print("🔍 Extracting tickers...")
        extracted_tickers = extract_korea_tickers_from_news(news_items)

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

        # Image 1 — K-drama / K-pop photo
        ai_image_path = await generate_image(image_prompt)
        if not ai_image_path:
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ Korea: No image generated.")
            return

        # Image 2 — Infographic
        print("📊 Generating infographic...")
        date_str = hk_time.strftime('%B %d, %Y')
        infographic_path = make_infographic(
            core_data, dynamic_data, foreign_flow_str, date_str, one_liner, weekly=sunday
        )

        # Telegram caption
        market_data_str = format_market_data(core_data, dynamic_data, foreign_flow_str, weekly=sunday)
        header = f"🇰🇷 Korea Weekly Recap • {date_str}" if sunday else f"🇰🇷 Korea Market Museum • {date_str}"
        tg_caption = f"{header}\n\n{recap}\n\n{market_data_str}\n\n#MarketMuseum #KOSPI #KoreaStocks"
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
            "📱 *IG Caption (Korea Weekly) — copy & paste ready:*"
            if sunday else
            "📱 *IG Caption (Korea) — copy & paste ready:*"
        )
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"{ig_label}\n\n{ig_caption}",
            parse_mode="Markdown"
        )

        print(f"✅ Korea {mode} — 2 images sent.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Korea Error: {str(e)[:300]}")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
