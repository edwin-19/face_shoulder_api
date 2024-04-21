from fastapi import APIRouter, Form, UploadFile, responses
from typing import Union
from utils.img_utils import byte_to_img
from net.detector import Detector
import cv2
import numpy as np
from model.face import FaceResponse

engine_route = APIRouter(prefix="/engine")
detector = Detector()

@engine_route.get("/")
def index_engine():
    return "Engine Route Face"

@engine_route.post("/face_det")
async def get_face_shoulder_coord(
    engine_type:str=Form(...),
    image: Union[UploadFile, None] = None
):
    if image is not None:
        try:
            contents = await image.read()
            img = np.array(byte_to_img(contents))
            
            if engine_type == "gray":
                img = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2BGR)
                
            box = detector.predict(img)
            if len(box) > 0:
                box = box[0][:4]
                
            box = np.array(box).astype(int).tolist()
            return FaceResponse(message="Sucesss", coords=box)
        except Exception as err:
            return FaceResponse(status=400, message="Failed: {}".format(err), coords=[0,0,0,0])