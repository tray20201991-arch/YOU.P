import os
import telebot
from telebot.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# التوكن الخاص ببوتك
TOKEN = "8608740193:AAF4cCr3fVdXEqqfX2Awt1I2OpMUQTuy1Eo"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "هلا بيك يا حسين! 🛠️ بوت الإنلاين مود صار يدعم نتائج بحث واسعة وضخمة تصل إلى 50 نتيجة بالبحث الواحد. اكتب اسم البوت بأي محادثة وابحث فوري!")

# استقبال الروابط (فيديو أو قائمة تشغيل Playlist) مباشرة
@bot.message_handler(func=lambda message: message.text and message.text.startswith('http'))
def handle_urls(message):
    url = message.text
    msg = bot.reply_to(message, "🔍 ديصير فحص الرابط وجلب التفاصيل...")
    
    ydl_opts = {'extract_flat': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        if 'entries' in info:
            playlist_title = info.get('title', 'قائمة تشغيل')
            entries = info.get('entries', [])
            text = f"📂 **قائمة تشغيل:** {playlist_title}\nعدد الفيديوهات الكلي: {len(entries)}\n\nاختر الفيديو للتحميل:"
            markup = InlineKeyboardMarkup()
            for i, entry in enumerate(entries[:50]): # عرض لحد 50 فيديو من البلاي ليست
                vid_id = entry.get('id')
                title = entry.get('title', f'فيديو {i+1}')
                if vid_id:
                    markup.add(InlineKeyboardButton(f"📥 {title[:35]}...", callback_data=f"get_vid|{vid_id}"))
            bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode="Markdown")
            return

        video_id = info.get('id')
        show_qualities_by_id(message.chat.id, message.message_id, f"https://www.youtube.com/watch?v={video_id}")

    except Exception as e:
        bot.edit_message_text(f"صار خطأ أثناء قراءة الرابط: {e}", message.chat.id, message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('get_vid|'))
def get_video_qualities_callback(call):
    video_id = call.data.split('|')[1]
    url = f"https://www.youtube.com/watch?v={video_id}"
    bot.answer_callback_query(call.id, "جاري جلب الجودات...")
    show_qualities_by_id(call.message.chat.id, call.message.message_id, url)

def show_qualities_by_id(chat_id, message_id, url):
    bot.edit_message_text("⚙️ جاي أجلب الجودات المتاحة...", chat_id, message_id)
    ydl_opts = {'extract_flat': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        title = info.get('title', 'فيديو')
        formats = info.get('formats', [])
        
        markup = InlineKeyboardMarkup()
        added_resolutions = set()
        
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('resolution') and f.get('ext') == 'mp4':
                res = f.get('resolution')
                format_id = f.get('format_id')
                note = f.get('format_note', '')
                
                if res not in added_resolutions:
                    added_resolutions.add(res)
                    btn_text = f"جودة: {res} ({note})" if note else f"جودة: {res}"
                    callback_data = f"dl|{format_id}|{url}"
                    if len(callback_data.encode('utf-8')) <= 64:
                        markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

        if not markup.keyboard:
            bot.edit_message_text("عذراً، ما لقيت جودات مناسبة.", chat_id, message_id)
        else:
            bot.edit_message_text(f"📹 **{title}**\n\nاختر جودة التحميل:", chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
            
    except Exception as e:
        bot.edit_message_text(f"خطأ بجلب الجودات: {e}", chat_id, message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl|'))
def download_selected_quality(call):
    data_parts = call.data.split('|')
    format_id = data_parts[1]
    url = data_parts[2]
    
    bot.answer_callback_query(call.id, "جاري بدء التحميل...")
    bot.edit_message_text("⬇️ جاي أحمل الفيديو بالجودة المحددة...", call.message.chat.id, call.message.message_id)
    
    output_template = 'downloaded_video.mp4'
    ydl_opts = {
        'format': f'{format_id}+bestaudio/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4'
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        bot.edit_message_text("⬆️ جاي أرفع الفيديو...", call.message.chat.id, call.message.message_id)
        
        with open(output_template, 'rb') as video:
            bot.send_video(call.message.chat.id, video, caption="تم التحميل بنجاح بواسطة بوت حسين 🛠️")
            
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        if os.path.exists(output_template):
            os.remove(output_template)
            
    except Exception as e:
        bot.send_message(call.message.chat.id, f"صار خطأ أثناء التحميل: {e}")

# نظام البحث السريع (Inline Mode) مع رفع الحد الأقصى للنتائج إلى 50 نتيجة
@bot.inline_handler(lambda query: True)
def inline_search(query):
    text = query.query.strip()
    results = []
    
    if not text:
        results.append(
            InlineQueryResultArticle(
                id="help",
                title="🔍 اكتب اسم الكلمة أو رابط البلاي ليست للبحث الموسع",
                input_message_content=InputTextMessageContent("يرجى كتابة الكلمة المطلوبة بعد معرف البوت."),
                description="مثال: @BotName قرآَن كريم"
            )
        )
        bot.answer_inline_query(query.id, results, cache_time=1)
        return

    ydl_opts = {'format': 'best[ext=mp4]/best', 'extract_flat': True, 'noplaylist': False}
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            # رفع عدد نتائج البحث المطلوبة من يوتيوب إلى 50 نتيجة (الحد الأقصى لمدى الإنلاين في تليغرام)
            info = ydl.extract_info(f"ytsearch50:{text}", download=False)
            entries = info.get('entries', [])
            
        for i, entry in enumerate(entries):
            res_id = entry.get('id')
            if not res_id:
                continue
            title = entry.get('title', 'نتيجة بحث يوتيوب')
            thumbnail = entry.get('thumbnail', '')
            
            if 'entries' in entry or entry.get('_type') == 'playlist':
                playlist_url = f"https://www.youtube.com/playlist?list={res_id}"
                results.append(
                    InlineQueryResultArticle(
                        id=f"pl_{i}_{res_id}",
                        title=f"📂 [قائمة تشغيل] {title}",
                        input_message_content=InputTextMessageContent(f"📂 تم اختيار قائمة التشغيل:\n{playlist_url}\n\nيرجى إرسال الرابط للبوت مباشرة لعرض وتنزيل محتواها!"),
                        description="اضغط لإرسال رابط قائمة التشغيل هذه",
                        thumb_url=thumbnail
                    )
                )
            else:
                url = f"https://www.youtube.com/watch?v={res_id}"
                duration = entry.get('duration', 0)
                
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("📥 تحميل الفيديو", callback_data=f"get_vid|{res_id}"),
                    InlineKeyboardButton("🌐 فتح الرابط", url=url)
                )
                
                results.append(
                    InlineQueryResultArticle(
                        id=f"vid_{i}_{res_id}",
                        title=title,
                        input_message_content=InputTextMessageContent(f"📹 **{title}**\n🔗 الرابط: {url}\n\nاضغط على الزر أدناه للتحميل بالجودة المطلوبة 👇"),
                        description=f"المدة: {duration} ثانية | اضغط للإرسال والاختيار",
                        thumb_url=thumbnail,
                        reply_markup=markup
                    )
                )
                
        bot.answer_inline_query(query.id, results, cache_time=1)
    except Exception as e:
        print(f"Inline Playlist Error: {e}")

bot.infinity_polling()
