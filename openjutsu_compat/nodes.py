"""
OpenJutsu compatibility nodes for ComfyUI.

Provides a stub for MiniMaxH3GenerationProfile, which is referenced by
official openjutsu workflows (object.api.json, simple.api.json, etc.)
but is missing from public ComfyUI-MiniMaxH3-Context-Loop releases.
The stub returns a chain-policy dict that MiniMaxH3ChainPlanModern accepts.
"""


class MiniMaxH3GenerationProfile:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scene_continuity": (
                    ["Hard picture + protected audio", "Soft picture", "None"],
                ),
                "audio_profile": (["Generate audio", "Silent", "Mute"],),
            }
        }

    RETURN_TYPES = ("CHAIN_POLICY",)
    FUNCTION = "apply"
    CATEGORY = "openjutsu"

    def apply(self, scene_continuity, audio_profile):
        return (
            {
                "scene_continuity": scene_continuity,
                "audio_profile": audio_profile,
            },
        )


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3GenerationProfile": MiniMaxH3GenerationProfile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3GenerationProfile": "Generation Profile (OpenJutsu Compat)",
}
