from pydantic import BaseModel
from model.base_response import BaseResponse
from typing import List

class FaceResponse(BaseResponse):
    coords:List[int]=[]