"""
RunPod Serverless Handler for OpenJutsu (MiniMax H3 Video / Character / Clothing Swap).
Wraps ComfyUI headless with object.api.json workflow.
"""
import base64
import json
import os
import subprocess
import time
import urllib.request
import urllib.parse
import uuid
import runpod
import websocket

COMFY_HOST = "127.0.0.1:8188"
COMFY_DIR = "/workspace/ComfyUI"
INPUT_DIR = os.path.join(COMFY_DIR, "input")
OUTPUT_DIR = os.path.join(COMFY_DIR, "output")
WORKFLOW_FILE = "/workspace/worker_src/object_swap_workflow.json"

_comfy_proc = None

def ensure_comfy_running():
    global _comfy_proc
    if _comfy_proc is not None and _comfy_proc.poll() is None:
        return

    print("[INFO] Starting background ComfyUI instance...", flush=True)
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [
        "python",
        os.path.join(COMFY_DIR, "main.py"),
        "--listen", "127.0.0.1",
        "--port", "8188",
        "--disable-auto-launch"
    ]
    _comfy_proc = subprocess.Popen(cmd, cwd=COMFY_DIR)

    # Wait for ComfyUI to become available
    for i in range(60):
        try:
            req = urllib.request.Request(f"http://{COMFY_HOST}/system_stats")
            with urllib.request.urlopen(req, timeout=3) as r:
                if r.status == 200:
                    print(f"[INFO] ComfyUI ready in {i+1}s.", flush=True)
                    return
        except Exception:
            time.sleep(1)
    print("[WARN] ComfyUI start timed out, proceeding anyway...", flush=True)

def decode_to_file(data_str, out_path):
    if data_str.startswith("data:"):
        data_str = data_str.split(",", 1)[1]
    raw = base64.b64decode(data_str)
    with open(out_path, "wb") as f:
        f.write(raw)
    return out_path

def queue_prompt(prompt_workflow):
    client_id = str(uuid.uuid4())
    p = {"prompt": prompt_workflow, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request(f"http://{COMFY_HOST}/prompt", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())
    return res["prompt_id"], client_id

def wait_for_execution(prompt_id, client_id, timeout=600):
    ws_url = f"ws://{COMFY_HOST}/ws?clientId={client_id}"
    ws = websocket.WebSocket()
    ws.connect(ws_url, timeout=15)

    start = time.time()
    try:
        while time.time() - start < timeout:
            msg = ws.recv()
            if isinstance(msg, str):
                data = json.loads(msg)
                mtype = data.get("type")
                if mtype == "executing":
                    node = data.get("data", {}).get("node")
                    if node is None and data.get("data", {}).get("prompt_id") == prompt_id:
                        print("[INFO] ComfyUI execution finished.", flush=True)
                        break
                elif mtype == "execution_error":
                    err_info = data.get("data", {})
                    raise RuntimeError(f"ComfyUI Error in node {err_info.get('node_id')}: {err_info.get('exception_message')}")
    finally:
        ws.close()

def get_output_files(prompt_id):
    req = urllib.request.Request(f"http://{COMFY_HOST}/history/{prompt_id}")
    with urllib.request.urlopen(req, timeout=15) as r:
        hist = json.loads(r.read().decode())

    outputs = hist.get(prompt_id, {}).get("outputs", {})
    files = []
    for node_id, out in outputs.items():
        if "gifs" in out:
            for item in out["gifs"]:
                files.append(os.path.join(OUTPUT_DIR, item.get("subfolder", ""), item["filename"]))
        if "videos" in out:
            for item in out["videos"]:
                files.append(os.path.join(OUTPUT_DIR, item.get("subfolder", ""), item["filename"]))
    return files

def handler(job):
    job_input = job.get("input") or {}
    ensure_comfy_running()

    prompt_text = (job_input.get("prompt") or "").strip()
    if not prompt_text:
        return {"error": "'prompt' is required (e.g. 'change clothes to red flannel shirt')"}

    # Load base workflow
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        wf = json.load(f)

    uid = str(uuid.uuid4())[:8]

    # Save inputs into ComfyUI input folder
    video_b64 = job_input.get("video_base64") or job_input.get("video")
    if not video_b64:
        return {"error": "'video_base64' is required"}
    vid_name = f"in_vid_{uid}.mp4"
    decode_to_file(video_b64, os.path.join(INPUT_DIR, vid_name))

    garment_b64 = job_input.get("garment_image_base64") or job_input.get("image_base64") or job_input.get("image")
    if garment_b64:
        img_name = f"in_garment_{uid}.png"
        decode_to_file(garment_b64, os.path.join(INPUT_DIR, img_name))
    else:
        img_name = None

    # Patch workflow nodes
    # Node 5: VHS_LoadVideo
    if "5" in wf and "inputs" in wf["5"]:
        wf["5"]["inputs"]["video"] = vid_name
    # Node 2: LoadImage (Garment picture)
    if img_name and "2" in wf and "inputs" in wf["2"]:
        wf["2"]["inputs"]["image"] = img_name
    # Node 7: H3ObjectSwapPlan (Prompt / Action)
    if "7" in wf and "inputs" in wf["7"]:
        wf["7"]["inputs"]["prompt"] = prompt_text
        if "seed" in job_input:
            wf["7"]["inputs"]["seed"] = int(job_input["seed"])

    # Submit job to ComfyUI
    prompt_id, client_id = queue_prompt(wf)
    print(f"[INFO] Queued ComfyUI job prompt_id={prompt_id}", flush=True)

    wait_for_execution(prompt_id, client_id, timeout=job_input.get("timeout", 600))
    out_files = get_output_files(prompt_id)

    if not out_files or not os.path.isfile(out_files[0]):
        # Fallback scan output directory
        candidates = [os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp4")]
        if candidates:
            candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            out_files = [candidates[0]]
        else:
            return {"error": "Output video file not found after ComfyUI finished"}

    res_path = out_files[0]
    with open(res_path, "rb") as f:
        v_bytes = f.read()
    b64_res = base64.b64encode(v_bytes).decode("utf-8")

    return {
        "video": b64_res,
        "format": "mp4",
        "size_bytes": len(v_bytes),
        "prompt": prompt_text
    }

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
