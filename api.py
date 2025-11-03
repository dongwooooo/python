# api.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Simple API")

# (선택) CORS: 다른 포트의 UI(Gradio)에서 호출할 때 필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요시 도메인 제한
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    text: str

@app.get("/")
def root():
    return {"ok": True, "msg": "Use POST /predict"}

@app.post("/predict")
def predict(item: Item):
    # 여기에 실제 모델/로직을 넣으면 됨
    length = len(item.text.strip())
    return {"input": item.text, "length": length, "label": "POSITIVE" if length % 2 == 0 else "NEGATIVE"}
