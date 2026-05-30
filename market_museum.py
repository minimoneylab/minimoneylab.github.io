import os
import random
import google.generativeai as genai
from telegram import Bot
from datetime import datetime
import asyncio

# ====================== CONFIG ======================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# ====================== ART STYLES ======================
ART_STYLES = [
    "in the style of Yoshitomo Nara, big-eyed curious figures, soft pastel with dark undertones",
    "in the style of Yusuke Hanai, clean lines, vibrant modern street art",
    "in the style of Nagaba Yuma, delicate emotional character illustration",
    "in the style of Takashi Murakami, superflat, vibrant pop art",
    "in the style of Yayoi Kusama, infinity patterns",
    "in the style of Banksy, bold stencil street art",
    "in the style of Van Gogh, expressive brush strokes",
    "classic ukiyo-e woodblock print style inspired by Hokusai",
]

def get_random_style():
    return random.choice(ART_STYLES)

# ====================== MARKET SUMMARY ======================
def get_market_summary():
    return """
    On May 29, 2026, the US stock market closed at record highs. 
    The Dow Jones rose 0.7% and crossed 51,000 for the first time. 
    S&P 500 and Nasdaq also hit new records. 
    AI and technology stocks led the rally with strong optimism.
    """

# ====================== PROMPT (加強防白邊版) ======================
def create_art_prompt(market_summary):
    style = get_random_style()
    return f"""
A high-resolution museum-quality vertical artwork, 4:5 aspect ratio, full bleed image, no white borders, no frames, no edges at all.

Market situation: {market_summary}

Create an elegant, emotionally powerful vertical painting. 
Use clear symbolic elements like rising golden bull, blooming flowers, light beams, soaring doves. 
Beautiful composition, inspiring atmosphere, not too abstract.

{style}, masterpiece, ultra detailed, sharp focus, rich colors, professional art, best quality, clean edges, full composition, no border, no frame, vertical orientation --ar 4:5 --stylize 800
"""

# ====================== MAIN ======================
async def main():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Market Museum Started")

        market_summary = get_market_summary()
        prompt = create_art_prompt(market_summary)

        print("Generating image with Gemini...")

        model = genai.GenerativeModel('gemini-2.5-flash')   # 較穩定 model

        response = model.generate_content(prompt)

        image_path = "market_museum_today.jpg"
        image_saved = False

        for part in response.parts:
            if part.inline_data:
                with open(image_path, "wb") as f:
                    f.write(part.inline_data.data)
                image_saved = True
                break

        if not image_saved:
            print("❌ No image returned from Gemini")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ Gemini did not generate image today.")
            return

        caption = f"""🌸 Market Museum Daily • {datetime.now().strftime('%B %d, %Y')}

{market_summary.strip()}

#MarketMuseum #StockMarketArt"""

        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=open(image_path, 'rb'),
            caption=caption
        )

        print("✅ Success! Image sent to Telegram.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Error: {str(e)[:300]}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
