"""네이버 밴드 자동 글쓰기 매크로 V2.5 - 메인 GUI (CustomTkinter)"""

import os
import re
import sys
import time
import random
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

import customtkinter as ctk

# 프로젝트 루트 설정
# exe 실행 시: exe 파일이 있는 폴더 기준
# 일반 실행 시: main.py가 있는 폴더 기준
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_DIR = os.path.join(BASE_DIR, "system")
CONTENT_DIR = os.path.join(BASE_DIR, "content")
RANDOM_PHRASES_FILE = os.path.join(SYSTEM_DIR, "random_phrases.txt")

os.makedirs(SYSTEM_DIR, exist_ok=True)
os.makedirs(CONTENT_DIR, exist_ok=True)

# '_'로 시작하는 글 폴더는 글쓰기에서 제외 (샘플/보관용)
SKIP_FOLDER_PREFIX = "_"
SAMPLE_DIR = os.path.join(CONTENT_DIR, "_sample")
SAMPLE_TEXT = """여기에 밴드에 올릴 본문을 적어주세요.

[글 폴더 만드는 방법]
1. 이 _sample 폴더를 복사해서 이름을 바꿉니다. (예: 01_가을이벤트)
   ※ 이름이 _ 로 시작하는 폴더는 올라가지 않습니다. 이 샘플 폴더도 올라가지 않습니다.
2. 이 txt 파일 내용을 실제 올릴 글로 바꿉니다. (txt는 폴더당 1개)
3. 함께 올릴 이미지를 폴더에 넣습니다. (jpg, png, gif, webp 등)
"""


