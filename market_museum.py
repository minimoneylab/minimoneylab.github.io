import os
import random
from google import genai
from google.genai import types
from telegram import Bot
from datetime import datetime
import asyncio

# ====================== CONFIG ======================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# ====================== ART STYLES ======================
ART_STYLES = [
    "in the style of Yoshitomo Nara, big-eyed curious figures, soft pastel with dark undertones",
    "in the style of Yusuke Hanai, clean lines, vibrant modern street art",
    "in the style of Nagaba Yuma, delicate emotional character illustration",
    "in the style of Takashi Murakami, superflat, vibrant pop art",
    "in the style of Yayoi Kusama, infinity patterns",
    "in the style of Banksy, bold stencil street art",
    "in the style of Van Gogh, expressive emotional brush strokes",
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

# ====================== PROMPT ======================
def create_art_prompt(market_summary):
    style = get_random_style()
    return f"""Create a clean, high-quality vertical digital painting in 4:5 ratio. 
No borders, no frames, no white edges, full image.
Market situation: {market_summary}
Elegant and inspiring vertical composition with rising momentum. 
Use symbolic but clear elements like golden light, rising bull, blooming flowers or soaring birds. 
Beautiful, emotional, not too abstract.
{style}, masterpiece, highly detailed, sharp focus, rich colors, professional composition."""

# ====================== MAIN ======================
async def main():
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Market Museum Started")
        market_summary = get_market_summary()
        prompt = create_art_prompt(market_summary)

        print("Generating image with Imagen...")
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="4:5",
                output_mime_type="image/jpeg",
            ),
        )

        image_path = "market_museum_today.jpg"
        image_saved = False

        if response.generated_images:
            image_data = response.generated_images[0].image.image_bytes
            with open(image_path, "wb") as f:
                f.write(image_data)
            image_saved = True

        if not image_saved:
            print("❌ No image returned")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ No image generated today.")
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
