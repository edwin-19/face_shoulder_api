from pydantic import BaseModel

class BaseResponse(BaseModel):
    status:int=200
    message:str=""