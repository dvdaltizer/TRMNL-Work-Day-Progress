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
    "work hard. or just look busy.",
    "i'm not lazy. i'm on energy-saving mode.",
    "running on caffeine and bad decisions.",
    "teamwork makes the dream work… eventually.",
    "halfway through my give-a-damn quota.",
    "i'm not procrastinating. i'm prioritizing.",
    "stressed? who's stressed? i'm fine. fine!",
    "coffee: because murder is frowned upon.",
    "i survived another meeting that should've been an email.",
    "working from home: pajamas are business casual now.",
    "deadline approaching. panic level: moderate to severe.",
    "i put the 'pro' in procrastination."
]

def get_font_path():
    """Get the best available font path from the system."""
    if os.path.exists(FONT_PATH):
        return FONT_PATH
    
    for path in FALLBACK_FONT_PATHS:
        if os.path.exists(path):
            app.logger.info(f"Using fallback font: {path}")
            return path
    
    app.logger.warning("No suitable font found, using default")
    return None

def round_to_15(dt):
    """Round datetime to the nearest 15-minute interval."""
    m = 15 * round(dt.minute / 15)
    if m == 60:
        dt = dt.replace(minute=0) + timedelta(hours=1)
    else:
        dt = dt.replace(minute=m)
    return dt.replace(second=0, microsecond=0)

def calculate_work_progress(now):
    """Calculate work day progress as a percentage."""
    total_seconds = (datetime.combine(now.date(), WORK_END) - 
                    datetime.combine(now.date(), WORK_START)).total_seconds()
    
    elapsed_seconds = (datetime.combine(now.date(), now.time()) - 
                      datetime.combine(now.date(), WORK_START)).total_seconds()
    
    # Handle cases before work starts or after work ends
    if elapsed_seconds < 0:
        return 0.0
    elif elapsed_seconds > total_seconds:
        return 1.0
    else:
        return elapsed_seconds / total_seconds

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within the specified width."""
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
                # Single word is too long, force it on its own line
                lines.append(word)
        else:
            current_line = test_line
    
    if current_line:
        lines.append(current_line)
    
    return lines

def generate_image():
    """Generate the monochrome clock image with progress bar and quote."""
    try:
        timezone = request.args.get("timezone", "America/Chicago")
        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("America/Chicago")
        from_zone = pytz.utc
        to_zone = pytz.timezone('America/Chicago')  # change this to your desired timezone
        utc = datetime.utcnow().replace(tzinfo=from_zone)
        current_time = utc.astimezone(to_zone)
        # Add 15 minutes to stay ahead of schedule
        ahead_time = current_time + timedelta(minutes=15)
        now = round_to_15(ahead_time)


        progress = calculate_work_progress(now)
        
        # Create 1-bit monochrome image (white background)
        img = Image.new("1", (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        font_path = get_font_path()
        try:
            if font_path:
                font_big = ImageFont.truetype(font_path, 36)
                font_small = ImageFont.truetype(font_path, 12)
            else:
                font_big = ImageFont.load_default()
                font_small = ImageFont.load_default()
        except Exception as e:
            app.logger.warning(f"Font loading failed: {e}. Using default font.")
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw current time - centered at top
        time_str = now.strftime("%-I:%M %p")
        time_width = draw.textlength(time_str, font=font_big)
        time_x = (WIDTH - time_width) // 2
        draw.text((time_x, 15), time_str, font=font_big, fill=0)
        
        # Draw progress bar - perfectly centered
        bar_width = int(WIDTH * 0.75)  # Slightly narrower for better centering
        bar_height = 18
        bar_x = (WIDTH - bar_width) // 2
        bar_y = 70  # Moved up slightly
        fill_width = int(bar_width * progress)
        
        # Draw progress bar outline (centered)
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], outline=0, fill=255)
        # Draw progress bar fill
        if fill_width > 0:
            draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=0)
        
        # Draw progress percentage text - centered below bar
        progress_text = f"{int(progress * 100)}% of workday"
        progress_width = draw.textlength(progress_text, font=font_small)
        progress_x = (WIDTH - progress_width) // 2
        draw.text((progress_x, bar_y + 22), progress_text, font=font_small, fill=0)
        
        # Draw random snarky quote
        quote = random.choice(SNARKY_QUOTES)
        quote_lines = wrap_text(quote, font_small, WIDTH - 20, draw)
        
        # Position quote with better spacing from bottom
        line_height = 14
        total_quote_height = len(quote_lines) * line_height
        start_y = HEIGHT - total_quote_height - 25  # More space from bottom
        
        for i, line in enumerate(quote_lines):
            line_width = draw.textlength(line, font=font_small)
            line_x = (WIDTH - line_width) / 2
            line_y = start_y + (i * line_height)
            draw.text((line_x, line_y), line, font=font_small, fill=0)
        
        return img
        
    except Exception as e:
        app.logger.error(f"Error generating image: {e}")
        # Return a simple error image
        img = Image.new("1", (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(img)
        draw.text((10, HEIGHT//2), "Error generating image", fill=0)
        return img

@app.route("/")
def index():
    """Serve the main page with auto-refreshing image."""
    return render_template("index.html")

@app.route("/image.png")
def serve_image():
    """Generate and serve the monochrome clock image."""
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
    """TRMNL polling endpoint - returns image data when TRMNL polls."""
    try:
        app.logger.info(f"TRMNL polling from: {request.remote_addr} - Headers: {dict(request.headers)}")
        
        # Generate the clock image
        image = generate_image()
        
        # Convert to bytes and return as PNG
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
        # Return a simple error image
        error_img = Image.new("1", (WIDTH, HEIGHT), 255)
        draw = ImageDraw.Draw(error_img)
        draw.text((10, HEIGHT//2), "Error", fill=0)
        buf = io.BytesIO()
        error_img.save(buf, format="PNG")
        buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')

@app.route("/api/image", methods=["GET", "POST"])
def api_image():
    """Alternative endpoint for TRMNL - returns base64 encoded image."""
    try:
        app.logger.info(f"API image request from: {request.remote_addr}")
        
        # Generate the clock image
        image = generate_image()
        
        # Convert to base64
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
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
