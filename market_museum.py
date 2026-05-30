import os
import random
from openai import OpenAI
from telegram import Bot
from datetime import datetime
import asyncio
import requests

# ====================== CONFIG ======================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# ====================== ART STYLES ======================
ART_STYLES = [
    "in the style of Yoshitomo Nara, big-eyed curious figures, soft pastel with dark undertones",
    "in the style of Yusuke Hanai, clean lines, vibrant modern street art",
    "in the style of Nagaba Yuma, delicate emotional character illustration",
    "in the style of Takashi Murakami, superflat, vibrant pop art with flowers",
    "in the style of Yayoi Kusama, infinity patterns and dots",
    "in the style of Banksy, bold stencil street art",
    "in the style of Van Gogh, expressive emotional brush strokes",
    "in the style of Claude Monet, soft impressionist colors and light",
    "classic Japanese ukiyo-e woodblock print style inspired by Hokusai",
]

def get_random_style():
    return random.choice(ART_STYLES)

# ====================== MARKET SUMMARY ======================
def get_market_summary():
    """之後會改成自動抓真實新聞"""
    return """
    On May 29, 2026, the US stock market closed at record highs. 
    The Dow Jones rose 0.7% and crossed 51,000 for the first time. 
    S&P 500 and Nasdaq also hit new records. 
    AI and technology stocks led the rally with strong investor optimism.
    """

# ====================== PROMPT (優化版) ======================
def create_art_prompt(market_summary):
    style = get_random_style()
    return f"""
A high-resolution, museum-quality vertical artwork in 4:5 aspect ratio, full bleed image, no borders, no frames, no white edges.

Market situation: {market_summary}

Create an elegant, emotionally resonant and visually powerful vertical painting. 
Use clear symbolic elements such as rising golden energy, bull, blooming flowers, light from sky. 
Not too abstract, beautiful and inspiring composition.

{style}, masterpiece, ultra detailed, sharp focus, rich vibrant colors, professional art, best quality, clean edges, full image composition, vertical orientation
"""

# ====================== MAIN ======================
async def main():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Market Museum Started")

        market_summary = get_market_summary()
        prompt = create_art_prompt(market_summary)

        print("Generating image with GPT-Image-1...")

        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1536",      # Vertical 4:5
            quality="standard",
            n=1
        )

        image_url = response.data[0].url
        image_path = "market_museum_today.jpg"

        # 下載圖片
        img_data = requests.get(image_url).content
        with open(image_path, "wb") as f:
            f.write(img_data)

        # Caption
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
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Market Museum Error: {str(e)[:400]}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
