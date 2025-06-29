import os
import logging
from flask import Flask, send_file, render_template, request
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, time, timedelta
import random
import io
import pytz

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Display configuration
WIDTH, HEIGHT = 264, 176
WORK_START = time(9, 0)
WORK_END = time(17, 0)

# Font path - fallback to a common system font if DejaVu is not available
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FALLBACK_FONT_PATHS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/System/Library/Fonts/Arial.ttf",  # macOS
    "C:\\Windows\\Fonts\\arial.ttf"      # Windows
]

# Snarky workplace quotes
SNARKY_QUOTES = [
    "meetings: the practical alternative to work.",
    "i love deadlines. i like the whooshing sound they make as they fly by.",
    "my job is secure. no one else wants it.",
    "professional at googling things.",
    "i pretend to work. they pretend to pay me.",
    "multitasking: messing up several things at once.",
    "error 404: motivation not found.",
    "brb, mentally clocked out.",
    "let me overthink this real quick.",
    "every day is bring your sarcasm to work day.",
    "today’s forecast: 99% chance of caffeine dependency.",
    "fun fact: i'm not listening.",
    "you can't fire me, i'm already not doing anything.",
    "currently out of my mind — please leave a message.",
    "i'm not arguing. i'm just explaining why i'm right.",
    "work hard. or just look busy.",
    "i'm not lazy. i'm on energy-saving mode.",
    "running on caffeine and bad decisions.",
    "teamwork makes the dream work… eventually.",
    "i'm not procrastinating. i'm prioritizing.",
    "stressed? who's stressed? i'm fine. fine!",
    "i survived another meeting that should've been an email.",
    "deadline approaching. panic level: moderate to severe.",
    "i put the 'pro' in procrastination.",
    "working hard, or hardly working? yes.",
    "just here for the wi-fi.",
    "if i were paid to procrastinate, i'd be a billionaire.",
    "i’m not sure if this is a job or a social experiment.",
    "my work ethic is directly tied to how much coffee i’ve had.",
    "teamwork makes the dream work... as long as the dream is napping.",
    "overqualified, underpaid, still here.",
    "i’m not late — i’m on ‘creative timing.’",
    "i followed my passion. it led me to the break room.",
    "my soul left this zoom meeting 15 minutes ago.",
    "i don't always work, but when i do, i immediately need a break.",
]

def get_font_path():
    if os.path.exists(FONT_PATH):
        return FONT_PATH
    for path in FALLBACK_FONT_PATHS:
        if os.path.exists(path):
            app.logger.info(f"Using fallback font: {path}")
            return path
    app.logger.warning("No suitable font found, using default")
    return None

def round_to_15(dt):
    m = 15 * round(dt.minute / 15)
    if m == 60:
        dt = dt.replace(minute=0) + timedelta(hours=1)
    else:
        dt = dt.replace(minute=m)
    return dt.replace(second=0, microsecond=0)

def calculate_work_progress(now):
    total_seconds = (datetime.combine(now.date(), WORK_END) - datetime.combine(now.date(), WORK_START)).total_seconds()
    elapsed_seconds = (datetime.combine(now.date(), now.time()) - datetime.combine(now.date(), WORK_START)).total_seconds()
    if elapsed_seconds < 0:
        return 0.0
    elif elapsed_seconds > total_seconds:
        return 1.0
    else:
        return elapsed_seconds / total_seconds

def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = (current_line + " " + word).strip()
        if draw.textlength(test_line, font=font) > max_width:
            if current_line:
                lines.append(current_line)
                current_line = word
            else:
                lines.append(word)
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines

def generate_image():
    try:
        timezone = request.args.get("timezone", "America/Chicago")
        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("America/Chicago")
        now = datetime.now(tz)
        now = round_to_15(now + timedelta(minutes=15))
        progress = calculate_work_progress(now)

        img = Image.new("1", (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(img)
        font_path = get_font_path()
        try:
            font_big = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
            font_small = ImageFont.truetype(font_path, 12) if font_path else ImageFont.load_default()
        except:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        time_str = now.strftime("%-I:%M %p")
        time_x = (WIDTH - draw.textlength(time_str, font=font_big)) // 2
        draw.text((time_x, 15), time_str, font=font_big, fill=0)

        bar_width = int(WIDTH * 0.75)
        bar_height = 18
        bar_x = (WIDTH - bar_width) // 2
        bar_y = 70
        fill_width = int(bar_width * progress)
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], outline=0, fill=255)
        if fill_width > 0:
            draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=0)

        progress_text = f"{int(progress * 100)}% of workday"
        progress_x = (WIDTH - draw.textlength(progress_text, font=font_small)) // 2
        draw.text((progress_x, bar_y + 22), progress_text, font=font_small, fill=0)

        quote = random.choice(SNARKY_QUOTES)
        quote_lines = wrap_text(quote, font_small, WIDTH - 20, draw)
        start_y = HEIGHT - (len(quote_lines) * 14) - 25
        for i, line in enumerate(quote_lines):
            line_x = (WIDTH - draw.textlength(line, font=font_small)) / 2
            draw.text((line_x, start_y + i * 14), line, font=font_small, fill=0)

        return img

    except Exception as e:
        app.logger.error(f"Error generating image: {e}")
        img = Image.new("1", (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(img)
        draw.text((10, HEIGHT//2), "Error generating image", fill=0)
        return img

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/image.png")
def serve_image():
    try:
        image = generate_image()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")
    except Exception as e:
        app.logger.error(f"Error serving image: {e}")
        return "Error generating image", 500

@app.route("/webhook", methods=["GET", "POST"])
def trmnl_webhook():
    try:
        app.logger.info(f"TRMNL polling from: {request.remote_addr} - Headers: {dict(request.headers)}")
        image = generate_image()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        from flask import Response
        response = Response(buf.getvalue(), mimetype='image/png')
        response.headers['Content-Type'] = 'image/png'
        response.headers['Cache-Control'] = 'no-cache'
        return response
    except Exception as e:
        app.logger.error(f"Error generating TRMNL response: {e}")
        img = Image.new("1", (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(img)
        draw.text((10, HEIGHT//2), "Error", fill=0)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')

@app.route("/api/image", methods=["GET", "POST"])
def api_image():
    try:
        app.logger.info(f"API image request from: {request.remote_addr}")
        image = generate_image()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_data = buf.getvalue()
        import base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        return {
            "image": image_b64,
            "format": "png",
            "width": WIDTH,
            "height": HEIGHT,
            "refresh_rate": 900
        }
    except Exception as e:
        app.logger.error(f"Error generating API image: {e}")
        return {"error": str(e)}, 500

@app.route("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
