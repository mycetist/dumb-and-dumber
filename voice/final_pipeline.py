import json
import time
from pathlib import Path

from .whisper import load_model, transcribe_audio
from .LLM import get_llm_instance, extract_commands

BASE_DIR = Path(__file__).parent
WHISPER_PATH = BASE_DIR / "model"
LLM_PATH = BASE_DIR / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"

_whisper_model = None

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = load_model(WHISPER_PATH)
    return _whisper_model

def run_pipeline(file_name):
    start_time = time.perf_counter()
    
    w_model = get_whisper()
    llm = get_llm_instance(LLM_PATH) 
    
    text, info = transcribe_audio(w_model, file_name)
    
    result = extract_commands(text, llm)
    
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    return result, total_time