import os
import imghdr
from datetime import datetime

def saveImg(image_bytes, original_filename):
    # Ensure directory exists
    save_dir = 'static/uploads'
    os.makedirs(save_dir, exist_ok=True)

    # Create a unique filename
    ext = imghdr.what(None, h=image_bytes) or 'png'
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{original_filename}"
    filepath = os.path.join(save_dir, filename)

    with open(filepath, 'wb') as f:
        f.write(image_bytes)

    # Return relative path to static dir and MIME type
    return f"uploads/{filename}", f"image/{ext}"
