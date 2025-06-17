import os
import imghdr
from datetime import datetime

def saveImg(image_bytes, original_filename):
    save_dir = 'static/uploads'
    os.makedirs(save_dir, exist_ok=True)

    ext = imghdr.what(None, h=image_bytes) or 'png'
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{original_filename}"
    filepath = os.path.join('app/' + save_dir, filename)

    with open(filepath, 'wb') as f:
        f.write(image_bytes)

    return f"uploads/{filename}", f"image/{ext}"
