FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /workspace

# System dependencies: git, ffmpeg, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI (pinned to H3-capable release line)
RUN git clone --depth 1 --branch v0.41.2 https://github.com/comfyanonymous/ComfyUI.git ComfyUI

# Install ComfyUI core dependencies
RUN cd ComfyUI && pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 && \
    pip install --no-cache-dir -r requirements.txt

WORKDIR /workspace/ComfyUI/custom_nodes

# Clone OpenJutsu required custom nodes (URLs verified 200 OK via README official)
RUN git clone https://github.com/ethanfel/ComfyUI-MiniMaxH3-Context-Loop && \
    git clone https://github.com/Adudeguyman/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder && \
    git clone https://github.com/kijai/ComfyUI-KJNodes && \
    git clone https://github.com/Fannovel16/comfyui_controlnet_aux && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite && \
    git clone https://github.com/D3voz/comfyui-h3-oneclick-swap && \
    git clone https://github.com/Carasibana/ComfyUI-H3-FaceRefine && \
    git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack && \
    git clone https://github.com/D3voz/comfyui-image-detail-contrast && \
    git clone https://github.com/orion4d/Orion4D_FXMax && \
    git clone https://github.com/D3voz/comfyui-websocket-reconnect-fix

# Clone SolarRenderer (relighting subfolder: Enderfga/SolarRenderer/comfyui)
RUN git clone --depth 1 https://github.com/Enderfga/SolarRenderer SolarRenderer_src && \
    mkdir -p SolarRenderer && \
    cp -r SolarRenderer_src/comfyui/* SolarRenderer/ 2>/dev/null || cp -r SolarRenderer_src/* SolarRenderer/ && \
    rm -rf SolarRenderer_src

# Install per-pack Python dependencies into ComfyUI env
RUN for d in ComfyUI-MiniMaxH3-Context-Loop ComfyUI-Fantastic-MiniMaxH3-PromptBuilder ComfyUI-KJNodes comfyui_controlnet_aux ComfyUI-VideoHelperSuite comfyui-h3-oneclick-swap ComfyUI-H3-FaceRefine ComfyUI-Impact-Pack comfyui-image-detail-contrast Orion4D_FXMax ; do \
      if [ -f "$d/requirements.txt" ]; then pip install --no-cache-dir -r "$d/requirements.txt"; fi; \
    done && \
    pip install --no-cache-dir ultralytics scipy insightface onnxruntime-gpu imageio-ffmpeg runpod requests websocket-client

WORKDIR /workspace

COPY . /workspace/worker_src/
RUN cp /workspace/worker_src/handler.py /workspace/handler.py && \
    cp /workspace/worker_src/requirements.txt /workspace/requirements.txt && \
    pip install --no-cache-dir -r /workspace/requirements.txt

# Model weights are NOT baked in — mounted from RunPod Network Volume at:
#   /workspace/ComfyUI/models/
# Use preload_weights.py to fetch them once into the volume.
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV HF_HOME=/workspace/cache
ENV TMPDIR=/workspace/tmp
RUN mkdir -p /workspace/cache /workspace/tmp && chmod -R 777 /workspace/cache /workspace/tmp

CMD ["python", "-u", "/workspace/handler.py"]
