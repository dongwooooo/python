# main_gradio_mount.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import uvicorn

app = FastAPI(title="FastAPI + Gradio (mounted)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요시 제한
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    text: str

@app.post("/predict")
def predict(item: Item):
    txt = item.text.strip()
    return {"reversed": txt[::-1], "chars": len(txt)}

# --- Gradio UI 정의 ---
def ui_predict(user_text: str):
    # 같은 서버 내 엔드포인트 직접 호출 없이 로직을 복제하거나,
    # 실제론 내부 함수로 감싸 공유하는 패턴을 권장
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        r = c.post("/predict", json={"text": user_text})
        d = r.json()
    return f"Reversed: {d['reversed']}\nChars: {d['chars']}"

gradio_app = gr.Interface(fn=ui_predict, inputs="text", outputs="text", title="Mounted Gradio UI")

# /ui 경로에 마운트
app = gr.mount_gradio_app(app, gradio_app, path="/ui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
