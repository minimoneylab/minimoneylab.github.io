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

# ====================== ART STYLES (你鍾意嘅藝術家) ======================
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

# ====================== MARKET SUMMARY (暫用模板) ======================
def get_market_summary():
    """之後會改成自動抓真實新聞"""
    return """
    On May 29, 2026, the US stock market closed at record highs. 
    The Dow Jones Industrial Average rose 0.7% and crossed 51,000 for the first time. 
    S&P 500 and Nasdaq also hit new records. 
    AI and technology stocks led the rally amid strong investor optimism.
    """

# ====================== PROMPT ======================
def create_art_prompt(market_summary):
    style = get_random_style()
    
    prompt = f"""
A beautiful vertical museum-quality painting capturing the spirit of today's US stock market.

Market situation: {market_summary}

Create a clear, emotionally resonant vertical painting. 
Use symbolic but understandable elements (rising bull, light, sky, flowers, energy etc). 
Not too abstract. Should be visually appealing and easy to understand.

{style}, masterpiece, highly detailed, excellent composition, vertical orientation, museum quality --ar 4:5 --stylize 650
"""
    return prompt.strip()

# ====================== MAIN ======================
async def main():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Market Museum Started")

        market_summary = get_market_summary()
        prompt = create_art_prompt(market_summary)

        print("Generating image with Gemini...")

        model = genai.GenerativeModel('gemini-2.5-flash-image')
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
