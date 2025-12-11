# app.py — Streamlit UI (sidebar) with correct image/audio handling
import streamlit as st
import requests
import json
import time
import base64
from typing import List

# ----------------------------
# Configuration
# ----------------------------
WEBHOOK_URL = "https://sp12012012.app.n8n.cloud/webhook-test/multi"
AVAILABLE_MODELS = [
    {"id": "gpt4o", "title": "GPT-4o", "desc": "High-capacity LLM"},
    {"id": "gpt4o-mini", "title": "GPT-4o Mini", "desc": "Faster, cheaper LLM"},
    {"id": "whisper", "title": "Whisper", "desc": "Audio → text transcription"},
    {"id": "gpt4o-vision", "title": "Vision", "desc": "Image understanding"}
]

# ----------------------------
# Page setup & CSS (dark + sidebar)
# ----------------------------
st.set_page_config(page_title="n8n Multi — Sidebar UI", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    .stApp { background: #0b0f12; color: #e6eef6; font-family: Inter, sans-serif; }
    .header-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
        border-radius: 12px; padding: 18px; margin-bottom: 14px; border:1px solid rgba(255,255,255,0.03);
    }
    .avatar { width:34px; height:34px; border-radius:8px; background: linear-gradient(90deg,#fb923c,#ef4444); display:inline-block; margin-right:12px;}
    .muted { color:#9fb0c8; font-size:13px; }
    .results-card { background:#071018; border-radius:10px; padding:14px; border:1px solid rgba(255,255,255,0.03); }
    .resp-card { background: transparent; border-radius:8px; padding:10px; margin-bottom:10px; border:1px solid rgba(255,255,255,0.02); }
    .resp-title { font-weight:700; color:#e6eef6; font-size:14px; }
    .resp-lat { color:#93aec6; font-size:12px; }
    .muted-small { color:#93aec6; font-size:12px; }
    .sidebar .stButton>button { background: linear-gradient(90deg,#4ade80,#60a5fa); color:#06202e; font-weight:700; border-radius:8px; }
    .stTextArea textarea { background: #061018 !important; color: #e6eef6 !important; border: 1px solid rgba(255,255,255,0.03) !important; border-radius:8px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Sidebar — controls
# ----------------------------
st.sidebar.markdown(
    "<div style='display:flex; align-items:center; gap:12px;'><div style='width:34px;height:34px;border-radius:8px;background:linear-gradient(90deg,#fb923c,#ef4444)'></div>"
    "<div><b style='font-size:16px'>n8n Multi — Controls</b><div class='muted' style='margin-top:4px'>Select models & input, then run.</div></div></div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

# Webhook (editable in sidebar)
webhook_input = st.sidebar.text_input("Webhook URL", value=WEBHOOK_URL)

# Models
st.sidebar.markdown("**Models**")
selected_models = []
for m in AVAILABLE_MODELS:
    key = f"mdl_{m['id']}"
    # default GPT-4o checked
    default_checked = True if m['id'] == "gpt4o" else False
    checked = st.sidebar.checkbox(f"{m['title']} — {m['desc']}", value=st.session_state.get(key, default_checked), key=key)
    if checked:
        selected_models.append(m['id'])

# ensure at least one model
if not selected_models:
    st.sidebar.warning("Select at least one model — defaulting to GPT-4o.")
    st.session_state["mdl_gpt4o"] = True
    selected_models = ["gpt4o"]

st.sidebar.markdown("---")
st.sidebar.markdown("**Input Type**")
input_type = st.sidebar.radio("", options=["text", "image", "audio"], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("**Prompt (optional)**")
prompt_text = st.sidebar.text_area("", value="", height=120, key="sidebar_prompt")

uploaded_file = None
if input_type in ("image", "audio"):
    uploaded_file = st.sidebar.file_uploader(f"Upload {input_type} file", type=None, key="sidebar_upload")
    if uploaded_file is not None:
        st.sidebar.markdown(f"<div class='muted-small'>Uploaded: <b>{uploaded_file.name}</b></div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
run = st.sidebar.button("🚀 Run Models", key="sidebar_run", help="Send request to n8n")
st.sidebar.markdown(f"<div class='muted-small'>Webhook: edit if needed</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='muted-small'>{webhook_input}</div>", unsafe_allow_html=True)

# ----------------------------
# Main area
# ----------------------------
st.markdown(
    "<div class='header-card'><div style='display:flex;align-items:center'><div class='avatar'></div>"
    "<div><div style='font-size:18px;font-weight:700;color:#fff'>n8n Multi-Model UI — Sidebar</div>"
    "<div class='muted' style='margin-top:6px'>Clean UI: controls in sidebar, results here.</div></div></div></div>",
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1, 2])
with left_col:
    st.markdown("### Request Summary", unsafe_allow_html=True)
    st.markdown(f"- **Models:** {', '.join(selected_models)}", unsafe_allow_html=True)
    st.markdown(f"- **Input type:** {input_type}", unsafe_allow_html=True)
    if prompt_text:
        st.markdown(f"- **Prompt:** {prompt_text[:120]}{'...' if len(prompt_text) > 120 else ''}", unsafe_allow_html=True)
    if uploaded_file:
        if input_type == "image":
            st.image(uploaded_file, width=260)
        else:
            st.markdown(f"- **File:** {uploaded_file.name}", unsafe_allow_html=True)

with right_col:
    status = st.empty()
    results_box = st.empty()

# ----------------------------
# Helpers — sending requests
# ----------------------------
def send_json(url: str, prompt: str, models: List[str], inputType: str):
    payload = {"prompt": prompt, "models": models, "inputType": inputType}
    start = time.time()
    r = requests.post(url, json=payload, timeout=120)
    return r, time.time() - start

def send_multipart(url: str, file_bytes: bytes, filename: str, models: List[str], inputType: str, prompt_txt: str = None):
    files = {"prompt": (filename, file_bytes)}
    data = {"models": json.dumps(models), "inputType": inputType}
    # include textual prompt optionally for nodes expecting body.prompt
    if prompt_txt:
        data["prompt"] = prompt_txt
        data["prompt_text"] = prompt_txt
    start = time.time()
    r = requests.post(url, files=files, data=data, timeout=180)
    return r, time.time() - start

def image_to_data_url(file_bytes: bytes, filename: str) -> str:
    # try to infer mime from extension (fallback to png)
    ext = filename.split(".")[-1].lower() if "." in filename else "png"
    mime = "image/png"
    if ext in ("jpg", "jpeg"):
        mime = "image/jpeg"
    elif ext == "gif":
        mime = "image/gif"
    elif ext == "webp":
        mime = "image/webp"
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def normalize_response(resp_json):
    """Return list of {model, response, latencyMs}"""
    if not isinstance(resp_json, dict):
        return [{"model":"result","response":str(resp_json),"latencyMs":0}]
    if "responses" in resp_json:
        r = resp_json["responses"]
        if isinstance(r, list):
            return r
        if isinstance(r, dict):
            out=[]
            for k,v in r.items():
                if isinstance(v, dict):
                    out.append({"model":k,"response":v.get("response") or v.get("text") or str(v),"latencyMs": v.get("latencyMs", v.get("latency_ms",0))})
                else:
                    out.append({"model":k,"response":str(v),"latencyMs":0})
            return out
    return [{"model":"result","response":json.dumps(resp_json,indent=2),"latencyMs":0}]

# ----------------------------
# Run logic
# ----------------------------
if run:
    status.markdown("<div style='padding:12px;border-radius:8px;background:#071018;border:1px solid rgba(255,255,255,0.03)'><b>Sending request…</b></div>", unsafe_allow_html=True)
    results_box.empty()

    try:
        # Decide how to send based on input_type
        if input_type == "text" and uploaded_file is None:
            # text only -> JSON
            resp, elapsed = send_json(webhook_input, prompt_text, selected_models, input_type)

        elif input_type == "audio":
            # audio -> always send RAW binary multipart under field name 'prompt'
            if uploaded_file is None:
                st.warning("No audio file uploaded — please upload an audio file for Whisper.")
                status.markdown("<div style='padding:12px;border-radius:8px;background:#071018;border:1px solid rgba(255,255,255,0.03)'><b style='color:#ef4444'>No file</b></div>", unsafe_allow_html=True)
                results_box.text("Upload an audio file in the sidebar.")
                raise SystemExit("No audio file uploaded")
            file_bytes = uploaded_file.read()
            filename = uploaded_file.name
            resp, elapsed = send_multipart(webhook_input, file_bytes, filename, selected_models, input_type, prompt_text if prompt_text else None)

        elif input_type == "image":
            # image -> convert to base64 data URL and send as JSON in 'prompt' field
            if uploaded_file is None:
                st.warning("No image uploaded — please upload an image or change input type to text.")
                status.markdown("<div style='padding:12px;border-radius:8px;background:#071018;border:1px solid rgba(255,255,255,0.03)'><b style='color:#ef4444'>No file</b></div>", unsafe_allow_html=True)
                results_box.text("Upload an image in the sidebar or switch to text mode.")
                raise SystemExit("No image file uploaded")
            file_bytes = uploaded_file.read()
            filename = uploaded_file.name
            data_url = image_to_data_url(file_bytes, filename)
            # Build payload: prompt = data_url (vision node expects imageUrls = {{$json.prompt}})
            payload = {"prompt": data_url, "models": selected_models, "inputType": input_type}
            # Include textual prompt_text as separate field if present
            if prompt_text:
                payload["prompt_text"] = prompt_text
            resp, elapsed = send_json(webhook_input, payload["prompt"], payload["models"], payload["inputType"]) if False else (requests.post(webhook_input, json=payload, timeout=120), time.time() - time.time())  # placeholder to ensure we have resp below

            # The above line is a trick to preserve readable code: do actual call separately
            # call properly:
            start = time.time()
            resp = requests.post(webhook_input, json=payload, timeout=120)
            elapsed = time.time() - start

        else:
            # fallback: json
            resp, elapsed = send_json(webhook_input, prompt_text, selected_models, input_type)

        # Handle response
        if 200 <= resp.status_code < 300:
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
            status.markdown(f"<div style='padding:12px;border-radius:8px;background:#071018;border:1px solid rgba(255,255,255,0.03)'><b style='color:#10b981'>Success</b> — {elapsed:.2f}s</div>", unsafe_allow_html=True)
            items = normalize_response(body)
            html = "<div class='results-card'>"
            for it in items:
                model = it.get("model","unknown")
                text = it.get("response","")
                lat = it.get("latencyMs",0)
                # safe display: if text is bytes or non-str, convert
                if not isinstance(text, str):
                    text = json.dumps(text, indent=2)
                html += f"""
                    <div class='resp-card'>
                      <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div>
                          <div class='resp-title'>{model}</div>
                          <div class='resp-lat'>latency: {lat} ms</div>
                        </div>
                      </div>
                      <div style='margin-top:8px;color:#dbeefe;font-size:14px;'><pre style='white-space:pre-wrap;font-family:Inter, monospace;font-size:13px;border:none;background:transparent;padding:0;margin:0;'>{st.markdown(text, unsafe_allow_html=False) or ''}</pre></div>
                    </div>
                """
            html += "</div>"
            results_box.markdown(html, unsafe_allow_html=True)

        else:
            status.markdown(f"<div style='padding:12px;border-radius:8px;background:#071018;border:1px solid rgba(255,255,255,0.03)'><b style='color:#ef4444'>Error {resp.status_code}</b></div>", unsafe_allow_html=True)
            results_box.text(resp.text)

    except SystemExit:
        # handled above (just ignore)
        pass
    except Exception as exc:
        status.markdown(f"<div style='padding:12px;border-radius:8px;background:#071018;border:1px solid rgba(255,255,255,0.03)'><b style='color:#ef4444'>Request failed</b></div>", unsafe_allow_html=True)
        results_box.text(str(exc))
