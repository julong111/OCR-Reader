# image_pipeline.py

from .opencv_operations import OpenCVOperations
from .parameters import ProcessingParameters


class ImagePipeline:
    # 封装多阶段图像处理流程。
    # 它接收输入图像、处理阶段和参数，并返回处理结果。
    def __init__(self):
        self.opencv_ops = OpenCVOperations()

    def process(self, input_image, stage_index, params: ProcessingParameters, debug_info=None):
        # 根据给定的阶段和参数处理图像。
        # 返回一个元组 (preview_image, main_result_image)。
        if input_image is None:
            return None, None, None, None, None, None

        if stage_index == 0:
            return self.opencv_ops.apply_stage1_geometry(input_image, params, debug_info=debug_info)
        elif stage_index == 1:
            return self.opencv_ops.apply_stage2_binarization(input_image, params)
        elif stage_index == 2:
            return self.opencv_ops.apply_stage3_noise_removal(input_image, params)
        else:  # 第四阶段及以后，不进行处理
            return input_image, input_image, None, None, None, None

    def process_fully(self, original_image, params: ProcessingParameters, debug_info=None):
        # Applies the full processing pipeline based on a parameter dictionary.
        # Returns the final image ready for OCR.
        if original_image is None:
            return None

        # Stage 1
        _, main_result_s1, _, _, _, _ = self.opencv_ops.apply_stage1_geometry(
            original_image, params, debug_info=debug_info
        )
        # Stage 2
        _, main_result_s2, _, _, _, _ = self.opencv_ops.apply_stage2_binarization(main_result_s1, params)
        # Stage 3
        _, main_result_s3, _, _, _, _ = self.opencv_ops.apply_stage3_noise_removal(main_result_s2, params)

        return main_result_s3