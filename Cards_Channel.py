import requests
import json
import telebot
import time

# بيانات تسجيل الدخول
num = "01060972975"
password = "ABcd@_11"
url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
data = {
    "username": num,
    "password": password,
    "grant_type": "password",
    "client_secret": "a2ec6fff-0b7f-4aa4-a733-96ceae5c84c3",
    "client_id": "my-vodafone-app"
}
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "okhttp/4.9.1"
}

# بيانات بوت تيليجرام
BOT_TOKEN = "7100725807:AAHijQI3bezS57lo5esKU0ba9aGtBUUIPUM"
CHAT_ID = "@Hadidy2"
bot = telebot.TeleBot(BOT_TOKEN)

# قاموس لتخزين الكروت المرسلة
# المفتاح: رقم الكارت
# القيمة: قاموس يحتوي على message_id والعدد الأخير للشحنات (remaining) والـ unit
sent_cards = {}

def get_token():
    """دالة للحصول على التوكن من السيرفر"""
    response = requests.post(url, data=data, headers=headers)
    if response.status_code != 200:
        print("فشل في الحصول على التوكن:", response.text)
        return None
    return response.json().get("access_token")

# استخراج التوكن للمرة الأولى وتخزين توقيت الحصول عليه
token = get_token()
if token is None:
    exit()
token_timestamp = time.time()  # حفظ وقت الحصول على التوكن

while True:
    # تحديث التوكن كل 5 دقائق (300 ثانية)
    if time.time() - token_timestamp > 300:
        new_token = get_token()
        if new_token is not None:
            token = new_token
            token_timestamp = time.time()
            print("تم تحديث التوكن.")
        else:
            print("تعذر تحديث التوكن، سيتم المحاولة لاحقاً.")
    
    # إعداد بيانات الطلب لجلب الكروت
    api_url = f"https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion?%40type=RamadanHub&channel=website&msisdn={num}"
    api_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 9; CPH1923 Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.121 Mobile Safari/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "msisdn": num,
        "clientId": "WebsiteConsumer",
        "api-host": "PromotionHost",
        "channel": "APP_PORTAL"
    }

    response = requests.get(api_url, headers=api_headers)
    if response.status_code != 200:
        print("فشل في جلب البيانات:", response.text)
    else:
        try:
            data_response = response.json()
        except json.JSONDecodeError:
            print("فشل في فك تشفير البيانات المستلمة")
            data_response = None

        # مجموعة لتخزين الكروت الحالية المستلمة من البيانات
        current_cards = set()

        # التحقق من وجود بيانات الكروت
        if (isinstance(data_response, list) and len(data_response) > 1 
                and "pattern" in data_response[1]):
            mz = data_response[1]["pattern"]
            for i in mz:
                if "action" in i and i["action"] and "characteristics" in i["action"][0]:
                    characteristics = i["action"][0]["characteristics"]
                    card = None
                    unit = None
                    remaining = None

                    for char in characteristics:
                        if char["name"] == "CARD_SERIAL":
                            card = char["value"]
                        elif char["name"] == "GIFT_UNITS":
                            try:
                                unit = int(char["value"])
                            except ValueError:
                                unit = 0
                        elif char["name"] == "REMAINING_DEDICATIONS":
                            remaining = char["value"]

                    if card and unit and remaining and unit > 100:
                        if not card.startswith("0"):
                            current_cards.add(card)  # حفظ الكارت ضمن الكروت الحالية
                            message_text = (f"كارت بقيمة • {unit} • وحدة 🔥❤️\n\n"
                                            f"الكارت : `*858*{card}#` ✓\n\n"
                                            f"عدد الشحنات : • {remaining} •\n\n"
                                            "❤️رمضان مبارك❤️\n\n"
                                            "بواسطة : @Hadidy2")
                            
                            # إذا لم يتم إرسال الكارت من قبل، يتم إرساله وتخزين بياناته
                            if card not in sent_cards:
                                sent = bot.send_message(CHAT_ID, message_text, parse_mode="Markdown")
                                print(f"تم إرسال الكارت إلى تيليجرام: {card} , {unit}")
                                sent_cards[card] = {"message_id": sent.message_id, "remaining": remaining, "unit": unit}
                            else:
                                # إذا كان الكارت موجوداً مسبقاً، نقارن قيمة الشحنات وإذا تغيرت يتم التعديل
                                if sent_cards[card]["remaining"] != remaining:
                                    try:
                                        bot.edit_message_text(chat_id=CHAT_ID,
                                                              message_id=sent_cards[card]["message_id"],
                                                              text=message_text,
                                                              parse_mode="Markdown")
                                        print(f"تم تحديث الكارت: {card}")
                                        sent_cards[card]["remaining"] = remaining
                                    except Exception as e:
                                        print(f"فشل تحديث الكارت {card}: {e}")
                                else:
                                    print(f"لا يوجد تغيير في عدد الشحنات للكارت: {card}")
        else:
            bot.send_message(CHAT_ID, "❌ لا توجد بيانات كروت متاحة")
            print("لا توجد بيانات كروت متاحة")
        
        # حذف الكروت التي سبق إرسالها ولكن لم تعد موجودة في البيانات الجديدة
        for card in list(sent_cards.keys()):
            if card not in current_cards:
                try:
                    bot.delete_message(CHAT_ID, sent_cards[card]["message_id"])
                    print(f"تم حذف الكارت {card} لأنه لم يعد موجوداً في البيانات.")
                except Exception as e:
                    print(f"فشل حذف الكارت {card}: {e}")
                # إزالة الكارت من القاموس
                del sent_cards[card]
    
    # الانتظار 20 ثانية قبل التحديث التالي
    time.sleep(15)