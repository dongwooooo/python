# gradio_fastapi_twoservers.py
import threading
import time
import gradio as gr
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ---------- FastAPI (Backend) ----------
api = FastAPI(title="Backend API")
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    text: str

@api.post("/predict")
def predict(item: Item):
    txt = item.text.strip()
    return {"input": txt, "length": len(txt), "upper": txt.upper()}

def run_fastapi():
    uvicorn.run(api, host="0.0.0.0", port=8000, log_level="info")

# ---------- Gradio (Frontend) ----------
API_URL = "http://127.0.0.1:8000/predict"

def call_api(user_text: str):
    r = requests.post(API_URL, json={"text": user_text}, timeout=10)
    r.raise_for_status()
    d = r.json()
    return f"Upper: {d['upper']}\nLength: {d['length']}"

def run_gradio():
    with gr.Blocks(title="Two Servers Demo") as demo:
        gr.Markdown("### 같은 스크립트에서 Backend(8000) + Frontend(7860) 동시 구동")
        t = gr.Textbox(label="Text")
        o = gr.Textbox(label="Result", lines=3)
        gr.Button("Send").click(call_api, inputs=t, outputs=o)
    demo.launch(server_name="0.0.0.0", server_port=7860, prevent_thread_lock=True)

if __name__ == "__main__":
    th_api = threading.Thread(target=run_fastapi, daemon=True)
    th_api.start()
    time.sleep(0.5)  # API 부팅 대기
    run_gradio()
    # Ctrl+C로 종료
