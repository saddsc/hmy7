import os, json, requests, traceback
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message

api_id = int(os.environ.get("API_ID", 25543540))
api_hash = os.environ.get("API_HASH", "06d6f15b55b341e2220828b2804b2a4f")
bot_token = os.environ.get("BOT_TOKEN", "8121347476:AAGoEl7W-xz87XqWVBPlbPmTMgc9mmTFcK0")

app = Client("protection_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

stats_file = "stats.json"
if os.path.exists(stats_file) and os.path.getsize(stats_file) > 0:
    with open(stats_file, "r") as f:
        stats = json.load(f)
else:
    stats = {
        "banned": 0,
        "nudity_detected": 0,
        "files_deleted": 0,
        "edited_deleted": 0
    }

def save_stats():
    with open(stats_file, "w") as f:
        json.dump(stats, f)

banned_name_words = ["sex", "porn", "nude", "xxx", "rape", "18+", "fuck"]

async def get_admins_text(chat_id):
    try:
        admin_mentions = []
        i = 1
        async for member in app.get_chat_members(chat_id, filter="administrators"):
            user = member.user
            name = user.first_name or "مشرف"
            mention = f"{i}- {name} (ID: {user.id})"
            admin_mentions.append(mention)
            i += 1
        return "\n".join(admin_mentions)
    except Exception as e:
        print("فشل جلب المشرفين:", e)
        return "⚠️ لم يتم جلب المشرفين"

async def notify_owner_and_dev(chat_id, user, reason):
    try:
        owner = None
        async for member in app.get_chat_members(chat_id, filter="administrators"):
            if member.status == "owner":
                owner = member.user
                break

        msg = f"""🚨 تم اتخاذ إجراء في القروب:
- المستخدم: {user.first_name} (@{user.username or 'لايوجد'})
- السبب: {reason}
- ID: {user.id}
- المجموعة: {chat_id}
"""

        await app.send_message("ddiir", msg)
        if owner:
            await app.send_message(owner.id, msg)
    except:
        pass

async def ban_user_and_alert(chat_id, user, reason="مخالفة"):
    username = f"@{user.username}" if user.username else user.first_name
    try: await app.ban_chat_member(chat_id, user.id)
    except: pass
    stats["banned"] += 1
    save_stats()
    admin_text = await get_admins_text(chat_id)
    alert = f"""⚠️ تحذير ابن الحمير : {username}
أرسل {reason} وتم حذف رسالته وطرده من القروب مباشره.
{admin_text}
🔔"""
    await app.send_message(chat_id, alert)
    await notify_owner_and_dev(chat_id, user, reason)

async def warn_user_and_alert(chat_id, user, reason="مخالفة"):
    username = f"@{user.username}" if user.username else user.first_name
    admin_text = await get_admins_text(chat_id)
    alert = f"""⚠️ تنبيه للمخالف : {username}
{reason}
{admin_text}
🔔"""
    await app.send_message(chat_id, alert)

@app.on_message(filters.photo)
async def scan_photo(client, message):
    try:
        file_path = await message.download(file_name="downloads/scan.jpg")
        params = {
            'models': 'nudity-2.1,weapon,recreational_drug,medical,text-content,face-attributes,self-harm',
            'api_user': os.environ.get("SIGHTENGINE_USER", "920678863"),
            'api_secret': os.environ.get("SIGHTENGINE_SECRET", "YpBa4TehSqJQB6TXqBCsGPZZgtuFL4cn")
        }
        with open(file_path, 'rb') as media_file:
            r = requests.post('https://api.sightengine.com/1.0/check.json', files={'media': media_file}, data=params)
        result = r.json()

        nudity_score = result.get("nudity", {}).get("sexual_activity", 0) * 100
        weapon_score = result.get("weapon", {}).get("prob", 0) * 100
        drug_score = result.get("recreational_drug", {}).get("prob", 0) * 100

        print(f"Nudity: {nudity_score:.2f}% | Weapon: {weapon_score:.2f}% | Drug: {drug_score:.2f}%")

        if nudity_score > 20 or weapon_score > 20 or drug_score > 20:
            await message.delete()
            stats["nudity_detected"] += 1
            save_stats()
            await ban_user_and_alert(message.chat.id, message.from_user, "صورة مخالفة")

    except Exception:
        traceback.print_exc()
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

@app.on_message(filters.text)
async def check_name_and_links(client, message):
    try:
        lowered_name = (message.from_user.first_name or "").lower()
        if any(bad in lowered_name for bad in banned_name_words):
            await message.delete()
            await ban_user_and_alert(message.chat.id, message.from_user, "اسم المستخدم يحتوي على كلمات ممنوعة")
            return

        if message.text:
            lowered = message.text.lower()
            image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
            if any(ext in lowered for ext in image_exts):
                await message.delete()
                await ban_user_and_alert(message.chat.id, message.from_user, "رابط صورة مباشرة")
    except Exception:
        traceback.print_exc()

# هذا يسمح بالفيديوهات العادية، ويحظر فقط الملفات والـ GIF
@app.on_message(filters.document | filters.animation)
async def block_documents(client, message):
    try:
        await message.delete()
        stats["files_deleted"] += 1
        save_stats()
        await warn_user_and_alert(message.chat.id, message.from_user, "تم حذف الملف، إرسال الملفات ممنوع.")
    except Exception:
        traceback.print_exc()

@app.on_edited_message()
async def handle_edited(client, message):
    try:
        now = datetime.utcnow()
        msg_time = message.date.replace(tzinfo=None)
        if now - msg_time > timedelta(minutes=5):
            await message.delete()
            stats["edited_deleted"] += 1
            save_stats()
            await warn_user_and_alert(message.chat.id, message.from_user, "تم تعديل رسالة قديمة بعد أكثر من 5 دقائق وتم حذفها.")
            await notify_owner_and_dev(message.chat.id, message.from_user, "تعديل متأخر على رسالة")
            return

        if message.photo or message.video or message.document or message.animation:
            await message.delete()
            stats["edited_deleted"] += 1
            save_stats()
            await ban_user_and_alert(message.chat.id, message.from_user, "تعديل الرسالة إلى وسائط مخالفة")

        elif message.text and any(ext in message.text.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]):
            await message.delete()
            stats["edited_deleted"] += 1
            save_stats()
            await ban_user_and_alert(message.chat.id, message.from_user, "تعديل الرسالة إلى رابط صورة مشبوه")

    except Exception:
        traceback.print_exc()

@app.on_message(filters.command("احصائيات"))
async def stats_command(client, message):
    if message.from_user.id != 1419403233:
        return
    text = f"""
📊 إحصائيات الحماية:

- عدد المطرودين: {stats['banned']}
- الصور الإباحية المكتشفة: {stats['nudity_detected']}
- الملفات المحذوفة: {stats['files_deleted']}
- الرسائل المعدلة المحذوفة: {stats['edited_deleted']}
"""
    await message.reply(text)

print("✅ البوت يعمل الآن وجاهز للحماية!")
app.run()