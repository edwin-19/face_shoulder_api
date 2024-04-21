from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from configs import origins
from router.engine import engine_route

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engine_route)

@app.get("/")
def get_index():
    return "Running normally seg server"