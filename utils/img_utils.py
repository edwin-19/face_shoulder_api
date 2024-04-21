from io import BytesIO
from PIL import Image
import torch

def byte_to_img(img_bytes:bytes):
    img = Image.open(BytesIO(img_bytes)).convert('RGB')
    return img