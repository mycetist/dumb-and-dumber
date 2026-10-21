import os
from pathlib import Path
import psutil

import numpy as np

os.environ["HF_HUB_OFFLINE"] = "1"

from faster_whisper import WhisperModel

def _resolve_device_and_compute():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"

def load_model(model_path, device=None, compute_type=None):
    
    if device is None or compute_type is None:
        auto_device, auto_compute = _resolve_device_and_compute()
        device = device or auto_device
        compute_type = compute_type or auto_compute

    if device == "cuda":
        cpu_threads = 1  
    else:
        cpu_threads = psutil.cpu_count(logical=False) or 4

    return WhisperModel(
        str(model_path),
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
    )

def _default_beam_size(device, compute_type):
    if device == "cuda":
        return 3 if compute_type == "int8" else 5
    return 1

def segments_to_text(segments):
    return " ".join(seg.text.strip() for seg in segments)

def transcribe_audio(model, audio_path, language="ru", vad_filter=True, beam_size=None, condition_on_previous_text=False):
    if beam_size is None:
        device = getattr(model, "device", "cpu")
        compute_type = getattr(model, "compute_type", "int8")
        if device not in ("cpu", "cuda"):
            device = "cpu"
        beam_size = _default_beam_size(device, compute_type)

    segments_gen, info = model.transcribe(
        audio_path if isinstance(audio_path, np.ndarray) else str(audio_path),
        language=language,
        vad_filter=vad_filter,
        beam_size=beam_size,
        condition_on_previous_text=condition_on_previous_text,
    )
    return segments_to_text(segments_gen), info