# src/core/task_definitions.py
import enum


class TaskName(enum.Enum):
    
    OCR = "ocr"
    TRANSLATE = "translate"
    LOAD_MODEL = "load_model"
    BATCH_SAVE = "batch_save"