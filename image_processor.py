"""이미지 가공 모듈 - 이미지 압축 및 리사이즈"""

import os
from PIL import Image, ImageOps

MAX_WIDTH = 1280
MAX_HEIGHT = 1280
JPEG_QUALITY = 75
MAX_FILE_SIZE_KB = 500


def compress_image(image_path, output_path=None):
    """이미지를 압축하여 용량을 줄입니다.

    결과는 항상 JPEG이므로 확장자도 .jpg로 맞춥니다. (예: a.png → a.jpg, 원본 a.png 삭제)
    움직이는 GIF처럼 여러 장면이 있는 이미지는 JPEG로 바꾸면 정지 사진이 되므로 건너뜁니다.
    압축하지 않았으면 None을 반환합니다.
    """
    base, ext = os.path.splitext(image_path)
    in_place = output_path == image_path
    if output_path is None:
        output_path = f"{base}_compressed.jpg"
    elif in_place and ext.lower() not in (".jpg", ".jpeg"):
        # 같은 이름의 .jpg가 이미 있으면 덮어쓰지 않도록 번호를 붙임
        output_path = f"{base}.jpg"
        n = 1
        while os.path.exists(output_path):
            output_path = f"{base}_{n}.jpg"
            n += 1

    try:
        with Image.open(image_path) as src:
            if getattr(src, "n_frames", 1) > 1:
                print(f"움직이는 이미지라 건너뜀: {image_path}")
                return None
            # 휴대폰 사진의 회전 정보(EXIF)를 실제 픽셀에 반영 → 저장 후에도 세로 사진이 눕지 않음
            img = ImageOps.exif_transpose(src)
            img.load()

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

        # 확장자를 .jpg로 바꿔 저장했으면 원본(.png 등)은 지움 (같은 글에 두 번 올라가지 않게)
        if in_place and output_path != image_path:
            os.remove(image_path)
        return output_path
    except Exception as e:
        print(f"이미지 압축 실패: {image_path} - {e}")
        return None


def compress_folder(folder_path):
    """폴더 내 모든 이미지를 압축합니다."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    compressed_count = 0

    for filename in sorted(os.listdir(folder_path)):
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
