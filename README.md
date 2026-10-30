# OpenJutsu RunPod Serverless Worker

Serverless implementation of [D3voz/openjutsu](https://github.com/D3voz/openjutsu) on RunPod.
Uses ComfyUI Headless + MiniMax H3 + SAM 3.1 + InsightFace to perform consistent character, garment, and clothing replacement on videos.

---

## 🏗️ Architecture

```text
Klien (Editor z0z0 UI)
       │ (POST /run - JSON payload base64 video + garment image)
       ▼
RunPod Serverless Endpoint (Pool: ADA_24 RTX 4090 / ADA_48_PRO L40S)
  ├── handler.py (RunPod SDK listener)
  ├── ComfyUI Headless (Port 8188)
  └── Models Mounted via Network Volume (/workspace/ComfyUI/models/)
```

---

## 🚀 Deployment via GitHub Actions (Zero Local Docker)

1. Buat repo baru di GitHub: `openjutsu-serverless` (akun `z0ci` atau personal).
2. Push seluruh isi folder ini ke GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: init openjutsu serverless worker"
   git branch -M main
   git remote add origin https://github.com/<user>/openjutsu-serverless.git
   git push -u origin main
   ```
3. GitHub Actions otomatis membangun image dan mem-push ke Docker Hub:
   `z0ci/openjutsu-serverless:latest`

---

## 💾 Model Weights (Network Volume Setup)

Bobot model **tidak dimasukkan ke image Docker** agar container tetap ramping.
Mount Network Volume ke `/workspace/ComfyUI/models/`.
Jalankan skrip `preload_weights.py` sekali di pod sementara untuk mendownload:
- `minimax_h3_ref2va_pruned_int8_convrot.safetensors`
- `qwen3vl_8b_int8_convrot.safetensors`
- `sam3.1_multiplex_fp16.safetensors`
- LoRA DMAD 4-step & SolarRenderer
- VAE H3 video & audio

---

## 📡 API Input Format

```json
{
  "input": {
    "video_base64": "<base64 video MP4>",
    "garment_image_base64": "<base64 foto baju baru / opsional>",
    "prompt": "change clothes to red flannel shirt, natural lighting",
    "seed": 42
  }
}
```

## 📦 API Output Format

```json
{
  "video": "<base64 mp4 video hasil>",
  "format": "mp4",
  "size_bytes": 12450820,
  "prompt": "change clothes to red flannel shirt, natural lighting"
}
```
