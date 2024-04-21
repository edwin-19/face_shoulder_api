from io import BytesIO
from PIL import Image

def byte_to_img(img_bytes:bytes):
    img = Image.open(BytesIO(img_bytes)).convert('RGB')
    return img
