from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# 1. अपने Telegram API details और Bot Token यहाँ डालें
API_ID = 30299119          
API_HASH = "c43280d05b671f854558c966385e76f0"
BOT_TOKEN = "8985306032:AAFqFhqX052egLhEzZElFPnqDpzvfYrizdo"

# 2. यहाँ अपना MongoDB Connection URL डालें (अनलिमिटेड फाइल्स सेव करने के लिए)
MONGO_URL = "mongodb+srv://kumarnautam8_db_user:w35V819UStPvSjQX@cluster0.qnsp151.mongodb.net/?compressors=zlib"

# 3. यहाँ अपने चारों प्राइवेट चैनल्स की Numeric IDs (-100 वाली) और इनवाइट लिंक्स डालें
CHANNEL_IDS = [-100111111111, -100222222222, -100333333333, -100444444444] 
CHANNEL_LINKS = [
    "https://t.me", 
    "https://t.me",
    "https://t.me",
    "https://t.me"
]

# बॉट और डेटाबेस का सेटअप
app = Client("unlimited_file_store", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["file_store_db"]
files_col = db["files"]

async def check_user_joined(client, user_id):
    """चेक करता है कि यूजर ने चारों चैनल्स जॉइन किए हैं या नहीं"""
    for ch_id in CHANNEL_IDS:
        try:
            await client.get_chat_member(ch_id, user_id)
        except UserNotParticipant:
            return False
        except Exception:
            return False
    return True

@app.on_message(filters.document | filters.video | filters.audio | filters.photo & filters.private)
async def store_file(client, message):
    """जब आप (बॉट के मालिक) कोई फाइल भेजेंगे, तो यह उसका यूनिक लिंक बनाएगा"""
    # नोट: सुरक्षा के लिए आप यहाँ अपना खुद का User ID चेक भी लगा सकते हैं
    file_type = message.media.value
    media_obj = getattr(message, file_type)
    file_id = media_obj.file_id
    
    # एक यूनिक सीक्रेट कोड बनाएं
    unique_code = str(uuid.uuid4())[:8]
    
    # डेटाबेस में सेव करें
    await files_col.insert_one({"code": unique_code, "file_id": file_id})
    
    # शेयर लिंक जनरेट करें
    bot_username = (await client.get_me()).username
    share_link = f"https://t.me{bot_username}?start={unique_code}"
    
    await message.reply_text(f"✅ **फाइल स्टोर हो गई है!**\n\n🔗 आपका शेयर लिंक:\n`{share_link}`\n\nइसे आप कहीं भी शेयर कर सकते हैं।")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    
    # अगर लिंक में कोई फाइल का कोड है
    if len(message.command) > 1:
        file_code = message.command[1]
        
        # पहले जॉइनिंग चेक करें
        is_joined = await check_user_joined(client, user_id)
        
        if not is_joined:
            # अगर जॉइन नहीं है, तो 4 चैनल के बटन और कोड के साथ Try Again बटन दिखाएं
            buttons = [
                [InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_LINKS[0])],
                [InlineKeyboardButton("📢 Join Channel 2", url=CHANNEL_LINKS[1])],
                [InlineKeyboardButton("📢 Join Channel 3", url=CHANNEL_LINKS[2])],
                [InlineKeyboardButton("📢 Join Channel 4", url=CHANNEL_LINKS[3])],
                [InlineKeyboardButton("🔄 Try Again", callback_data=f"check_{file_code}")]
            ]
            await message.reply_text(
                "Hey! Please Join All Our 4 Channels To Access The File!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            # अगर जॉइन है, तो डेटाबेस से फाइल ढूंढकर भेजें
            file_data = await files_col.find_one({"code": file_code})
            if file_data:
                await client.send_document(chat_id=message.chat.id, document=file_data["file_id"])
            else:
                await message.reply_text("❌ यह फाइल मौजूद नहीं है या डिलीट हो चुकी है।")
    else:
        await message.reply_text("हेलो! मैं एक अनलिमिटेड फाइल स्टोर बॉट हूँ। मुझे कोई भी फाइल भेजकर उसका शेयर लिंक प्राप्त करें।")

@app.on_callback_query(filters.regex(r"^check_"))
async def check_callback(client, callback_query):
    user_id = callback_query.from_user.id
    file_code = callback_query.data.split("_")[1]
    
    is_joined = await check_user_joined(client, user_id)
    
    if is_joined:
        await callback_query.message.delete()
        file_data = await files_col.find_one({"code": file_code})
        if file_data:
            await client.send_document(chat_id=callback_query.message.chat.id, document=file_data["file_id"])
    else:
        await callback_query.answer("⚠️ आपने अभी भी सभी 4 चैनल्स जॉइन नहीं किए हैं!", show_alert=True)

print("अनलिमिटेड फाइल स्टोर बॉट चालू है...")
app.run()
