"""이미지 가공 모듈 - 이미지 압축 및 리사이즈"""

import os
from PIL import Image

MAX_WIDTH = 1280
MAX_HEIGHT = 1280
JPEG_QUALITY = 75
MAX_FILE_SIZE_KB = 500


def compress_image(image_path, output_path=None):
    """이미지를 압축하여 용량을 줄입니다."""
    if output_path is None:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_compressed{ext}"

    try:
        img = Image.open(image_path)

        # RGBA -> RGB 변환 (JPEG 저장용)
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 리사이즈 (비율 유지)
        img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)

        # JPEG로 저장 (품질 조절)
        img.save(output_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)

        # 파일 크기가 여전히 크면 품질을 더 낮춤
        quality = JPEG_QUALITY
        while os.path.getsize(output_path) > MAX_FILE_SIZE_KB * 1024 and quality > 20:
            quality -= 10
            img.save(output_path, 'JPEG', quality=quality, optimize=True)

        return output_path
    except Exception as e:
        print(f"이미지 압축 실패: {image_path} - {e}")
        return image_path


def compress_folder(folder_path):
    """폴더 내 모든 이미지를 압축합니다."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    compressed_count = 0

    for filename in os.listdir(folder_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext in image_extensions:
            filepath = os.path.join(folder_path, filename)
            original_size = os.path.getsize(filepath)

            # 이미 작은 파일은 건너뜀
            if original_size <= MAX_FILE_SIZE_KB * 1024:
                continue

            output_path = compress_image(filepath, filepath)
            if output_path:
                new_size = os.path.getsize(output_path)
                compressed_count += 1
                print(f"압축: {filename} ({original_size // 1024}KB -> {new_size // 1024}KB)")

    return compressed_count


def compress_all_content_folders(content_base_path):
    """모든 컨텐츠 폴더의 이미지를 압축합니다."""
    total = 0
    if not os.path.exists(content_base_path):
        return 0

    for folder_name in sorted(os.listdir(content_base_path)):
        folder_path = os.path.join(content_base_path, folder_name)
        if os.path.isdir(folder_path):
            count = compress_folder(folder_path)
            total += count

    return total
