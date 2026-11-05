import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# التوكن الجديد الخاص ببوتك مضمن مباشرة هنا
TOKEN = "8608740193:AAF4cCr3fVdXEqqfX2Awt1I2OpMUQTuy1Eo"
bot = telebot.TeleBot(TOKEN)

# تخزين مؤقت لخيارات البحث لكل مستخدم
user_search_filters = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "هلا بيك يا حسين! 🛠️ دزلي اسم الكلمة أو البحث اللي تريد تبحث عنه باليوتيوب.")

@bot.message_handler(func=lambda message: message.text and not message.text.startswith('http'))
def ask_for_filters(message):
    query = message.text
    user_search_filters[message.from_user.id] = {'query': query, 'filter': 'relevance'}
    
    # إنشاء الأزرار الشفافة للفلاتر (تشبه فلاتر اليوتيوب)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔍 الأكثر صلة", callback_data="filter|relevance"),
        InlineKeyboardButton("👀 عدد المشاهدات", callback_data="filter|view_count"),
        InlineKeyboardButton("⭐ تقييم عالي", callback_data="filter|rating"),
        InlineKeyboardButton("📅 الأحدث تحميلاً", callback_data="filter|date"),
        InlineKeyboardButton("🎬 فيديوهات طويلة", callback_data="filter|long"),
        InlineKeyboardButton("⚡ شورتس Shorts", callback_data="filter|short")
    )
    
    bot.reply_to(message, f"🎯 اختر فلتر البحث لـ: **{query}**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('filter|'))
def set_search_filter(call):
    user_id = call.from_user.id
    selected_filter = call.data.split('|')[1]
    
    if user_id not in user_search_filters:
        bot.answer_callback_query(call.id, "انتهت جلسة البحث، ابحث من جديد.")
        return
        
    query = user_search_filters[user_id]['query']
    bot.answer_callback_query(call.id, "جاري البحث في اليوتيوب...")
    bot.edit_message_text(f"🔍 جاي أبحث عن: **{query}** بالفلتر المطلوب...", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    search_query = f"ytsearch5:{query}"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'extract_flat': False,
        'noplaylist': True,
        'default_search': 'ytsearch5',
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            entries = info.get('entries', [])
            
        if not entries:
            bot.edit_message_text("ما لقيت نتائج بهذا البحث.", call.message.chat.id, call.message.message_id)
            return
            
        # عرض أول 5 نتائج مع أزرار لاختيار التحميل والجودة
        markup = InlineKeyboardMarkup()
        text = f"نتائج البحث عن: **{query}**\nاختر الفيديو للتحميل:\n\n"
        
        for i, entry in enumerate(entries[:5]):
            title = entry.get('title', 'بدون عنوان')
            text += f"{i+1}. {title}\n"
            markup.add(InlineKeyboardButton(f"تحميل رقم {i+1} 📥", callback_data=f"get_vid|{entry.get('id')}"))
            
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    except Exception as e:
        bot.edit_message_text(f"صار خطأ بالبحث: {e}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('get_vid|'))
def get_video_qualities(call):
    video_id = call.data.split('|')[1]
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    bot.answer_callback_query(call.id, "جاري جلب جودات الفيديو...")
    bot.edit_message_text("⚙️ جاي أجلب الجودات المتاحة لهذا الفيديو...", call.message.chat.id, call.message.message_id)
    
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
            bot.edit_message_text("عذراً، ما لقيت جودات مناسبة.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(f"📹 **{title}**\n\nاختر جودة التحميل:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            
    except Exception as e:
        bot.edit_message_text(f"خطأ بجلب الجودات: {e}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl|'))
def download_selected_quality(call):
    data_parts = call.data.split('|')
    format_id = data_parts[1]
    url = data_parts[2]
    
    bot.answer_callback_query(call.id, "جاري بدء التحميل...")
    bot.edit_message_text("⬇️ جاي أحمل الفيديو بالجودة المحددة، انتظر ثواني...", call.message.chat.id, call.message.message_id)
    
    output_template = 'downloaded_video.mp4'
    ydl_opts = {
        'format': f'{format_id}+bestaudio/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4'
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        bot.edit_message_text("⬆️ جاي أرفع الفيديو إلك...", call.message.chat.id, call.message.message_id)
        
        with open(output_template, 'rb') as video:
            bot.send_video(call.message.chat.id, video, caption="تم التحميل بنجاح بواسطة بوت حسين 🛠️")
            
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        if os.paths.exists(output_template) if hasattr(os, 'path') else os.path.exists(output_template):
            os.remove(output_template)
            
    except Exception as e:
        bot.send_message(call.message.chat.id, f"صار خطأ أثناء التحميل: {e}")

bot.infinity_polling()
