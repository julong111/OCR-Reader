# src/core/parameters.py
from dataclasses import dataclass, asdict, fields


@dataclass
class ProcessingParameters:

    # --- Stage 1: Geometry ---
    rotation_angle: float = 0.0
    perspective_points: str = ""  # Serialized list of points
    work_areas: str = ""          # Serialized list of rects
    work_area_crop_rect: str = "" # Serialized rect for the crop bounding box
    relative_work_areas: str = "" # Serialized list of rects relative to the cropped image
    sample_char_height: int = 0
    min_symbol_height: int = 0
    standard_char_rect: str = ""  # Serialized rect for the standard char sample
    relative_standard_char_rect: str = "" # Serialized rect for the standard char sample relative to the cropped image
    min_symbol_rect: str = ""     # Serialized rect for the min symbol sample
    relative_min_symbol_rect: str = "" # Serialized rect for the min symbol sample relative to the cropped image

    # --- Stage 2: Binarization ---
    blur_ksize: int = 1
    preview_small_noise: bool = False
    confirm_small_noise_removal: bool = False
    preview_large_noise: bool = False
    confirm_large_noise_removal: bool = False
    large_noise_morph_ksize: int = 3      # Kernel size for large noise opening
    thresh_method: str = "global"
    thresh_value: int = 127
    thresh_blocksize: int = 11
    thresh_c: int = 2

    # --- Stage 3: Noise Removal ---
    morph: bool = False
    morph_op: int = 0  # 0 for OPEN, 1 for CLOSE
    morph_ksize: int = 3
    dilate: bool = False
    dilate_ksize: int = 3
    noise_removal: bool = False
    small_noise_area_thresh: float = 0.0  # Absolute pixel area
    large_noise_area_thresh: float = 0.0  # Absolute pixel area
    filter_by_aspect_ratio: bool = False
    min_aspect_ratio: float = 0.0
    max_aspect_ratio: float = 5.0
    filter_by_convexity: bool = False
    min_convexity_ratio: float = 0.85
    filter_by_vertices: bool = False
    vertex_count: int = 4

    # --- Stage 4: OCR ---
    ocr_lang: str = "eng"

    # --- Navigation ---
    current_stage: int = 0

    @classmethod
    def from_dict(cls, data: dict):
        # This is a simple way to create an instance from a dict that might be missing keys.
        # It leverages the default values defined in the dataclass.
        instance = cls()
        cls_fields = {f.name: f.type for f in fields(cls)}

        for key, value in data.items():
            if key in cls_fields:
                expected_type = cls_fields[key]
                try:
                    # Handle boolean conversion from strings like 'True', 'False'
                    if expected_type is bool and isinstance(value, str):
                        converted_value = value.lower() in ('true', '1', 't', 'y', 'yes')
                    else:
                        # Coerce the value to the expected type (e.g., int(5.0) -> 5)
                        converted_value = expected_type(value)
                    setattr(instance, key, converted_value)
                except (ValueError, TypeError):
                    # If conversion fails, log a warning and use the default value.
                    print(
                        f"Warning: Could not convert value '{value}' for key '{key}' to {expected_type}. "
                        f"Using default value '{getattr(instance, key)}'."
                    )
        return instance

    def to_dicts(self):
        all_fields = asdict(self)
        nav_keys = {'current_stage'}
        nav_params = {k: v for k, v in all_fields.items() if k in nav_keys}
        image_params = {k: v for k, v in all_fields.items() if k not in nav_keys}
        return image_params, nav_params