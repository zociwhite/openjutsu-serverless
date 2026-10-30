"""
OpenJutsu compatibility & bridge nodes for ComfyUI.

Ensures that all MiniMax H3 Context Loop nodes (especially MiniMaxH3ChainPlanModern,
MiniMaxH3GenerationProfile, MiniMaxH3SourceTimeline, and loop traversal nodes)
are reliably loaded and registered in ComfyUI, preventing 'missing_node_type' errors.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
import types

_LOG = logging.getLogger("openjutsu_compat")

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# ---------------------------------------------------------------------------
# 1. DYNAMIC BRIDGE TO ComfyUI-MiniMaxH3-Context-Loop
# ---------------------------------------------------------------------------
def _load_upstream_loop_nodes():
    custom_nodes_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(custom_nodes_dir)
    candidates = [
        os.path.join(parent_dir, "ComfyUI-MiniMaxH3-Context-Loop"),
        os.path.join(parent_dir, "ComfyUI_MiniMaxH3_Context_Loop"),
        os.path.join(parent_dir, "comfyui-minimaxh3-context-loop"),
    ]
    loop_dir = next((c for c in candidates if os.path.isdir(c)), None)
    if not loop_dir:
        _LOG.warning("[OpenJutsu Compat] ComfyUI-MiniMaxH3-Context-Loop directory not found.")
        return

    pkg_name = "ComfyUI_MiniMaxH3_Context_Loop_Internal"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [loop_dir]
        sys.modules[pkg_name] = pkg

    # Try loading chain_nodes.py
    chain_path = os.path.join(loop_dir, "chain_nodes.py")
    if os.path.isfile(chain_path):
        try:
            spec = importlib.util.spec_from_file_location(f"{pkg_name}.chain_nodes", chain_path)
            chain_mod = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.chain_nodes"] = chain_mod
            spec.loader.exec_module(chain_mod)
            if hasattr(chain_mod, "CHAIN_NODE_CLASS_MAPPINGS"):
                NODE_CLASS_MAPPINGS.update(chain_mod.CHAIN_NODE_CLASS_MAPPINGS)
                _LOG.info(f"[OpenJutsu Compat] Bridged {len(chain_mod.CHAIN_NODE_CLASS_MAPPINGS)} nodes from chain_nodes.py")
            if hasattr(chain_mod, "CHAIN_NODE_DISPLAY_NAME_MAPPINGS"):
                NODE_DISPLAY_NAME_MAPPINGS.update(chain_mod.CHAIN_NODE_DISPLAY_NAME_MAPPINGS)
        except Exception as e:
            _LOG.warning(f"[OpenJutsu Compat] Note loading chain_nodes: {e}")

    # Try loading masking_nodes.py
    masking_path = os.path.join(loop_dir, "masking_nodes.py")
    if os.path.isfile(masking_path):
        try:
            spec = importlib.util.spec_from_file_location(f"{pkg_name}.masking_nodes", masking_path)
            mask_mod = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.masking_nodes"] = mask_mod
            spec.loader.exec_module(mask_mod)
            if hasattr(mask_mod, "NODE_CLASS_MAPPINGS"):
                NODE_CLASS_MAPPINGS.update(mask_mod.NODE_CLASS_MAPPINGS)
            if hasattr(mask_mod, "NODE_DISPLAY_NAME_MAPPINGS"):
                NODE_DISPLAY_NAME_MAPPINGS.update(mask_mod.NODE_DISPLAY_NAME_MAPPINGS)
        except Exception as e:
            _LOG.warning(f"[OpenJutsu Compat] Note loading masking_nodes: {e}")

    # Try loading nodes.py
    nodes_path = os.path.join(loop_dir, "nodes.py")
    if os.path.isfile(nodes_path):
        try:
            spec = importlib.util.spec_from_file_location(f"{pkg_name}.nodes", nodes_path)
            nodes_mod = importlib.util.module_from_spec(spec)
            sys.modules[f"{pkg_name}.nodes"] = nodes_mod
            spec.loader.exec_module(nodes_mod)
            if hasattr(nodes_mod, "NODE_CLASS_MAPPINGS"):
                NODE_CLASS_MAPPINGS.update(nodes_mod.NODE_CLASS_MAPPINGS)
            if hasattr(nodes_mod, "NODE_DISPLAY_NAME_MAPPINGS"):
                NODE_DISPLAY_NAME_MAPPINGS.update(nodes_mod.NODE_DISPLAY_NAME_MAPPINGS)
        except Exception as e:
            _LOG.warning(f"[OpenJutsu Compat] Note loading nodes: {e}")

try:
    _load_upstream_loop_nodes()
except Exception as e:
    _LOG.warning(f"[OpenJutsu Compat] Upstream bridge error: {e}")

# ---------------------------------------------------------------------------
# 2. BULLETPROOF FALLBACK CLASSES
# ---------------------------------------------------------------------------
# If MiniMaxH3GenerationProfile is not yet provided by upstream:
if "MiniMaxH3GenerationProfile" not in NODE_CLASS_MAPPINGS:
    class FallbackMiniMaxH3GenerationProfile:
        @classmethod
        def INPUT_TYPES(cls):
            return {
                "required": {
                    "scene_continuity": (
                        [
                            "Hard picture + protected audio",
                            "Visual continuity",
                            "Independent scenes",
                            "Hard picture + smooth audio",
                        ],
                        {"default": "Hard picture + protected audio"},
                    ),
                    "audio_profile": (
                        [
                            "Generate audio",
                            "Generate fresh audio per scene",
                            "Lip-sync to source audio",
                            "Generate audio from source guide",
                            "Use source soundtrack only",
                            "No final audio",
                        ],
                        {"default": "Generate audio"},
                    ),
                },
                "optional": {
                    "lip_sync_options": ("H3_LIP_SYNC_OPTIONS",),
                },
            }

        RETURN_TYPES = ("H3_CHAIN_POLICY", "STRING")
        RETURN_NAMES = ("chain_policy", "status")
        FUNCTION = "build"
        CATEGORY = "conditioning/minimax/context_loop/policies"

        def build(self, scene_continuity="Hard picture + protected audio", audio_profile="Generate audio", lip_sync_options=None):
            policy = {
                "version": 1,
                "transition": "hard_av" if "Hard" in scene_continuity else "guide",
                "final_audio": "generated",
                "source_reference": "off",
                "generated_continuity": "on",
                "source_audio_target": "off",
                "audio_context_length": 22,
                "lip_sync_options": lip_sync_options,
                "audio_policy": {
                    "final_audio": "generated",
                    "source_reference": "off",
                    "generated_continuity": "on",
                    "source_audio_target": "off",
                    "lip_sync_options": lip_sync_options,
                },
            }
            return (policy, f"{scene_continuity}; {audio_profile}")

    NODE_CLASS_MAPPINGS["MiniMaxH3GenerationProfile"] = FallbackMiniMaxH3GenerationProfile
    NODE_DISPLAY_NAME_MAPPINGS["MiniMaxH3GenerationProfile"] = "Generation Profile"

# If MiniMaxH3ChainPlanModern is not yet provided by upstream:
if "MiniMaxH3ChainPlanModern" not in NODE_CLASS_MAPPINGS:
    class FallbackMiniMaxH3ChainPlanModern:
        @classmethod
        def INPUT_TYPES(cls):
            sample = json.dumps({
                "shots": [
                    {"id": "intro", "prompt": "Describe the opening shot."},
                    {"id": "continuation", "prompt": "Continue the same take."},
                ]
            }, indent=2)
            return {
                "required": {
                    "plan_json": ("STRING", {"default": sample, "multiline": True}),
                    "chain_policy": ("H3_CHAIN_POLICY",),
                    "run_name": ("STRING", {"default": "h3_chain"}),
                    "generation_fingerprint": ("STRING", {"default": ""}),
                    "width": ("INT", {"default": 960, "min": 32, "max": 4096, "step": 32}),
                    "height": ("INT", {"default": 544, "min": 32, "max": 4096, "step": 32}),
                    "encode_mode": (["video", "frames"], {"default": "video"}),
                    "crop": (["disabled", "center"], {"default": "disabled"}),
                    "default_duration_seconds": ("FLOAT", {"default": 15.0, "min": 0.1, "max": 150.0, "step": 0.01}),
                    "default_steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                    "base_seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                    "segment_crf": ("INT", {"default": 18, "min": 0, "max": 51}),
                    "video_blend_frames": ("INT", {"default": 0, "min": 0, "max": 243}),
                },
                "optional": {
                    "plan_json_input": ("STRING", {"forceInput": True}),
                    "project_assets": ("H3_PROJECT_ASSETS",),
                },
            }

        RETURN_TYPES = ("H3_CHAIN_PLAN",)
        RETURN_NAMES = ("plan",)
        FUNCTION = "build"
        CATEGORY = "conditioning/minimax/context_loop"

        def build(self, plan_json, chain_policy, run_name, generation_fingerprint,
                  width, height, encode_mode, crop, default_duration_seconds,
                  default_steps, base_seed, segment_crf, video_blend_frames=0,
                  plan_json_input=None, project_assets=None):
            raw = plan_json_input if plan_json_input else plan_json
            try:
                data = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception:
                data = {}
            shots = data.get("shots", [])
            plan = {
                "version": 2,
                "run_name": str(run_name),
                "shots": shots,
                "summary": f"{len(shots)} shots, {width}x{height}",
                "compatibility": {
                    "width": int(width),
                    "height": int(height),
                    "video_blend_frames": int(video_blend_frames),
                    "encode_mode": encode_mode,
                    "crop": crop,
                    "anchor_mode": "head",
                    "context_length": 22,
                    "audio_context_length": 22,
                    "continuation_mode": "guide",
                    "audio_policy": chain_policy.get("audio_policy", {}) if isinstance(chain_policy, dict) else {},
                },
                "chain_policy": chain_policy,
            }
            return (plan,)

    NODE_CLASS_MAPPINGS["MiniMaxH3ChainPlanModern"] = FallbackMiniMaxH3ChainPlanModern
    NODE_DISPLAY_NAME_MAPPINGS["MiniMaxH3ChainPlanModern"] = "Production Plan (Modern)"
