import os
import random
from openai import OpenAI
from telegram import Bot
from datetime import datetime
import asyncio

# ====================== CONFIG ======================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# ====================== ART STYLES ======================
ART_STYLES = [
    "in the style of Yoshitomo Nara",
    "in the style of Yusuke Hanai",
    "in the style of Nagaba Yuma",
    "in the style of Takashi Murakami",
    "in the style of Yayoi Kusama",
    "in the style of Banksy",
    "in the style of Van Gogh",
    "in the style of Claude Monet",
    "classic Japanese ukiyo-e woodblock print style, Hokusai influence",
]

def get_random_style():
    return random.choice(ART_STYLES)

# ====================== MARKET SUMMARY ======================
def get_market_summary():
    return """
    On May 29, 2026, the US stock market closed strongly at record highs. 
    The Dow Jones rose 0.7% and crossed 51,000 for the first time. 
    S&P 500 and Nasdaq also hit new records. 
    AI and technology stocks led the rally with strong optimism.
    """

# ====================== PROMPT (DALL·E 3 優化版) ======================
def create_art_prompt(market_summary):
    style = get_random_style()
    return f"""
A beautiful, high-resolution vertical museum-quality artwork in 4:5 aspect ratio.

Today's US stock market: {market_summary}

Create an elegant, emotionally resonant vertical painting. 
Use clear symbolic storytelling with rising energy, golden light, bull, blooming flowers or soaring birds. 
Clean composition, no text, no border, no frame, full bleed image.

{style}, masterpiece, highly detailed, sharp focus, rich colors, professional art, best quality, vertical composition
"""

# ====================== MAIN ======================
async def main():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Market Museum Started")

        market_summary = get_market_summary()
        prompt = create_art_prompt(market_summary)

        print("Generating image with DALL·E 3...")

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1536",      # 垂直 4:5 高解像度
            quality="standard",    # 可改 "hd" 如果想更高質
            n=1
        )

        image_url = response.data[0].url
        image_path = "market_museum_today.jpg"

        # 下載圖片
        import requests
        img_data = requests.get(image_url).content
        with open(image_path, "wb") as f:
            f.write(img_data)

        # 發送到 Telegram
        caption = f"""🌸 Market Museum Daily • {datetime.now().strftime('%B %d, %Y')}

{market_summary.strip()}

#MarketMuseum #StockMarketArt"""

        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=open(image_path, 'rb'),
            caption=caption
        )

        print("✅ Success! DALL·E 3 Image sent to Telegram.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Error: {str(e)[:300]}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
