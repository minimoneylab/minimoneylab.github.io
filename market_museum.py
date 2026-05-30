import os
import google.generativeai as genai
from telegram import Bot
from datetime import datetime
import asyncio
import random

# ====================== CONFIG ======================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# ====================== ART STYLES ======================
ART_STYLES = [
    "in the style of Yoshitomo Nara, big-eyed curious figures, soft pastel with dark undertones, minimalist yet emotionally powerful",
    "in the style of Yusuke Hanai, clean lines, vibrant modern street art with warmth",
    "in the style of Nagaba Yuma, delicate emotional character illustration",
    "in the style of Takashi Murakami, superflat, vibrant pop art with flowers",
    "in the style of Yayoi Kusama, infinity dots and patterns",
    "in the style of Banksy, bold stencil street art",
    "in the style of Van Gogh, expressive emotional brush strokes",
    "in the style of Claude Monet, soft impressionist colors and light",
    "classic ukiyo-e woodblock print style, bold lines, dramatic waves inspired by Hokusai",
]

def get_random_style():
    return random.choice(ART_STYLES)

# ====================== MARKET SUMMARY ======================
def get_market_summary():
    """之後會改成自動抓真實新聞"""
    return """
    On May 29, 2026, the US stock market closed at record highs. 
    The Dow Jones Industrial Average rose 0.7% and crossed 51,000 for the first time. 
    S&P 500 and Nasdaq also hit new records. 
    AI and technology stocks led the rally amid strong investor optimism.
    """

# ====================== IMPROVED PROMPT (重點加強) ======================
def create_art_prompt(market_summary):
    style = get_random_style()
    
    prompt = f"""
A high-resolution, museum-quality vertical artwork in 4:5 aspect ratio, full bleed image with no white borders, no frames, no edges.

Today's US stock market summary: {market_summary}

Create a visually powerful, emotionally resonant vertical painting. 
Use clear symbolic elements such as rising golden bull, light beams, blooming flowers, soaring birds, or energetic sky. 
Elegant and inspiring composition, not too abstract, easy to understand, high aesthetic appeal.

{style}, masterpiece, ultra detailed, sharp focus, rich colors, professional composition, best quality, clean edges, full image composition, no border, no frame, high resolution, vertical orientation --ar 4:5 --stylize 850 --v 6
"""
    return prompt.strip()

# ====================== MAIN ======================
async def main():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Market Museum Started")

        market_summary = get_market_summary()
        prompt = create_art_prompt(market_summary)

        print("Generating image with Gemini...")

        # 使用較穩定 model
        model = genai.GenerativeModel('gemini-2.5-flash')

        response = model.generate_content(prompt)

        image_path = "market_museum_today.jpg"
        for part in response.parts:
            if part.inline_data:
                with open(image_path, "wb") as f:
                    f.write(part.inline_data.data)
                break

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

if __name__ == "__main__":
    asyncio.run(main())