def ensure_sample_content():
    """글 폴더가 하나도 없으면(첫 실행) 예시용 _sample 폴더를 만듭니다."""
    if any(os.path.isdir(os.path.join(CONTENT_DIR, n)) for n in os.listdir(CONTENT_DIR)):
        return
    try:
        os.makedirs(SAMPLE_DIR, exist_ok=True)
        with open(os.path.join(SAMPLE_DIR, "글.txt"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_TEXT)

        from PIL import Image, ImageDraw
        img = Image.new("RGB", (800, 600), "#533483")
        draw = ImageDraw.Draw(img)
        draw.rectangle((40, 40, 760, 560), outline="#e0e0e0", width=6)
        draw.text((400, 300), "SAMPLE IMAGE", fill="#e0e0e0", anchor="mm", font_size=64)
        img.save(os.path.join(SAMPLE_DIR, "sample.png"))
    except Exception:
        pass  # 샘플은 없어도 동작에 지장 없음


ensure_sample_content()

from automation import BandAutomation
from image_processor import compress_all_content_folders

# 테마 설정
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 색상 상수
COLOR_BG = "#1a1a2e"
COLOR_CARD = "#16213e"
COLOR_ACCENT = "#0f3460"
COLOR_PRIMARY = "#533483"
COLOR_SUCCESS = "#2ecc71"
COLOR_DANGER = "#e74c3c"
COLOR_TEXT = "#e0e0e0"
COLOR_MUTED = "#7f8c8d"
COLOR_STEP = "#a29bfe"
COLOR_HELP = "#3d4b6b"
COLOR_HELP_HOVER = "#55658c"

# 작업 순서 번호
STEP_NUMBERS = "①②③④⑤⑥⑦⑧⑨⑩"
STEP_BADGE_WIDTH = 34

# ? 버튼 도움말 (키: (제목, 내용))
HELP_TEXTS = {
    "content_folder": ("① 글작성 폴더 열기",
        "올릴 글을 넣어두는 content 폴더를 엽니다.\n\n"
        "[만드는 방법]\n"
        "1. content 폴더 안에 글 1개당 폴더 1개를 만듭니다.\n"
        "   예) 01_가을이벤트, 02_신상품안내\n"
        "2. 각 폴더에 본문 .txt 파일 1개를 넣습니다.\n"
        "   (메모장에서 UTF-8로 저장, txt가 여러 개면 이름순 마지막 1개만 사용)\n"
        "3. 함께 올릴 이미지(jpg, png, gif, webp 등)를 같은 폴더에 넣습니다.\n\n"
        "폴더는 이름순으로 하나씩 돌아가며 사용됩니다.\n"
        "(⑥의 '랜덤 글작성'을 켜면 무작위 순서)\n\n"
        "※ 처음 실행하면 예시용 _sample 폴더가 만들어져 있습니다. 복사해서 쓰세요.\n"
        "※ 이름이 _ 로 시작하는 폴더는 올라가지 않습니다. (샘플·보관용)"),
    "process_images": ("② 이미지 가공 (선택)",
        "content 안 모든 폴더의 이미지 중 500KB가 넘는 것을\n"
        "최대 1280px, JPEG 형식으로 줄입니다.\n\n"
        "※ 원본 파일에 그대로 덮어씁니다. 원본이 필요하면 따로 복사해 두세요.\n"
        "※ 이미지 업로드가 느리거나 실패할 때 사용하세요."),
    "edit_random_phrases": ("③ 랜덤문구 작성 (선택)",
        "메모장으로 랜덤문구 파일을 엽니다.\n\n"
        "한 줄에 문구 하나씩 적고 저장하세요.\n"
        "글을 올릴 때마다 이 중 한 줄이 무작위로 본문에 덧붙습니다.\n\n"
        "같은 글을 여러 밴드에 올릴 때 내용이 완전히 똑같아지는 것을 막아줍니다."),
    "random_phrase": ("랜덤문구 추가",
        "체크하면 글을 올릴 때마다 랜덤문구 중 한 줄을 본문에 덧붙입니다.\n"
        "체크를 끄면 txt 내용만 그대로 올립니다."),
    "browser": ("④ 브라우저 선택",
        "로그인과 글쓰기에 사용할 브라우저를 고릅니다.\n"
        "PC에 설치된 브라우저를 선택하세요.\n\n"
        "시크릿: 기록이 남지 않는 창으로 엽니다.\n"
        "체크하면 프로그램을 켤 때마다 다시 로그인해야 합니다.\n\n"
        "※ 로그인 하기를 누르기 전에 선택해야 적용됩니다.\n"
        "※ 선택한 브라우저가 없거나 실행되지 않으면 다른 브라우저(크롬↔엣지)로 자동 전환합니다.\n"
        "※ 처음 실행할 때 브라우저 버전에 맞는 드라이버를 자동으로 내려받습니다. (인터넷 필요)"),
    "login": ("④ 로그인 하기",
        "선택한 브라우저로 밴드 로그인 페이지를 엽니다.\n"
        "열린 브라우저에서 직접 로그인해주세요.\n\n"
        "※ 로그인 후 브라우저 창을 닫지 마세요. 매크로가 이 창으로 글을 씁니다.\n"
        "※ 'GoLogin 멀티 프로필 사용'이 켜져 있으면 선택한 GoLogin 프로필 브라우저들이 열립니다."),
    "fetch_band_urls": ("⑤ 밴드주소 가져오기",
        "로그인한 계정이 가입한 밴드 목록을 읽어\n"
        "아래 '밴드 URL 목록'에 자동으로 채웁니다.\n"
        "'방문이 뜸한 밴드' 폴더 안의 밴드도 함께 가져옵니다.\n"
        "광고(AD) 카드와 '이런 밴드는 어때요' 추천 밴드는 제외됩니다.\n\n"
        "※ ④에서 로그인을 마친 뒤에 눌러주세요.\n"
        "※ 기존 목록은 지워지고 새로 채워집니다.\n\n"
        "[GoLogin 사용 시]\n"
        "프로필마다 자기 계정의 가입 밴드를 가져와\n"
        "'# [프로필명]' 아래에 나눠서 채웁니다."),
    "band_urls": ("밴드 URL 목록",
        "글을 올릴 밴드 주소 목록입니다. 한 줄에 하나씩 적습니다.\n"
        "예) https://band.us/band/12345678\n\n"
        "⑤로 자동으로 채우거나 직접 붙여넣을 수 있습니다.\n"
        "글을 올리고 싶지 않은 밴드는 줄을 지우면 됩니다.\n\n"
        "※ https://band.us/band/ 로 시작하는 줄만 사용됩니다.\n\n"
        "[GoLogin 사용 시]\n"
        "# [프로필명] 줄 아래의 주소가 그 프로필이 글을 쓸 밴드입니다.\n"
        "   # [웹쿡]\n"
        "   https://band.us/band/11111111\n"
        "   # [rnjseor]\n"
        "   https://band.us/band/22222222\n"
        "줄을 지우면 그 프로필은 그 밴드에 쓰지 않습니다.\n"
        "# [프로필명] 줄이 하나도 없으면 시작할 때 프로필마다 자동으로 가져옵니다."),
    "delay": ("글쓰기 딜레이 (초)",
        "한 밴드에 글을 올린 뒤 다음 밴드로 넘어가기 전 기다리는 시간입니다.\n\n"
        "숫자 하나(예: 600) 또는 범위(예: 500~700)로 적습니다.\n"
        "범위로 적으면 그 사이에서 매번 무작위로 정해집니다.\n\n"
        "※ 너무 짧으면 밴드에서 스팸으로 막힐 수 있습니다."),
    "repeat_count": ("총 반복 횟수 (회)",
        "전체 과정을 몇 번 반복할지 정합니다.\n\n"
        "1회 = 글 폴더 1개를 골라 URL 목록의 모든 밴드에 올리기\n"
        "회차마다 다음 글 폴더로 넘어갑니다."),
    "system_delay": ("시스템 딜레이 (초)",
        "버튼 클릭·페이지 이동 사이에 기다리는 기본 시간입니다.\n\n"
        "인터넷이나 PC가 느려서 중간에 실패가 잦으면 값을 올려주세요.\n"
        "(예: 1.5 → 2.5)"),
    "final_delay": ("최종 딜레이 (분)",
        "한 회차(모든 밴드에 1번씩 올리기)를 마친 뒤\n"
        "다음 회차를 시작하기 전 기다리는 시간입니다."),
    "board_index": ("게시판 선택 (번)",
        "글쓰기 화면에서 게시판을 고르는 밴드라면\n"
        "목록에서 몇 번째 게시판에 올릴지 정합니다.\n\n"
        "1 = 첫 번째 게시판, 2 = 두 번째 게시판 ...\n"
        "게시판 선택이 없는 밴드에서는 무시됩니다."),
    "image_first": ("이미지 먼저",
        "체크하면 이미지를 먼저 올린 뒤 본문을 입력합니다.\n"
        "체크를 끄면 본문을 먼저 입력하고 이미지를 올립니다."),
    "random_post": ("랜덤 글작성",
        "체크하면 회차마다 content의 글 폴더 중 하나를 무작위로 고릅니다.\n"
        "체크를 끄면 폴더 이름순으로 차례대로 사용합니다."),
    "start_stop": ("⑦ 시작 / 중지",
        "시작: 설정대로 URL 목록의 밴드에 글을 올립니다.\n"
        "진행 상황은 아래 '실행 로그'에 표시됩니다.\n\n"
        "중지: 진행 중인 작업을 멈춥니다.\n"
        "(지금 쓰는 글은 마무리될 때까지 기다릴 수 있습니다)\n\n"
        "시작 전 확인할 것\n"
        "- ① content에 글 폴더가 있는지\n"
        "- ④ 로그인이 되어 있는지\n"
        "- URL 목록에 밴드 주소가 있는지"),
    "timer": ("작동시간 설정",
        "체크하면 지정한 시간대에만 글을 올립니다.\n"
        "시간대 밖이면 다음 시작 시각까지 기다렸다가 자동으로 이어갑니다.\n\n"
        "예) 22시 ~ 06시 처럼 자정을 넘는 시간대도 가능합니다."),
    "gologin": ("GoLogin 멀티 프로필",
        "여러 계정을 동시에 돌릴 때 사용하는 기능입니다. 일반 사용 시에는 끄세요.\n\n"
        "사용 순서\n"
        "1. 체크하면 나타나는 칸에 GoLogin API Key 입력\n"
        "2. 프로필 가져오기 → 사용할 프로필 선택\n"
        "3. ④ 로그인 하기 → 열린 브라우저마다 로그인\n"
        "4. ⑤ 밴드주소 가져오기 → URL 목록에 프로필별로 나눠 채워짐 (확인·수정 가능)\n"
        "5. ⑦ 시작 → 모든 프로필이 동시에 글을 올림\n\n"
        "[프로필별 동작]\n"
        "- 프로필마다 자기 계정의 가입 밴드에만 씁니다.\n"
        "  (⑤를 건너뛰면 시작할 때 자동으로 가져옵니다)\n"
        "- 같은 회차에 프로필끼리 같은 글을 쓰지 않도록 시작 글 폴더를 한 칸씩 엇갈립니다.\n"
        "  예) 프로필1은 폴더1부터, 프로필2는 폴더2부터 ...\n"
        "  ※ 글 폴더 수가 프로필 수보다 적으면 일부 프로필은 같은 글로 시작합니다."),
    "gologin_dedupe": ("겹치는 밴드는 중복 게시 발행 안함",
        "여러 프로필(계정)이 같은 밴드에 함께 가입해 있을 때,\n"
        "그 밴드에는 한 프로필만 글을 쓰도록 나눠 맡깁니다.\n"
        "같은 밴드에 여러 계정의 글이 몰리는 것을 막아줍니다.\n\n"
        "겹치는 밴드는 맡은 밴드가 적은 프로필에 먼저 배정됩니다.\n\n"
        "체크를 끄면 각 프로필이 자기 가입 밴드 전부에 씁니다."),
    "gologin_profiles": ("프로필 가져오기",
        "입력한 API Key로 GoLogin 계정의 프로필 목록을 불러옵니다.\n"
        "체크된 프로필만 실행됩니다.\n\n"
        "API Key는 GoLogin 웹사이트 > Settings > API 에서 확인할 수 있습니다."),
}


def gologin_profile_problem(gl):
    """GoLogin 브라우저를 띄우기 전에 프로필 정보를 확인합니다.

    gologin 라이브러리는 서버 응답에 브라우저 버전(userAgent의 Chrome/xxx)이 없으면
    "invalid literal for int()" 오류만 내고 실제 사유를 숨깁니다.
    먼저 응답을 받아보고, 문제가 있으면 서버가 보낸 사유를 문자열로 반환합니다. 정상이면 None.
    """
    try:
        data = gl.getProfile()
    except Exception as e:
        return f"프로필 정보를 받지 못했습니다 ({e})"

    user_agent = (data.get("navigator") or {}).get("userAgent", "")
    if "Chrome/" in user_agent:
        return None

    message = data.get("message") or data.get("error")
    if message:
        status = data.get("statusCode")
        return f"GoLogin 서버 응답: {message}" + (f" (코드 {status})" if status else "")
    if not user_agent:
        return ("프로필에 브라우저 정보(userAgent)가 비어 있습니다. "
                "GoLogin 앱에서 이 프로필을 한 번 열었다 닫거나, 지문(fingerprint)을 새로 고쳐주세요. "
                f"[응답 항목: {', '.join(list(data)[:12])}]")
    return f"브라우저 버전을 알 수 없는 userAgent입니다: {user_agent[:80]}"


def window_geometry(root, width, height):
    """창 크기를 화면 안에 들어오게 줄이고, 화면 위쪽 가운데에 둡니다.

    customtkinter는 윈도우 화면 배율(125%, 150% 등)만큼 창을 키우므로
    작은 노트북 화면에서는 820 높이가 화면 밖으로 넘칠 수 있습니다.
    """
    scale = ctk.ScalingTracker.get_window_scaling(root) or 1
    screen_w = root.winfo_screenwidth() / scale
    screen_h = root.winfo_screenheight() / scale
    width = int(min(width, screen_w - 40))
    height = int(min(height, screen_h - 100))  # 작업 표시줄·제목 표시줄 여유
    x = int(max(0, (screen_w - width) / 2))
    return f"{width}x{height}+{x}+20"


PROFILE_SECTION_RE =re.compile(r"^#\s*\[(.+)\]\s*$")


def format_profile_sections(names, profile_urls):
    """프로필별 URL 목록을 '# [프로필명]' 구역 텍스트로 만듭니다."""
    lines = []
    for name, urls in zip(names, profile_urls):
        lines.append(f"# [{name}]")
        lines.extend(urls)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_profile_sections(text):
    """'# [프로필명]' 구역 텍스트를 [(프로필명, [URL...]), ...]로 읽습니다.

    구역 머리말이 하나도 없으면 None을 반환합니다.
    밴드 주소가 아닌 줄과 첫 구역 앞의 주소는 무시합니다.
    """
    sections = []
    for line in text.splitlines():
        line = line.strip()
        header = PROFILE_SECTION_RE.match(line)
        if header:
            sections.append((header.group(1).strip(), []))
        elif sections and line.startswith("https://band.us/band/"):
            sections[-1][1].append(line)
    return sections or None


def assign_shared_bands(profile_urls):
    """여러 프로필이 함께 가입한 밴드를 한 프로필에만 배정합니다.

    profile_urls: 프로필별 밴드 URL 목록의 리스트.
    밴드마다 그 밴드에 가입한 프로필 중 지금까지 배정이 가장 적은 프로필에 줍니다.
    (가입 밴드가 적은 프로필이 일감을 덜 잃도록, 혼자만 가입한 밴드부터 먼저 배정)
    """
    owners = {}
    for idx, urls in enumerate(profile_urls):
        for url in urls:
            owners.setdefault(url, []).append(idx)

    assigned = [[] for _ in profile_urls]
    for url, idxs in sorted(owners.items(), key=lambda item: len(item[1])):
        target = min(idxs, key=lambda i: (len(assigned[i]), i))
        assigned[target].append(url)

    # 각 프로필 안에서는 원래 순서 유지
    result = []
    for urls, mine in zip(profile_urls, assigned):
        mine = set(mine)
        result.append([u for u in urls if u in mine])
    return result


class BandMacroApp:
    """밴드 매크로 메인 GUI 애플리케이션"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("밴드 매크로 V2.5")
        self.root.geometry(window_geometry(self.root, 620, 820))
        self.root.minsize(560, 420)
        self.root.resizable(True, True)

        # 상태 변수
        self.automation = None
        self.worker_thread = None
        self.is_running = False
        self.stop_event = threading.Event()

        # GUI 변수
        self.var_delay = ctk.StringVar(value="600")
        self.var_image_first = ctk.BooleanVar(value=True)
        self.var_random_post = ctk.BooleanVar(value=False)
        self.var_repeat_count = ctk.StringVar(value="9999")
        self.var_system_delay = ctk.StringVar(value="1.5")
        self.var_final_delay = ctk.StringVar(value="2")
        self.var_random_phrase = ctk.BooleanVar(value=True)
        self.var_board_index = ctk.StringVar(value="2")
        self.var_browser = ctk.StringVar(value="chrome")
        self.var_incognito = ctk.BooleanVar(value=False)
        self.var_use_gologin = ctk.BooleanVar(value=False)
        self.var_gologin_dedupe = ctk.BooleanVar(value=False)
        self.var_gologin_api_key = ctk.StringVar(value="")
        self.gologin_profiles = []       # [{"id": ..., "name": ...}]
        self.profile_vars = {}           # {profile_id: BooleanVar}
        self.var_timer_enabled = ctk.BooleanVar(value=False)
        self.var_start_hour = ctk.StringVar(value="09")
        self.var_start_minute = ctk.StringVar(value="00")
        self.var_end_hour = ctk.StringVar(value="18")
        self.var_end_minute = ctk.StringVar(value="00")

        self._build_gui()

    def _build_gui(self):
        """GUI를 구성합니다. ①~⑦ 순서대로 조작하면 되도록 배치합니다."""
        # 메인 스크롤 프레임
        main_frame = ctk.CTkScrollableFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # ═══════════════════════════════════════════
        #  헤더
        # ═══════════════════════════════════════════
        header = ctk.CTkLabel(
            main_frame, text="밴드 매크로 V2.5",
            font=ctk.CTkFont(size=22, weight="bold"))
        header.pack(pady=(0, 2))
        ctk.CTkLabel(main_frame, text="①부터 ⑦까지 순서대로 진행하세요.  ? 를 누르면 설명이 나옵니다.",
                     text_color=COLOR_MUTED).pack(pady=(0, 10))

        # ═══════════════════════════════════════════
        #  ①~⑤ 준비 단계 카드
        # ═══════════════════════════════════════════
        steps_card = ctk.CTkFrame(main_frame, corner_radius=12)
        steps_card.pack(fill="x", pady=(0, 8))

        # ① 글작성 폴더
        step1 = self._step_row(steps_card, 1, first=True)
        ctk.CTkButton(step1, text="글작성 폴더 열기", width=140, height=28,
                      command=self.open_content_folder).pack(side="left")
        self._help_button(step1, "content_folder")
        self._hint(step1, "글 폴더 만들고 txt·이미지 넣기")

        # ② 이미지 가공
        step2 = self._step_row(steps_card, 2)
        ctk.CTkButton(step2, text="이미지 가공", width=140, height=28,
                      fg_color=COLOR_ACCENT, command=self.process_images).pack(side="left")
        self._help_button(step2, "process_images")
        self._hint(step2, "(선택) 큰 이미지 용량 줄이기")

        # ③ 랜덤문구
        step3 = self._step_row(steps_card, 3)
        ctk.CTkButton(step3, text="랜덤문구 작성", width=140, height=28,
                      fg_color=COLOR_ACCENT, command=self.edit_random_phrases).pack(side="left")
        self._help_button(step3, "edit_random_phrases")
        ctk.CTkCheckBox(step3, text="랜덤문구 추가", variable=self.var_random_phrase,
                        checkbox_width=20, checkbox_height=20).pack(side="left", padx=(14, 0))
        self._help_button(step3, "random_phrase")

        # GoLogin 멀티 프로필 (선택) — ④ 로그인 전에 설정해야 하므로 ③과 ④ 사이에 둠
        gologin_card = ctk.CTkFrame(steps_card, corner_radius=10, fg_color=COLOR_CARD)
        gologin_card.pack(fill="x", padx=(8 + STEP_BADGE_WIDTH + 6, 12), pady=6)

        gl_header = ctk.CTkFrame(gologin_card, fg_color="transparent")
        gl_header.pack(fill="x", padx=12, pady=(10, 5))
        ctk.CTkCheckBox(gl_header, text="GoLogin 멀티 프로필 사용",
                        variable=self.var_use_gologin,
                        font=ctk.CTkFont(weight="bold"),
                        checkbox_width=20, checkbox_height=20,
                        command=self._toggle_gologin_body).pack(side="left")
        self._help_button(gl_header, "gologin")
        self._hint(gl_header, "여러 계정을 쓸 때만 · ④ 전에 설정")

        # 체크했을 때만 보이는 영역 (API Key + 프로필 목록)
        self.gl_body = ctk.CTkFrame(gologin_card, fg_color="transparent")

        gl_row1 = ctk.CTkFrame(self.gl_body, fg_color="transparent")
        gl_row1.pack(fill="x", padx=12, pady=(0, 5))
        ctk.CTkLabel(gl_row1, text="API Key", width=60, anchor="w").pack(side="left")
        ctk.CTkEntry(gl_row1, textvariable=self.var_gologin_api_key, width=230,
                     placeholder_text="GoLogin API Key 입력").pack(side="left", padx=(0, 8))
        ctk.CTkButton(gl_row1, text="프로필 가져오기", width=120, height=28,
                      fg_color=COLOR_ACCENT, command=self.fetch_gologin_profiles).pack(side="left")
        self._help_button(gl_row1, "gologin_profiles")

        gl_row2 = ctk.CTkFrame(self.gl_body, fg_color="transparent")
        gl_row2.pack(fill="x", padx=12, pady=(0, 5))
        ctk.CTkCheckBox(gl_row2, text="겹치는 밴드는 중복 게시 발행 안함",
                        variable=self.var_gologin_dedupe,
                        checkbox_width=20, checkbox_height=20).pack(side="left")
        self._help_button(gl_row2, "gologin_dedupe")

        # 프로필 수만큼만 늘어나는 목록 (전체 화면이 스크롤되므로 별도 스크롤 없음)
        self.gl_profile_frame = ctk.CTkFrame(self.gl_body, corner_radius=8)
        self.gl_profile_frame.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(self.gl_profile_frame, text="프로필을 가져오면 여기에 표시됩니다.",
                     text_color=COLOR_MUTED).pack(pady=6)
        self._toggle_gologin_body()

        # ④ 브라우저 선택 + 로그인
        step4 = self._step_row(steps_card, 4)
        ctk.CTkRadioButton(step4, text="크롬", variable=self.var_browser, width=60,
                           value="chrome", radiobutton_width=18, radiobutton_height=18).pack(side="left")
        ctk.CTkRadioButton(step4, text="엣지", variable=self.var_browser, width=60,
                           value="edge", radiobutton_width=18, radiobutton_height=18).pack(side="left")
        ctk.CTkCheckBox(step4, text="시크릿", variable=self.var_incognito, width=70,
                        checkbox_width=20, checkbox_height=20).pack(side="left")
        self._help_button(step4, "browser")
        ctk.CTkButton(step4, text="로그인 하기", width=110, height=28,
                      fg_color=COLOR_SUCCESS, hover_color="#27ae60",
                      command=self.do_login).pack(side="left", padx=(14, 0))
        self._help_button(step4, "login")

        # ⑤ 밴드주소 가져오기
        step5 = self._step_row(steps_card, 5, last=True)
        ctk.CTkButton(step5, text="밴드주소 가져오기", width=140, height=28,
                      fg_color=COLOR_ACCENT, command=self.fetch_band_urls).pack(side="left")
        self._help_button(step5, "fetch_band_urls")
        self._hint(step5, "아래 URL 목록에 자동으로 채워짐")

        # ═══════════════════════════════════════════
        #  밴드 URL 입력
        # ═══════════════════════════════════════════
        url_header = ctk.CTkFrame(main_frame, fg_color="transparent")
        url_header.pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(url_header, text="밴드 URL 목록",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(side="left")
        self._help_button(url_header, "band_urls")

        self.text_urls = ctk.CTkTextbox(main_frame, height=110, corner_radius=8,
                                        font=ctk.CTkFont(size=12))
        self.text_urls.pack(fill="x", pady=(0, 8))

        # ═══════════════════════════════════════════
        #  ⑥ 세부 설정 카드
        # ═══════════════════════════════════════════
        settings_card = ctk.CTkFrame(main_frame, corner_radius=12)
        settings_card.pack(fill="x", pady=(0, 8))

        step6 = self._step_row(settings_card, 6, first=True)
        ctk.CTkLabel(step6, text="세부 설정 확인",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        self._hint(step6, "처음이면 기본값 그대로 두어도 됩니다")

        row_a = self._indented_row(settings_card)
        self._setting_entry(row_a, "글쓰기 딜레이", self.var_delay, "초", "delay")
        self._setting_entry(row_a, "총 반복 횟수", self.var_repeat_count, "회", "repeat_count")

        row_b = self._indented_row(settings_card)
        self._setting_entry(row_b, "시스템 딜레이", self.var_system_delay, "초", "system_delay")
        self._setting_entry(row_b, "최종 딜레이", self.var_final_delay, "분", "final_delay")

        row_c = self._indented_row(settings_card)
        self._setting_entry(row_c, "게시판 선택", self.var_board_index, "번", "board_index")

        row_d = self._indented_row(settings_card, last=True)
        ctk.CTkCheckBox(row_d, text="이미지 먼저", variable=self.var_image_first,
                        checkbox_width=20, checkbox_height=20).pack(side="left")
        self._help_button(row_d, "image_first")
        ctk.CTkCheckBox(row_d, text="랜덤 글작성", variable=self.var_random_post,
                        checkbox_width=20, checkbox_height=20).pack(side="left", padx=(20, 0))
        self._help_button(row_d, "random_post")

        # ═══════════════════════════════════════════
        #  ⑦ 시작 / 중지 버튼
        # ═══════════════════════════════════════════
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 8))
        self._step_badge(btn_frame, 7).pack(side="left", padx=(8, 6))

        self.btn_start = ctk.CTkButton(
            btn_frame, text="▶  시작", height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLOR_SUCCESS, hover_color="#27ae60",
            command=self.start_macro)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_stop = ctk.CTkButton(
            btn_frame, text="■  중지", height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLOR_DANGER, hover_color="#c0392b",
            state="disabled", command=self.stop_macro)
        self.btn_stop.pack(side="left", expand=True, fill="x")
        self._help_button(btn_frame, "start_stop")

        # ═══════════════════════════════════════════
        #  로그 영역
        # ═══════════════════════════════════════════
        log_label = ctk.CTkLabel(main_frame, text="실행 로그",
                                 font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        log_label.pack(fill="x", pady=(4, 2))

        self.text_log = ctk.CTkTextbox(main_frame, height=120, corner_radius=8,
                                       font=ctk.CTkFont(size=11),
                                       state="disabled")
        self.text_log.pack(fill="x", pady=(0, 12))

        # ═══════════════════════════════════════════
        #  추가 기능 (선택)
        # ═══════════════════════════════════════════
        ctk.CTkLabel(main_frame, text="추가 기능 (선택)",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", pady=(4, 2))

        # 작동시간
        timer_card = ctk.CTkFrame(main_frame, corner_radius=12)
        timer_card.pack(fill="x", pady=(0, 8))

        timer_header = ctk.CTkFrame(timer_card, fg_color="transparent")
        timer_header.pack(fill="x", padx=12, pady=(10, 5))
        ctk.CTkCheckBox(timer_header, text="작동시간 설정", variable=self.var_timer_enabled,
                        font=ctk.CTkFont(weight="bold"),
                        checkbox_width=20, checkbox_height=20).pack(side="left")
        self._help_button(timer_header, "timer")

        timer_row = ctk.CTkFrame(timer_card, fg_color="transparent")
        timer_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(timer_row, text="시작", text_color=COLOR_MUTED).pack(side="left", padx=(10, 5))
        ctk.CTkComboBox(timer_row, variable=self.var_start_hour,
                        values=[f"{h:02d}" for h in range(24)],
                        width=65, state="readonly").pack(side="left")
        ctk.CTkLabel(timer_row, text="시").pack(side="left", padx=3)
        ctk.CTkComboBox(timer_row, variable=self.var_start_minute,
                        values=[f"{m:02d}" for m in range(0, 60, 10)],
                        width=65, state="readonly").pack(side="left")
        ctk.CTkLabel(timer_row, text="분").pack(side="left", padx=(3, 15))

        ctk.CTkLabel(timer_row, text="~  종료", text_color=COLOR_MUTED).pack(side="left", padx=(0, 5))
        ctk.CTkComboBox(timer_row, variable=self.var_end_hour,
                        values=[f"{h:02d}" for h in range(24)],
                        width=65, state="readonly").pack(side="left")
        ctk.CTkLabel(timer_row, text="시").pack(side="left", padx=3)
        ctk.CTkComboBox(timer_row, variable=self.var_end_minute,
                        values=[f"{m:02d}" for m in range(0, 60, 10)],
                        width=65, state="readonly").pack(side="left")
        ctk.CTkLabel(timer_row, text="분").pack(side="left", padx=3)


    # ──────────────────────────────────────────────
    #  GUI 헬퍼 (순서 번호 / 도움말)
    # ──────────────────────────────────────────────
    def _step_badge(self, parent, number):
        """좌측 순서 번호(①②③...) 라벨을 만듭니다."""
        return ctk.CTkLabel(parent, text=STEP_NUMBERS[number - 1], width=STEP_BADGE_WIDTH,
                            font=ctk.CTkFont(size=22, weight="bold"), text_color=COLOR_STEP)

    def _step_row(self, card, number, first=False, last=False):
        """좌측에 순서 번호가 붙은 행을 만들고, 내용을 담을 프레임을 반환합니다."""
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=(8, 12), pady=(10 if first else 3, 10 if last else 3))
        self._step_badge(row, number).pack(side="left", padx=(0, 6))
        return row

    def _indented_row(self, card, last=False):
        """번호 열만큼 들여쓴 행을 만듭니다 (⑥ 설정 항목용)."""
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=(8 + STEP_BADGE_WIDTH + 6, 12), pady=(3, 10 if last else 3))
        return row

    def _setting_entry(self, parent, label, variable, unit, help_key):
        """라벨 + 입력칸 + 단위 + ? 버튼 묶음을 만듭니다."""
        ctk.CTkLabel(parent, text=label, width=90, anchor="w").pack(side="left")
        ctk.CTkEntry(parent, textvariable=variable, width=75).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(parent, text=unit, text_color=COLOR_MUTED, width=16).pack(side="left")
        self._help_button(parent, help_key)
        ctk.CTkFrame(parent, fg_color="transparent", width=18, height=1).pack(side="left")

    def _toggle_gologin_body(self):
        """GoLogin 사용 체크 여부에 따라 API Key/프로필 영역을 보이거나 숨깁니다."""
        if self.var_use_gologin.get():
            self.gl_body.pack(fill="x")
        else:
            self.gl_body.pack_forget()

    def _hint(self, parent, text):
        """버튼 옆 짧은 회색 안내 문구를 붙입니다."""
        ctk.CTkLabel(parent, text=text, text_color=COLOR_MUTED,
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 0))

    def _help_button(self, parent, help_key):
        """클릭하면 설명 창이 뜨는 ? 버튼을 붙입니다."""
        title, body = HELP_TEXTS[help_key]
        btn = ctk.CTkButton(parent, text="?", width=22, height=22, corner_radius=11,
                            font=ctk.CTkFont(size=12, weight="bold"),
                            fg_color=COLOR_HELP, hover_color=COLOR_HELP_HOVER,
                            command=lambda: messagebox.showinfo(title, body, parent=self.root))
        btn.pack(side="left", padx=(4, 0))
        return btn

    # ──────────────────────────────────────────────
    #  로그
    # ──────────────────────────────────────────────
    def log(self, message):
        """로그 메시지를 출력합니다."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"

        def _update():
            self.text_log.configure(state="normal")
            self.text_log.insert("end", line)
            self.text_log.see("end")
            self.text_log.configure(state="disabled")

        self.root.after(0, _update)

    # ──────────────────────────────────────────────
    #  버튼 핸들러
    # ──────────────────────────────────────────────
    def open_content_folder(self):
        """글작성 폴더를 엽니다."""
        os.makedirs(CONTENT_DIR, exist_ok=True)
        os.startfile(CONTENT_DIR)

    def process_images(self):
        """이미지 가공을 실행합니다."""
        self.log("이미지 가공 시작...")

        def _work():
            count = compress_all_content_folders(CONTENT_DIR)
            self.log(f"이미지 가공 완료: {count}개 압축됨")

        threading.Thread(target=_work, daemon=True).start()

    def do_login(self):
        """로그인 페이지를 엽니다. GoLogin 모드면 선택된 프로필 모두 실행."""
        if self.var_use_gologin.get():
            self._launch_gologin_profiles()
            return

        browser = self.var_browser.get()
        incognito = self.var_incognito.get()
        system_delay = float(self.var_system_delay.get())

        self.automation = BandAutomation(
            browser_type=browser,
            incognito=incognito,
            system_delay=system_delay,
            log_callback=self.log
        )
        if not self.automation.open_login_page():
            messagebox.showerror("브라우저 실행 실패",
                                 "브라우저를 열지 못했습니다.\n실행 로그의 안내를 확인해주세요.",
                                 parent=self.root)
            return
        # 선택한 브라우저가 안 돼서 다른 브라우저로 바뀐 경우 화면 선택도 맞춤
        self.var_browser.set(self.automation.browser_type)
        self.log("브라우저에서 로그인을 진행해주세요.")

    def _launch_gologin_profiles(self):
        """선택된 GoLogin 프로필을 모두 실행합니다."""
        from gologin import GoLogin

        api_key = self.var_gologin_api_key.get().strip()
        if not api_key:
            messagebox.showwarning("경고", "GoLogin API Key를 입력해주세요.")
            return

        selected = [pid for pid, var in self.profile_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("경고", "프로필을 선택해주세요.")
            return

        # 실행 중에 다시 누르면 같은 프로필이 두 번 열리므로 막음
        if getattr(self, "gologin_launching", False):
            self.log("GoLogin 브라우저를 여는 중입니다. 끝날 때까지 기다려주세요.")
            return
        self.gologin_launching = True

        # GoLogin 인스턴스 저장 (나중에 stop용)
        self.gologin_instances = []
        self.gologin_automations = []
        self.gologin_names = []          # gologin_automations와 같은 순서의 프로필 이름

        def _launch():
            try:
                _launch_all()
            finally:
                self.gologin_launching = False

        def _launch_all():
            for p_idx, profile_id in enumerate(selected):
                profile_name = next(
                    (p["name"] for p in self.gologin_profiles if p["id"] == profile_id),
                    profile_id)

                try:
                    gl = GoLogin({"token": api_key, "profile_id": profile_id})
                    problem = gologin_profile_problem(gl)
                    if problem and "subscription" in problem.lower():
                        # 계정 단위 문제라 나머지 프로필도 같은 이유로 실패함 → 바로 중단
                        self.log(f"[{profile_name}] 시작 불가: {problem}")
                        self.log("GoLogin 구독이 만료되어 브라우저를 열 수 없습니다. 실행을 중단합니다.")
                        self.root.after(0, lambda: messagebox.showwarning(
                            "GoLogin 구독 만료",
                            "GoLogin 워크스페이스 구독이 종료되어 브라우저를 열 수 없습니다.\n\n"
                            "GoLogin 웹사이트에서 요금제를 갱신한 뒤 다시 시도해주세요.\n"
                            "(프로필 목록 가져오기는 되지만, 브라우저 실행은 유료 구독이 필요합니다)",
                            parent=self.root))
                        break
                    if problem:
                        self.log(f"[{profile_name}] 시작 불가: {problem}")
                        continue
                    debugger_address = gl.start()
                    self.log(f"[{profile_name}] 브라우저 시작: {debugger_address}")

                    time.sleep(3)  # GoLogin 브라우저 완전 로드 대기

                    automation = BandAutomation(
                        system_delay=float(self.var_system_delay.get()),
                        log_callback=self.log
                    )
                    browser_path = getattr(gl, "executablePath", "")
                    if automation.connect_gologin(debugger_address, browser_path):
                        # 밴드 로그인 페이지로 이동 (JS로 강제)
                        time.sleep(2)
                        try:
                            # 새 탭으로 밴드 로그인 페이지 열기
                            automation.driver.execute_script("window.open('https://auth.band.us/login_page', '_blank');")
                            time.sleep(1)
                            # 새 탭으로 전환
                            handles = automation.driver.window_handles
                            automation.driver.switch_to.window(handles[-1])
                        except Exception:
                            try:
                                automation.driver.get("https://auth.band.us/login_page")
                            except Exception:
                                pass
                        self.gologin_instances.append(gl)
                        self.gologin_automations.append(automation)
                        self.gologin_names.append(profile_name)
                        self.log(f"[{profile_name}] 밴드 로그인 페이지 열림 - 로그인해주세요.")
                    else:
                        self.log(f"[{profile_name}] 연결 실패 - 브라우저는 유지됩니다.")

                except Exception as e:
                    self.log(f"[{profile_name}] 시작 실패: {e}")

                time.sleep(2)  # 프로필 간 시작 간격

            self.log(f"\n총 {len(self.gologin_automations)}개 브라우저 실행 완료. 각 브라우저에서 로그인해주세요.")

        threading.Thread(target=_launch, daemon=True).start()

    def fetch_band_urls(self):
        """가입된 밴드 URL을 가져옵니다. GoLogin 모드면 프로필별로 나눠서 채웁니다."""
        if self.var_use_gologin.get():
            self._fetch_gologin_band_urls()
            return
        if not self.automation or not self.automation.driver:
            self.log("먼저 로그인을 해주세요.")
            return

        self.log("밴드 주소 가져오는 중...")

        def _work():
            urls = self.automation.fetch_band_urls()
            if urls:
                def _update():
                    self.text_urls.delete("1.0", "end")
                    self.text_urls.insert("1.0", "\n".join(urls))
                self.root.after(0, _update)

        threading.Thread(target=_work, daemon=True).start()

    def _fetch_gologin_band_urls(self):
        """GoLogin 프로필마다 가입 밴드를 가져와 URL 목록에 '# [프로필명]' 구역으로 채웁니다."""
        if not getattr(self, "gologin_automations", None):
            messagebox.showwarning("경고", "먼저 ④ 로그인 하기를 눌러 GoLogin 브라우저를 실행하고\n"
                                           "각 브라우저에서 로그인해주세요.", parent=self.root)
            return
        if self.is_running or getattr(self, "gologin_fetching", False):
            self.log("작업이 진행 중입니다. 끝난 뒤 다시 눌러주세요.")
            return
        self.gologin_fetching = True
        dedupe = self.var_gologin_dedupe.get()  # tkinter 값은 메인 스레드에서 읽음
        self.log("프로필별 밴드 주소 가져오는 중...")

        def _work():
            try:
                profile_urls = self._collect_gologin_urls(dedupe)
                text = format_profile_sections(self.gologin_names, profile_urls)
                total = sum(len(u) for u in profile_urls)

                def _update():
                    self.text_urls.delete("1.0", "end")
                    self.text_urls.insert("1.0", text)
                self.root.after(0, _update)
                self.log(f"프로필 {len(profile_urls)}개, 밴드 {total}개를 URL 목록에 채웠습니다. "
                         "확인 후 ⑦ 시작을 눌러주세요.")
            finally:
                self.gologin_fetching = False

        threading.Thread(target=_work, daemon=True).start()

    def edit_random_phrases(self):
        """랜덤 문구 파일을 메모장으로 엽니다."""
        if not os.path.exists(RANDOM_PHRASES_FILE):
            with open(RANDOM_PHRASES_FILE, "w", encoding="utf-8") as f:
                f.write("오늘도 좋은 하루 되세요!\n")
        os.startfile(RANDOM_PHRASES_FILE)

    def fetch_gologin_profiles(self):
        """GoLogin API에서 프로필 목록을 가져옵니다."""
        api_key = self.var_gologin_api_key.get().strip()
        if not api_key:
            messagebox.showwarning("경고", "GoLogin API Key를 입력해주세요.")
            return

        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get("https://api.gologin.com/browser/v2", headers=headers, timeout=15)
            if resp.status_code != 200:
                messagebox.showerror("오류", f"API 요청 실패: {resp.status_code}\n{resp.text[:200]}")
                return

            data = resp.json()
            profiles = data.get("profiles", [])
            self.gologin_profiles = [{"id": p["id"], "name": p.get("name", p["id"])} for p in profiles]

            # 체크박스 렌더링
            for widget in self.gl_profile_frame.winfo_children():
                widget.destroy()

            self.profile_vars = {}
            if not self.gologin_profiles:
                ctk.CTkLabel(self.gl_profile_frame, text="프로필이 없습니다.",
                             text_color=COLOR_MUTED).pack()
                return

            for p in self.gologin_profiles:
                var = ctk.BooleanVar(value=True)
                self.profile_vars[p["id"]] = var
                ctk.CTkCheckBox(self.gl_profile_frame, text=f"{p['name']}",
                                variable=var, checkbox_width=18, checkbox_height=18).pack(anchor="w", padx=5, pady=1)

            self.log(f"GoLogin 프로필 {len(self.gologin_profiles)}개 로드 완료")
        except Exception as e:
            messagebox.showerror("오류", f"프로필 가져오기 실패: {e}")

    # ──────────────────────────────────────────────
    #  작동시간 타이머
    # ──────────────────────────────────────────────
    def _is_within_operating_hours(self):
        """현재 시간이 작동시간 범위 안인지 확인합니다."""
        if not self.var_timer_enabled.get():
            return True

        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        start_minutes = int(self.var_start_hour.get()) * 60 + int(self.var_start_minute.get())
        end_minutes = int(self.var_end_hour.get()) * 60 + int(self.var_end_minute.get())

        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes < end_minutes
        else:
            return current_minutes >= start_minutes or current_minutes < end_minutes

    def _wait_for_operating_hours(self):
        """작동시간이 될 때까지 대기합니다. 중지 시 False 반환."""
        if self._is_within_operating_hours():
            return True

        start_h = self.var_start_hour.get()
        start_m = self.var_start_minute.get()
        end_h = self.var_end_hour.get()
        end_m = self.var_end_minute.get()
        self.log(f"작동시간 외 ({start_h}:{start_m}~{end_h}:{end_m}). 대기 중...")

        while not self._is_within_operating_hours():
            if self.stop_event.is_set():
                return False
            time.sleep(10)

        self.log("작동시간 도달! 매크로 재개합니다.")
        return True

    # ──────────────────────────────────────────────
    #  컨텐츠 로딩
    # ──────────────────────────────────────────────
    def _load_content_folders(self):
        """컨텐츠 폴더 목록을 로드합니다."""
        folders = []
        if not os.path.exists(CONTENT_DIR):
            return folders
        for name in sorted(os.listdir(CONTENT_DIR)):
            path = os.path.join(CONTENT_DIR, name)
            if os.path.isdir(path) and not name.startswith(SKIP_FOLDER_PREFIX):
                folders.append(path)
        return folders

    def _load_content(self, folder_path):
        """폴더에서 텍스트와 이미지를 로드합니다."""
        text_content = ""
        image_paths = []
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}

        for filename in sorted(os.listdir(folder_path)):
            filepath = os.path.join(folder_path, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext == '.txt':
                with open(filepath, "r", encoding="utf-8") as f:
                    text_content = f.read().strip()
            elif ext in image_exts:
                image_paths.append(filepath)

        return text_content, image_paths

    def _get_random_phrase(self):
        """랜덤 문구를 하나 가져옵니다."""
        if not os.path.exists(RANDOM_PHRASES_FILE):
            return ""
        try:
            with open(RANDOM_PHRASES_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            if lines:
                return random.choice(lines)
        except Exception:
            pass
        return ""

    # ──────────────────────────────────────────────
    #  매크로 실행
    # ──────────────────────────────────────────────
    def start_macro(self):
        """매크로를 시작합니다."""
        use_gologin = self.var_use_gologin.get()

        # GoLogin 모드: URL 목록에 '# [프로필명]' 구역이 있으면 그대로, 없으면 시작 시 프로필별 수집
        band_urls = []
        gologin_sections = None
        gologin_dedupe = False
        if use_gologin:
            if getattr(self, "gologin_fetching", False):
                messagebox.showwarning("경고", "프로필별 밴드 주소를 가져오는 중입니다. 끝난 뒤 시작해주세요.")
                return
            gologin_sections = parse_profile_sections(self.text_urls.get("1.0", "end"))
            gologin_dedupe = self.var_gologin_dedupe.get()
        else:
            urls_text = self.text_urls.get("1.0", "end").strip()
            if not urls_text:
                messagebox.showwarning("경고", "밴드 URL을 입력해주세요.")
                return

            for line in urls_text.split("\n"):
                line = line.strip()
                if line.startswith("https://band.us/band/"):
                    band_urls.append(line)
            if not band_urls:
                messagebox.showwarning("경고", "유효한 밴드 URL이 없습니다.\nhttps://band.us/band/... 형식으로 입력해주세요.")
                return

        content_folders = self._load_content_folders()
        if not content_folders:
            messagebox.showwarning(
                "경고", "글작성 폴더(content/)에 올릴 글 폴더를 만들어주세요.\n\n"
                        "_sample 폴더를 복사해서 이름을 바꾸면 됩니다.\n"
                        "(이름이 _ 로 시작하는 폴더는 올라가지 않습니다)")
            return

        if not use_gologin:
            if not self.automation or not self.automation.driver:
                messagebox.showwarning("경고", "먼저 로그인을 해주세요.")
                return
        else:
            if not hasattr(self, 'gologin_automations') or not self.gologin_automations:
                messagebox.showwarning("경고", "먼저 로그인 하기를 눌러 GoLogin 브라우저를 실행해주세요.")
                return

        # 설정값 파싱
        try:
            delay_parts = self.var_delay.get().split("~")
            delay_min = int(delay_parts[0])
            delay_max = int(delay_parts[1]) if len(delay_parts) > 1 else delay_min
        except ValueError:
            delay_min, delay_max = 600, 600

        try:
            repeat_count = int(self.var_repeat_count.get())
        except ValueError:
            repeat_count = 10

        try:
            system_delay = float(self.var_system_delay.get())
        except ValueError:
            system_delay = 1.5

        try:
            final_delay_min = int(self.var_final_delay.get())
        except ValueError:
            final_delay_min = 2

        try:
            board_index = int(self.var_board_index.get())
        except ValueError:
            board_index = 0

        image_first = self.var_image_first.get()
        random_post = self.var_random_post.get()
        use_random_phrase = self.var_random_phrase.get()

        # UI 상태 변경
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.is_running = True
        self.stop_event.clear()

        def _worker():
            try:
                if use_gologin:
                    self._run_gologin_macro(
                        gologin_sections, content_folders,
                        repeat_count, delay_min, delay_max,
                        system_delay, final_delay_min, board_index,
                        image_first, random_post, use_random_phrase,
                        dedupe=gologin_dedupe)
                else:
                    self._run_normal_macro(
                        self.automation, band_urls, content_folders,
                        repeat_count, delay_min, delay_max,
                        system_delay, final_delay_min, board_index,
                        image_first, random_post, use_random_phrase)
            except Exception as e:
                self.log(f"매크로 오류: {e}")
            finally:
                self.is_running = False
                def _ui_reset():
                    self.btn_start.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
                self.root.after(0, _ui_reset)

        self.worker_thread = threading.Thread(target=_worker, daemon=True)
        self.worker_thread.start()

    def _run_posting_loop(self, automation, band_urls, content_folders,
                          repeat_count, delay_min, delay_max,
                          system_delay, final_delay_min, board_index,
                          image_first, random_post, use_random_phrase,
                          content_offset=0):
        """포스팅 반복 루프 (일반/GoLogin 공용).

        content_offset: 시작 글 폴더 위치. GoLogin 프로필마다 다르게 주어
        같은 회차에 프로필끼리 같은 글을 쓰지 않도록 합니다.
        """
        for cycle in range(1, repeat_count + 1):
            if self.stop_event.is_set():
                break

            if random_post:
                folder = random.choice(content_folders)
            else:
                folder = content_folders[(cycle - 1 + content_offset) % len(content_folders)]

            text_content, image_paths = self._load_content(folder)
            folder_name = os.path.basename(folder)

            if not text_content and not image_paths:
                self.log(f"컨텐츠 없음: {folder_name} (스킵)")
                continue

            self.log(f"\n── 사이클 {cycle}/{repeat_count} 시작 (폴더: {folder_name}) ──")

            for url_idx, band_url in enumerate(band_urls):
                if self.stop_event.is_set():
                    break
                if not self._wait_for_operating_hours():
                    break

                phrase = ""
                if use_random_phrase:
                    phrase = self._get_random_phrase()

                clean_url = band_url.split("#")[0]
                self.log(f"[{url_idx + 1}/{len(band_urls)}] 폴더: {folder_name} → {clean_url}")

                success = automation.write_post(
                    band_url=band_url,
                    text_content=text_content,
                    image_paths=image_paths,
                    image_first=image_first,
                    board_index=board_index,
                    random_phrase=phrase,
                    system_delay=system_delay
                )

                if success:
                    self.log(f"글쓰기 성공 - {clean_url}")
                    # 성공 시에만 딜레이 적용
                    if not self.stop_event.is_set() and url_idx < len(band_urls) - 1:
                        delay = random.randint(delay_min, delay_max)
                        self.log(f"다음 밴드까지 {delay}초 대기")
                        for _ in range(delay):
                            if self.stop_event.is_set():
                                break
                            time.sleep(1)
                else:
                    self.log(f"글쓰기 실패 - {clean_url} → 다음 밴드로 이동")

            if not self.stop_event.is_set() and cycle < repeat_count:
                final_seconds = final_delay_min * 60
                self.log(f"최종 딜레이: {final_delay_min}분 대기 중...")
                for _ in range(final_seconds):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)

    def _run_normal_macro(self, automation, band_urls, content_folders,
                          repeat_count, delay_min, delay_max,
                          system_delay, final_delay_min, board_index,
                          image_first, random_post, use_random_phrase):
        """일반 모드 매크로 (기존 방식)."""
        self.log("=" * 40)
        self.log("매크로 시작!")
        self.log(f"밴드 URL: {len(band_urls)}개")
        self.log(f"컨텐츠 폴더: {len(content_folders)}개")
        self.log(f"반복 횟수: {repeat_count}회")
        self.log(f"글쓰기 딜레이: {delay_min}~{delay_max}초")
        self.log("=" * 40)

        self._run_posting_loop(automation, band_urls, content_folders,
                               repeat_count, delay_min, delay_max,
                               system_delay, final_delay_min, board_index,
                               image_first, random_post, use_random_phrase)
        self.log("\n매크로 완료!")

    # ──────────────────────────────────────────────
    #  GoLogin 멀티 프로필
    # ──────────────────────────────────────────────
    def _gologin_prefixes(self):
        """프로필별 로그 머리말([프로필명]) 목록."""
        names = getattr(self, "gologin_names", [])
        return [f"[{names[i] if i < len(names) else f'브라우저{i + 1}'}]"
                for i in range(len(self.gologin_automations))]

    def _with_profile_log(self, automation, prefix, work):
        """automation 로그에 프로필 이름을 붙인 채로 work()를 실행합니다."""
        orig_log = automation.log
        automation.log = lambda msg: self.log(f"{prefix} {msg}")
        try:
            return work()
        except Exception as e:
            automation.log(f"오류: {e}")
        finally:
            automation.log = orig_log

    def _run_per_profile(self, target):
        """target(automation, idx)를 프로필마다 동시에 실행하고 모두 끝날 때까지 기다립니다."""
        threads = [threading.Thread(target=target, args=(a, i), daemon=True)
                   for i, a in enumerate(self.gologin_automations)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def _collect_gologin_urls(self, dedupe):
        """프로필마다 자기 계정의 가입 밴드를 동시에 가져오고,
        옵션이 켜져 있으면 겹치는 밴드를 한 프로필에만 배정합니다."""
        prefixes = self._gologin_prefixes()
        profile_urls = [[] for _ in self.gologin_automations]

        def _fetch(automation, idx):
            self.log(f"{prefixes[idx]} 가입한 밴드 주소 가져오는 중...")
            profile_urls[idx] = self._with_profile_log(
                automation, prefixes[idx], automation.fetch_band_urls) or []

        self._run_per_profile(_fetch)

        if dedupe:
            assigned = assign_shared_bands(profile_urls)
            removed = sum(len(a) for a in profile_urls) - sum(len(a) for a in assigned)
            if removed:
                self.log(f"여러 프로필이 함께 가입한 밴드 {removed}건을 한 프로필에만 배정했습니다.")
            profile_urls = assigned
        return profile_urls

    def _profile_urls_from_sections(self, sections):
        """URL 목록의 '# [프로필명]' 구역을 실행 중인 프로필 순서에 맞춰 나눕니다."""
        names = getattr(self, "gologin_names", [])
        by_name = dict(sections)
        for name, _ in sections:
            if name not in names:
                self.log(f"URL 목록의 [{name}] 구역은 실행 중인 프로필이 아니라서 건너뜁니다.")
        return [by_name.get(name, []) for name in names]

    def _run_gologin_macro(self, sections, content_folders,
                           repeat_count, delay_min, delay_max,
                           system_delay, final_delay_min, board_index,
                           image_first, random_post, use_random_phrase, dedupe=False):
        """GoLogin 멀티 프로필 매크로.

        sections: URL 목록에서 읽은 [(프로필명, [URL...]), ...].
                  ⑤로 채운 목록이 있으면 그대로 쓰고, 없으면(None) 지금 프로필별로 가져옴.
        프로필마다 글 폴더 시작 위치를 다르게 해서 동시에 글쓰기.
        """
        prefixes = self._gologin_prefixes()

        self.log("=" * 40)
        self.log(f"GoLogin 매크로 시작! 프로필 {len(self.gologin_automations)}개 (동시 실행)")
        self.log(f"컨텐츠 폴더: {len(content_folders)}개")
        self.log("=" * 40)

        if sections is None:
            self.log("URL 목록에 프로필별 구역이 없어 지금 프로필마다 가입 밴드를 가져옵니다.")
            profile_urls = self._collect_gologin_urls(dedupe)
        else:
            self.log("URL 목록의 프로필별 구역대로 글을 씁니다.")
            profile_urls = self._profile_urls_from_sections(sections)
        if self.stop_event.is_set():
            return

        for idx, urls in enumerate(profile_urls):
            self.log(f"{prefixes[idx]} 글 쓸 밴드 {len(urls)}개, 시작 글 폴더 "
                     f"{os.path.basename(content_folders[idx % len(content_folders)])}")

        # 동시에 글쓰기 (프로필마다 시작 글 폴더를 한 칸씩 밀어서)
        def _post(automation, idx):
            urls = profile_urls[idx]
            if not urls:
                self.log(f"{prefixes[idx]} 글 쓸 밴드가 없어 건너뜁니다.")
                return

            def work():
                self._run_posting_loop(
                    automation, urls, content_folders,
                    repeat_count, delay_min, delay_max,
                    system_delay, final_delay_min, board_index,
                    image_first, random_post, use_random_phrase,
                    content_offset=idx)
                automation.log("완료!")

            self._with_profile_log(automation, prefixes[idx], work)

        self._run_per_profile(_post)
        self.log("\n모든 프로필 매크로 완료!")

    def stop_macro(self):
        """매크로를 중지합니다."""
        self.stop_event.set()
        self.is_running = False
        self.log("매크로 중지 요청...")
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    # ──────────────────────────────────────────────
    #  실행
    # ──────────────────────────────────────────────
    def run(self):
        """앱을 실행합니다."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        """종료 시 브라우저도 닫습니다."""
        if self.is_running:
            if not messagebox.askyesno("종료", "매크로가 실행 중입니다. 종료하시겠습니까?"):
                return
            self.stop_event.set()

        if self.automation:
            self.automation.close()

        self.root.destroy()


def run_selftest():
    """exe 실행 환경 점검 (밴드매크로V2.5.exe --selftest).

    필요한 부품을 하나씩 불러보고 결과를 system/selftest.txt에 남깁니다.
    다른 PC에서 문제가 생겼을 때 원인을 찾는 용도입니다.
    """
    import platform
    import traceback

    results = []

    def check(name, func):
        try:
            detail = func()
            results.append(f"[OK]   {name}" + (f" - {detail}" if detail else ""))
        except Exception as e:
            results.append(f"[FAIL] {name} - {type(e).__name__}: {e}")
            results.append("       " + traceback.format_exc().strip().splitlines()[-1])

    def selenium_manager():
        from selenium.webdriver.common.selenium_manager import SeleniumManager
        return str(SeleniumManager()._get_binary())

    def driver_for(browser):
        from selenium.webdriver.common.selenium_manager import SeleniumManager
        paths = SeleniumManager().binary_paths(["--browser", browser])
        return f"driver={paths.get('driver_path')} browser={paths.get('browser_path')}"

    def gologin_import():
        from gologin import GoLogin
        return GoLogin.__module__

    def sample_write():
        test_path = os.path.join(SYSTEM_DIR, "selftest_write.tmp")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_path)
        return SYSTEM_DIR

    check("OS", lambda: f"{platform.platform()} / {platform.machine()}")
    check("실행 위치", lambda: BASE_DIR)
    check("폴더 쓰기 권한", sample_write)
    check("customtkinter", lambda: ctk.__version__)
    check("Pillow", lambda: __import__("PIL").__version__)
    check("pyautogui", lambda: __import__("pyautogui").__version__)
    check("selenium", lambda: __import__("selenium").__version__)
    check("Selenium Manager", selenium_manager)
    check("크롬 드라이버", lambda: driver_for("chrome"))
    check("엣지 드라이버", lambda: driver_for("MicrosoftEdge"))
    check("gologin", gologin_import)
    check("requests", lambda: __import__("requests").__version__)

    report = "\n".join(results)
    with open(os.path.join(SYSTEM_DIR, "selftest.txt"), "w", encoding="utf-8") as f:
        f.write(report + "\n")
    return report


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        run_selftest()
        sys.exit(0)
    app = BandMacroApp()
    app.run()
