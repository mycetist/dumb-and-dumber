import json
import sys
import psutil
from pydantic import BaseModel, Field
from typing import Literal
from llama_cpp import Llama, LlamaGrammar

def _is_gpu_available():
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

_llm_instance = None

def get_llm_instance(model_path):
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    has_gpu = _is_gpu_available()

    if has_gpu:
        n_gpu_layers = -1
        n_threads = 4
    else:
        n_gpu_layers = -1 if sys.platform == "darwin" else 0
        n_threads = psutil.cpu_count(logical=False) or 4
    
    _llm_instance = Llama(
        model_path=str(model_path),
        n_ctx=2048,
        n_batch=512,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        verbose=False
    )
    return _llm_instance

def close_llm():
    global _llm_instance
    if _llm_instance is not None:
        _llm_instance.close()
        _llm_instance = None

CommandType = Literal["Left", "Right", "Jump"]

class Command(BaseModel):
    type: CommandType
    duration: float = Field(ge=0, le=30, description="Длительность в секундах")
    phrase: str = Field(description="Фрагмент исходного текста")

class CommandList(BaseModel):
    commands: list[Command]

DURATION_SCALE = {
    "мгновенно, быстро, чуть-чуть": 0.3,
    "немного, недолго, слегка": 0.8,
    "секунду, одну секунду": 1.0,
    "пару секунд, несколько секунд": 2.5,
    "долго, подольше, хорошенько": 8.0,
    "очень долго": 15.0,
}

DURATION_BOUNDS = {
    "Jump": (0.0, 0.0),
    "Left": (0.2, 5.0),
    "Right": (0.2, 5.0),
}

def build_system_prompt():
    lines = [
        "Ты — парсер голосовых команд для игры.",
        "На вход получаешь текст. Извлеки последовательность команд и их длительность.",
        "Допустимые команды: Left, Right, Jump.",
        "Команд без длительности не бывает — всегда ставь число (для Jump ставь 0.0).",
        "",
        "Правила перевода длительности:"
    ]
    for phrase, seconds in DURATION_SCALE.items():
        lines.append(f"- {phrase} → {seconds}")
    lines.append('- явное число ("3 секунды") → ровно это число')
    lines.append('- прыжок ("прыгни") → 0.0')
    lines.append("")
    lines.append("Верни команды в порядке произнесения.")
    return "\n".join(lines)

FEW_SHOT = [
    {"role": "user", "content": "Пробеги налево секунду, а потом прыгни"},
    {"role": "assistant", "content": '{"commands": [{"type": "Left", "duration": 1.0, "phrase": "пробеги налево секунду"}, {"type": "Jump", "duration": 0.0, "phrase": "прыгни"}]}'},
    {"role": "user", "content": "Беги долго вправо"},
    {"role": "assistant", "content": '{"commands": [{"type": "Right", "duration": 8.0, "phrase": "беги долго вправо"}]}'},
    {"role": "user", "content": "Чуть-чуть влево"},
    {"role": "assistant", "content": '{"commands": [{"type": "Left", "duration": 0.3, "phrase": "чуть-чуть влево"}]}'},
    {"role": "user", "content": "Прыгни и иди 3 секунды направо"},
    {"role": "assistant", "content": '{"commands": [{"type": "Jump", "duration": 0.0, "phrase": "прыгни"}, {"type": "Right", "duration": 3.0, "phrase": "иди 3 секунды направо"}]}'}
]

def sanitize_commands(commands):
    for cmd in commands:
        lo, hi = DURATION_BOUNDS[cmd.type]
        if not (lo <= cmd.duration <= hi):
            cmd.duration = max(lo, min(hi, cmd.duration))
    return commands

def build_final_json(message, commands):
    result_commands = []
    current_time = 0.0

    for cmd in commands:
        start = current_time
        end = start + cmd.duration
        result_commands.append({
            "type": cmd.type,
            "duration": [round(start, 2), round(end, 2)]
        })
        current_time = end

    return {
        "message": message,
        "commands": result_commands
    }

def extract_commands(text, llm):
    messages = [{"role": "system", "content": build_system_prompt()}]
    messages.extend(FEW_SHOT)
    messages.append({"role": "user", "content": text})

    schema_json = json.dumps(CommandList.model_json_schema())
    
    grammar = LlamaGrammar.from_json_schema(schema_json)

    try:
        response = llm.create_chat_completion(
            messages=messages,
            grammar=grammar,
            temperature=0,
            max_tokens=150
        )
        
        content = response["choices"][0]["message"]["content"]
        
        parsed = CommandList.model_validate_json(content)
        commands = sanitize_commands(parsed.commands)
        return build_final_json(text, commands)
        
    except Exception as e:
        print(f"Ошибка при генерации команд: {e}")
        return {"message": str(text), "commands": []}