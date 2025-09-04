# opencv_operations.py
import cv2
import os
import numpy as np
from PIL import Image
from PyQt5.QtGui import QImage, QPixmap

from .param_utils import deserialize_rect_list, deserialize_point_list
from .image_identifier import ImageIdentifier
from .parameters import ProcessingParameters


class OpenCVOperations:
    

    @staticmethod
    def load_raw_image(identifier: ImageIdentifier):
        
        if identifier.page > -1:
            try:
                pil_image = Image.open(identifier.path)
                pil_image.seek(identifier.page)
                pil_image = pil_image.convert("RGB")
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            except Exception:
                return None
        else:
            image = cv2.imread(identifier.path)
        return image

    def apply_stage1_geometry(self, image, params: ProcessingParameters, debug_info=None):
        
        if image is None:
            return None, None

        # This will be the base for both preview and final output
        geo_corrected_img = image.copy()

        # 1. 应用透视校正
        perspective_points_str = params.perspective_points
        if perspective_points_str:
            perspective_points = deserialize_point_list(perspective_points_str)
            if len(perspective_points) == 4:
                geo_corrected_img = apply_perspective_transform(geo_corrected_img, perspective_points, debug_info)

        # 2. 应用旋转
        rotation_angle = params.rotation_angle
        if rotation_angle != 0.0:
            geo_corrected_img = rotate_image(geo_corrected_img, rotation_angle)

        # 几何校正后的图像是预览图
        preview_image = geo_corrected_img
        crop_rect = None
        relative_work_areas = None
        relative_standard_char_rect = None
        relative_min_symbol_rect = None

        # 3. 应用工作区 to the ocr_image
        work_areas_str = params.work_areas
        if work_areas_str:
            work_areas = deserialize_rect_list(work_areas_str)
            if work_areas:
                # 1. 计算所有工作区的理论最小外包矩形
                # 这是基于用户输入的“逻辑”边界
                logical_min_x = min(r[0] for r in work_areas)
                logical_min_y = min(r[1] for r in work_areas)
                logical_max_x = max(r[0] + r[2] for r in work_areas)
                logical_max_y = max(r[1] + r[3] for r in work_areas)

                # 2. 创建一个基于完整尺寸的副本，用于生成蒙版和涂白
                ocr_image = geo_corrected_img.copy()
                mask = np.zeros(ocr_image.shape[:2], dtype=np.uint8)
                for area in work_areas:
                    x, y, w, h = area
                    cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

                # 3. 将蒙版外的区域涂白
                ocr_image[mask == 0] = 255

                # 4. 将理论边界裁剪到图像的实际尺寸内，得到实际的裁剪坐标
                img_h, img_w, _ = ocr_image.shape
                actual_min_x = max(0, logical_min_x)
                actual_min_y = max(0, logical_min_y)
                actual_max_x = min(img_w, logical_max_x)
                actual_max_y = min(img_h, logical_max_y)

                # 只有当裁剪区域有效时才进行裁剪
                if actual_max_x > actual_min_x and actual_max_y > actual_min_y:
                    ocr_image = ocr_image[actual_min_y:actual_max_y, actual_min_x:actual_max_x]

                # crop_rect 必须存储用于坐标变换的实际偏移量和尺寸
                crop_rect = (actual_min_x, actual_min_y, actual_max_x - actual_min_x, actual_max_y - actual_min_y)

                # 5. 计算工作区在裁剪后图像中的相对坐标
                relative_work_areas = []
                crop_x_offset, crop_y_offset = crop_rect[0], crop_rect[1]
                for area in work_areas:
                    relative_x = area[0] - crop_x_offset
                    relative_y = area[1] - crop_y_offset
                    relative_work_areas.append((relative_x, relative_y, area[2], area[3]))

                # 6. 计算其他框的相对坐标
                if params.standard_char_rect:
                    std_rect_list = deserialize_rect_list(params.standard_char_rect)
                    if std_rect_list:
                        std_rect = std_rect_list[0]
                        relative_x = std_rect[0] - crop_x_offset
                        relative_y = std_rect[1] - crop_y_offset
                        relative_standard_char_rect = [(relative_x, relative_y, std_rect[2], std_rect[3])]

            else:
                ocr_image = preview_image.copy()
        else:
            ocr_image = preview_image.copy()

        # For stage 1, return the geometrically corrected image for preview,
        # and the masked image for saving/as the "real" result.
        return preview_image, ocr_image, crop_rect, relative_work_areas, relative_standard_char_rect, None

    def apply_stage2_binarization(self, image, params: ProcessingParameters):
        
        if image is None:
            return None, None, None, None, None, None

        processed_img = image.copy()

        # 强制转换为灰度图，因为二值化必须在单通道图像上进行
        if len(processed_img.shape) == 3:
            processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)

        ksize = params.blur_ksize | 1
        if ksize > 1:
            processed_img = cv2.GaussianBlur(processed_img, (ksize, ksize), 0)

        thresh_method = params.thresh_method

        if thresh_method == "global":
            thresh_value = params.thresh_value
            _, processed_img = cv2.threshold(
                processed_img, thresh_value, 255, cv2.THRESH_BINARY
            )
        elif thresh_method == "adaptive":
            block_size = params.thresh_blocksize | 1
            c_val = params.thresh_c
            processed_img = cv2.adaptiveThreshold(
                processed_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, block_size, c_val
            )
        elif thresh_method == "otsu":
            _, processed_img = cv2.threshold(
                processed_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

        # --- 智能移除噪点 ---
        small_noise_contours = []
        large_noise_contours = []

        inverted_img = cv2.bitwise_not(processed_img)

        # 1. 查找小型噪点
        if params.enable_smart_noise_removal and params.sample_char_height > 0 and params.noise_size_limit_percent > 0:
            max_side_length = params.sample_char_height * (params.noise_size_limit_percent / 100.0)
            area_threshold = max_side_length * max_side_length
            contours, _ = cv2.findContours(inverted_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            small_noise_contours = [cnt for cnt in contours if cv2.contourArea(cnt) < area_threshold]

        # 2. 查找大型噪点
        if (params.preview_large_noise or params.confirm_large_noise_removal) and params.sample_char_height > 0:
            large_area_thresh = (params.sample_char_height ** 2) * 1.5
            full_contours, _ = cv2.findContours(inverted_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            ksize = params.large_noise_morph_ksize | 1
            large_kernel = np.ones((ksize, ksize), np.uint8)
            image_for_analysis = cv2.morphologyEx(inverted_img, cv2.MORPH_OPEN, large_kernel)
            robust_contours, _ = cv2.findContours(image_for_analysis, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            robust_noise_seeds = [cnt for cnt in robust_contours if cv2.contourArea(cnt) > large_area_thresh]

            final_large_noise_indices = set()
            for seed_contour in robust_noise_seeds:
                M = cv2.moments(seed_contour)
                if M["m00"] == 0: continue
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                for i, full_contour in enumerate(full_contours):
                    if cv2.pointPolygonTest(full_contour, (cx, cy), False) >= 0:
                        final_large_noise_indices.add(i)
                        break
            large_noise_contours = [full_contours[i] for i in sorted(list(final_large_noise_indices))]

        # 3. 生成主输出图像 (用于下一阶段和最终保存)
        main_result_image = processed_img.copy()
        if params.enable_smart_noise_removal and small_noise_contours:
            # 在主输出图像上真正移除噪点 (涂白)
            cv2.drawContours(main_result_image, small_noise_contours, -1, 255, thickness=cv2.FILLED)
        if params.confirm_large_noise_removal and large_noise_contours:
            # 在主输出图像上真正移除大型噪点 (涂白)
            cv2.drawContours(main_result_image, large_noise_contours, -1, 255, thickness=cv2.FILLED)

        # 4. 生成预览图像 (用于UI显示)
        # 检查是否有任何需要预览的内容
        is_small_noise_preview = params.enable_smart_noise_removal and small_noise_contours
        is_large_noise_preview = params.preview_large_noise and large_noise_contours

        if not is_small_noise_preview and not is_large_noise_preview:
            # 如果没有任何需要预览的，预览图就等于最终结果图
            preview_image = main_result_image
        else:
            # 如果需要预览，则在原始二值化图上绘制高亮框
            preview_image = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)
            if is_small_noise_preview:
                cv2.drawContours(preview_image, small_noise_contours, -1, (0, 255, 0), 1) # Green
            if is_large_noise_preview:
                cv2.drawContours(preview_image, large_noise_contours, -1, (0, 0, 255), 1) # Red

        return preview_image, main_result_image, None, None, None, None

    def apply_stage3_noise_removal(self, image, params: ProcessingParameters):

        
        if image is None:
            return None, None, None, None, None, None

        # 噪声移除是在二值化图像上进行的
        processed_img = image.copy()
        if len(processed_img.shape) == 3:
            processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2GRAY)
            _, processed_img = cv2.threshold(processed_img, 127, 255, cv2.THRESH_BINARY)

        if params.morph:
            kernel_size = params.morph_ksize | 1
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

            if params.morph_op == 0:  # 开操作 (Opening) - 用于移除微小噪点
                processed_img = cv2.morphologyEx(processed_img, cv2.MORPH_OPEN, kernel)
            else:  # 闭操作 (Closing) - 用于连接大块区域
                processed_img = cv2.morphologyEx(processed_img, cv2.MORPH_CLOSE, kernel)

        if params.dilate:
            kernel_size = params.dilate_ksize | 1
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
            processed_img = cv2.dilate(processed_img, kernel, iterations=1)

        filters = self._build_contour_filters(params, image.shape)

        if filters:
            output_image = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)
            inverted_for_contours = cv2.bitwise_not(processed_img)
            contours, _ = cv2.findContours(
                inverted_for_contours, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            noise_contours = []
            for cnt in contours:
                # If any filter identifies it as noise, mark it.
                if any(f(cnt) for f in filters):
                    noise_contours.append(cnt)

            # 在预览图上画出被移除的轮廓
            cv2.drawContours(output_image, noise_contours, -1, (0, 255, 0), 2)
            # 在OCR图上真正地移除这些轮廓（涂白）
            ocr_image = processed_img.copy()
            cv2.drawContours(ocr_image, noise_contours, -1, 255, thickness=cv2.FILLED)

            return output_image, ocr_image, None, None, None, None

        return processed_img, processed_img, None, None, None, None

    @staticmethod
    def _build_contour_filters(params: ProcessingParameters, image_shape):
        
        filters = []

        if params.noise_removal:
            large_area_thresh = params.large_noise_area_thresh
            if large_area_thresh > 0:
                filters.append(lambda c: OpenCVOperations._is_large_noise_by_size(c, large_area_thresh))

        # Shape filtering is now controlled by individual toggles
        if params.filter_by_aspect_ratio:
            min_r = params.min_aspect_ratio
            max_r = params.max_aspect_ratio
            filters.append(lambda c: OpenCVOperations._is_noise_by_aspect_ratio(c, min_r, max_r))

        if params.filter_by_convexity:
            min_c = params.min_convexity_ratio
            filters.append(lambda c: OpenCVOperations._is_noise_by_convexity(c, min_c))

        if params.filter_by_vertices:
            min_v = params.vertex_count
            filters.append(lambda c: OpenCVOperations._is_noise_by_vertices(c, min_v))

        return filters

    @staticmethod
    def _is_large_noise_by_size(contour, large_area_thresh):
        # 只检查面积是否超过大型噪点阈值
        area = cv2.contourArea(contour)
        return area > large_area_thresh

    @staticmethod
    def _is_noise_by_aspect_ratio(contour, min_ratio, max_ratio):
        
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / h if h > 0 else 0
        return not (min_ratio <= aspect_ratio <= max_ratio)

    @staticmethod
    def _is_noise_by_convexity(contour, min_convexity_ratio):
        
        area = cv2.contourArea(contour)
        if area > 0:
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                convexity = area / hull_area
                if convexity < min_convexity_ratio:
                    return True
        return False

    @staticmethod
    def _is_noise_by_vertices(contour, min_vertex_count):
        
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        return len(approx) < min_vertex_count


def convert_cv_to_qpixmap(cv_img):
    
    if cv_img is None:
        return None
    height, width = cv_img.shape[:2]
    if len(cv_img.shape) == 2:  # Grayscale
        bytes_per_line = width
        q_img = QImage(
            cv_img.data, width, height, bytes_per_line, QImage.Format_Grayscale8
        )
    else:  # BGR
        bytes_per_line = 3 * width
        q_img = QImage(
            cv_img.data, width, height, bytes_per_line, QImage.Format_BGR888
        )
    return QPixmap.fromImage(q_img)

def rotate_image(image, angle_degrees):
    
    if image is None or angle_degrees == 0:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    # 获取旋转矩阵
    M = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)

    # 计算旋转后图像的新边界框大小
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    # 调整旋转矩阵以考虑平移
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    # 应用仿射变换（旋转）
    return cv2.warpAffine(image, M, (new_w, new_h), borderValue=(255, 255, 255))

def _save_debug_image(image, step_name, debug_info):
    # Helper function to save debug images.
    if not debug_info:
        return

    project_path = debug_info.get("project_path")
    identifier = debug_info.get("identifier")

    if not project_path or not identifier:
        return

    debug_dir = os.path.join(project_path, "debug")
    os.makedirs(debug_dir, exist_ok=True)

    base_name, _ = os.path.splitext(os.path.basename(identifier.path))
    if identifier.page > -1:
        filename = f"{base_name}_p{identifier.page + 1}_{step_name}.png"
    else:
        filename = f"{base_name}_{step_name}.png"

    save_path = os.path.join(debug_dir, filename)
    try:
        cv2.imwrite(save_path, image)
        print(f"[DEBUG] Saved debug image to: {save_path}")
    except Exception as e:
        print(f"[DEBUG] Error saving debug image {save_path}: {e}")

def apply_perspective_transform(image, src_pts_list, debug_info=None):
    
    src_pts = np.array(src_pts_list, dtype=np.float32)

    # 1. 创建变换前的掩码
    h, w = image.shape[:2]
    mask_before = np.zeros((h, w), dtype=np.uint8)
    cv2.fillConvexPoly(mask_before, src_pts.astype(int), 255)
    _save_debug_image(mask_before, "1_initial_mask", debug_info)

    # 2. 计算变换矩阵并应用
    rect = np.zeros((4, 2), dtype="float32")
    s = src_pts.sum(axis=1)
    rect[0] = src_pts[np.argmin(s)]
    rect[2] = src_pts[np.argmax(s)]
    diff = np.diff(src_pts, axis=1)
    rect[1] = src_pts[np.argmin(diff)]
    rect[3] = src_pts[np.argmax(diff)]

    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    dst_pts = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    m = cv2.getPerspectiveTransform(rect, dst_pts)
    warped_image = cv2.warpPerspective(image, m, (max_width, max_height), borderValue=(255, 255, 255))
    warped_mask = cv2.warpPerspective(mask_before, m, (max_width, max_height), borderValue=(0, 0, 0))

    # 3. 寻找边界框并裁剪
    contours, _ = cv2.findContours(warped_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)

        if debug_info:
            debug_mask_after = cv2.cvtColor(warped_mask, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(debug_mask_after, (x, y), (x + w, y + h), (0, 255, 0), 2)
            _save_debug_image(debug_mask_after, "2_transformed_mask_with_bbox", debug_info)

        return warped_image[y:y+h, x:x+w]
    else:
        if debug_info:
            print("[DEBUG] No contours found on transformed mask. Returning uncropped image.")
        return warped_image
