# app_gradio.py
import gradio as gr
import requests

API_URL = "http://127.0.0.1:8000/predict"

def call_api(user_text: str):
    try:
        resp = requests.post(API_URL, json={"text": user_text}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return f"Label: {data['label']}\nLength: {data['length']}\nEcho: {data['input']}"
    except Exception as e:
        return f"Error: {e}"

with gr.Blocks(title="Gradio → FastAPI (separate servers)") as demo:
    gr.Markdown("### 별도 API 서버로 POST 호출하는 Gradio UI")
    inp = gr.Textbox(label="Enter text")
    out = gr.Textbox(label="Result", lines=4)
    btn = gr.Button("Predict")
    btn.click(call_api, inputs=inp, outputs=out)

if __name__ == "__main__":
    # 먼저 api.py를 8000포트로 실행해둔 상태여야 함
    demo.launch(server_name="0.0.0.0", server_port=7860)
