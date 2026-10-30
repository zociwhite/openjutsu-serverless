"""
Run ONCE on a cheap RunPod Pod (same region as the planned Endpoint):
Downloads MiniMax H3 / Qwen3-VL / SAM3.1 / LoRA weights into the mounted Network Volume.
Mount path example: /workspace/ComfyUI/models (or /runpod-volume/models -> symlink).
"""
import os
import sys
import subprocess

MODELS = [
    # (subdir, filename, huggingface_repo, description)
    ("diffusion_models", "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "MiniMax/H3", "H3 diffusion backbone INT8"),
    ("loras", "minimax_h3_DMAD_4step_full_lora_avg_rank_39_bf16.safetensors", "MiniMax/H3", "DMAD 4-step LoRA"),
    ("loras", "solarrenderer_4step_lora.safetensors", "SolarRenderer/repo", "SolarRenderer 4-step LoRA"),
    ("loras", "solarrenderer_control_lora.safetensors", "SolarRenderer/repo", "SolarRenderer control LoRA"),
    ("text_encoders", "qwen3vl_32b_minimax_h3_int4_convrot.safetensors", "MiniMax/H3", "Qwen3-VL 32B INT4 for H3"),
    ("text_encoders", "qwen3vl_8b_int8_convrot.safetensors", "MiniMax/H3", "Qwen3-VL 8B INT8 default"),
    ("vae", "minimax_h3_video_vae_int8_convrot.safetensors", "MiniMax/H3", "H3 video VAE INT8"),
    ("vae", "minimax_h3_audio_vae_fp32.safetensors", "MiniMax/H3", "H3 audio VAE FP32"),
    ("checkpoints", "sam3.1_multiplex_fp16.safetensors", "facebook/sam3", "SAM 3.1 segmentation"),
    ("sams", "sam_vit_b_01ec64.pth", "facebookresearch/segment-anything", "SAM ViT-B (face refine)"),
]

BASE = os.environ.get("MODELS_DIR", "/workspace/ComfyUI/models")

def main():
    print(f"[INFO] Target weights dir: {BASE}")
    for subdir, fname, repo, desc in MODELS:
        dest = os.path.join(BASE, subdir, fname)
        if os.path.isfile(dest):
            print(f"  [SKIP] {dest} already exists.")
            continue

        os.makedirs(os.path.join(BASE, subdir), exist_ok=True)
        print(f"  [DL] {desc} -> {dest}")
        try:
            subprocess.run(
                ["huggingface-cli", "download", repo, fname, "--local-dir", os.path.join(BASE, subdir)],
                check=True
            )
        except Exception as e:
            print(f"  [ERR] Failed {fname}: {e}\n  Manually verify repo ID in README / HuggingFace page.")
    print("[DONE] Please verify files with `ls -lh` per subfolder.")

if __name__ == "__main__":
    main()
