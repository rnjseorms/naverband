"""네이버 밴드 자동 글쓰기 매크로 V2.5 - 메인 GUI (CustomTkinter)"""

import os
import sys
import json
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


class BandMacroApp:
    """밴드 매크로 메인 GUI 애플리케이션"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("밴드 매크로 V2.5")
        self.root.geometry("620x820")
        self.root.resizable(True, True)

        # 상태 변수
        self.automation = None
        self.worker_thread = None
        self.is_running = False
        self.stop_event = threading.Event()

        # GUI 변수
        self.var_delay = ctk.StringVar(value="1000")
        self.var_image_first = ctk.BooleanVar(value=True)
        self.var_random_post = ctk.BooleanVar(value=False)
        self.var_repeat_count = ctk.StringVar(value="9999")
        self.var_system_delay = ctk.StringVar(value="1.5")
        self.var_final_delay = ctk.StringVar(value="10")
        self.var_random_phrase = ctk.BooleanVar(value=True)
        self.var_board_index = ctk.StringVar(value="2")
        self.var_browser = ctk.StringVar(value="chrome")
        self.var_incognito = ctk.BooleanVar(value=False)
        self.var_backup_list = ctk.StringVar(value="")
        self.var_use_gologin = ctk.BooleanVar(value=False)
        self.var_gologin_api_key = ctk.StringVar(value="")
        self.gologin_profiles = []       # [{"id": ..., "name": ...}]
        self.profile_vars = {}           # {profile_id: BooleanVar}
        self.var_timer_enabled = ctk.BooleanVar(value=False)
        self.var_start_hour = ctk.StringVar(value="09")
        self.var_start_minute = ctk.StringVar(value="00")
        self.var_end_hour = ctk.StringVar(value="18")
        self.var_end_minute = ctk.StringVar(value="00")

        self._build_gui()
        self._load_backup_list()

    def _build_gui(self):
        """GUI를 구성합니다."""
        # 메인 스크롤 프레임
        main_frame = ctk.CTkScrollableFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # ═══════════════════════════════════════════
        #  헤더
        # ═══════════════════════════════════════════
        header = ctk.CTkLabel(
            main_frame, text="밴드 매크로 V2.5",
            font=ctk.CTkFont(size=22, weight="bold"))
        header.pack(pady=(0, 12))

        # ═══════════════════════════════════════════
        #  설정 카드
        # ═══════════════════════════════════════════
        settings_card = ctk.CTkFrame(main_frame, corner_radius=12)
        settings_card.pack(fill="x", pady=(0, 8))

        # Row 0: 글쓰기 딜레이 + 체크박스
        row0 = ctk.CTkFrame(settings_card, fg_color="transparent")
        row0.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(row0, text="글쓰기 딜레이", width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(row0, textvariable=self.var_delay, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row0, text="초", text_color=COLOR_MUTED).pack(side="left", padx=(0, 15))
        ctk.CTkCheckBox(row0, text="이미지 먼저", variable=self.var_image_first,
                        checkbox_width=20, checkbox_height=20).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(row0, text="랜덤 글작성", variable=self.var_random_post,
                        checkbox_width=20, checkbox_height=20).pack(side="left")

        # Row 1: 총 반복 횟수 + 버튼들
        row1 = ctk.CTkFrame(settings_card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(row1, text="총 반복 횟수", width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(row1, textvariable=self.var_repeat_count, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row1, text="회", text_color=COLOR_MUTED).pack(side="left", padx=(0, 15))
        ctk.CTkButton(row1, text="글작성 폴더 열기", width=120, height=28,
                      command=self.open_content_folder).pack(side="left", padx=(0, 5))
        ctk.CTkButton(row1, text="이미지 가공", width=90, height=28,
                      fg_color=COLOR_ACCENT, command=self.process_images).pack(side="left")

        # Row 2: 시스템 딜레이 + 버튼들
        row2 = ctk.CTkFrame(settings_card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(row2, text="시스템 딜레이", width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(row2, textvariable=self.var_system_delay, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row2, text="초", text_color=COLOR_MUTED).pack(side="left", padx=(0, 15))
        ctk.CTkButton(row2, text="로그인 하기", width=120, height=28,
                      fg_color=COLOR_SUCCESS, hover_color="#27ae60",
                      command=self.do_login).pack(side="left", padx=(0, 5))
        ctk.CTkButton(row2, text="밴드주소 가져오기", width=130, height=28,
                      fg_color=COLOR_ACCENT, command=self.fetch_band_urls).pack(side="left")

        # Row 3: 최종 딜레이 + 랜덤문구
        row3 = ctk.CTkFrame(settings_card, fg_color="transparent")
        row3.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(row3, text="최종 딜레이", width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(row3, textvariable=self.var_final_delay, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row3, text="분", text_color=COLOR_MUTED).pack(side="left", padx=(0, 15))
        ctk.CTkCheckBox(row3, text="랜덤문구 추가", variable=self.var_random_phrase,
                        checkbox_width=20, checkbox_height=20).pack(side="left", padx=(0, 10))
        ctk.CTkButton(row3, text="랜덤문구 작성", width=110, height=28,
                      fg_color=COLOR_ACCENT, command=self.edit_random_phrases).pack(side="left")

        # Row 4: 게시판 선택 + 브라우저
        row4 = ctk.CTkFrame(settings_card, fg_color="transparent")
        row4.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(row4, text="게시판 선택", width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(row4, textvariable=self.var_board_index, width=100).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row4, text="번", text_color=COLOR_MUTED).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(row4, text="크롬", variable=self.var_browser,
                           value="chrome", radiobutton_width=18, radiobutton_height=18).pack(side="left", padx=(0, 8))
        ctk.CTkRadioButton(row4, text="엣지", variable=self.var_browser,
                           value="edge", radiobutton_width=18, radiobutton_height=18).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(row4, text="시크릿", variable=self.var_incognito,
                        checkbox_width=20, checkbox_height=20).pack(side="left", padx=(0, 10))
        ctk.CTkButton(row4, text="영역 캡처", width=90, height=28,
                      fg_color="#7f8c8d", hover_color="#636e72",
                      command=self.capture_area).pack(side="left")

        # ═══════════════════════════════════════════
        #  백업 카드
        # ═══════════════════════════════════════════
        backup_card = ctk.CTkFrame(main_frame, corner_radius=12)
        backup_card.pack(fill="x", pady=(0, 8))

        backup_row = ctk.CTkFrame(backup_card, fg_color="transparent")
        backup_row.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(backup_row, text="백업", width=40, anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.combo_backup = ctk.CTkComboBox(
            backup_row, variable=self.var_backup_list,
            width=200, state="readonly")
        self.combo_backup.pack(side="left", padx=(0, 8))
        ctk.CTkButton(backup_row, text="내보내기", width=80, height=28,
                      command=self.export_backup).pack(side="left", padx=(0, 5))
        ctk.CTkButton(backup_row, text="가져오기", width=80, height=28,
                      fg_color=COLOR_ACCENT, command=self.import_backup).pack(side="left")

        # ═══════════════════════════════════════════
        #  GoLogin 카드
        # ═══════════════════════════════════════════
        gologin_card = ctk.CTkFrame(main_frame, corner_radius=12)
        gologin_card.pack(fill="x", pady=(0, 8))

        gl_header = ctk.CTkFrame(gologin_card, fg_color="transparent")
        gl_header.pack(fill="x", padx=12, pady=(10, 5))
        ctk.CTkCheckBox(gl_header, text="GoLogin 멀티 프로필 사용",
                        variable=self.var_use_gologin,
                        font=ctk.CTkFont(weight="bold"),
                        checkbox_width=20, checkbox_height=20).pack(side="left")

        gl_row1 = ctk.CTkFrame(gologin_card, fg_color="transparent")
        gl_row1.pack(fill="x", padx=12, pady=(0, 5))
        ctk.CTkLabel(gl_row1, text="API Key", width=60, anchor="w").pack(side="left")
        ctk.CTkEntry(gl_row1, textvariable=self.var_gologin_api_key, width=280,
                     placeholder_text="GoLogin API Key 입력").pack(side="left", padx=(0, 8))
        ctk.CTkButton(gl_row1, text="프로필 가져오기", width=120, height=28,
                      fg_color=COLOR_ACCENT, command=self.fetch_gologin_profiles).pack(side="left")

        self.gl_profile_frame = ctk.CTkScrollableFrame(gologin_card, height=40, corner_radius=8)
        self.gl_profile_frame.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(self.gl_profile_frame, text="프로필을 가져오면 여기에 표시됩니다.",
                     text_color=COLOR_MUTED).pack()

        # ═══════════════════════════════════════════
        #  타이머 카드
        # ═══════════════════════════════════════════
        timer_card = ctk.CTkFrame(main_frame, corner_radius=12)
        timer_card.pack(fill="x", pady=(0, 8))

        timer_header = ctk.CTkFrame(timer_card, fg_color="transparent")
        timer_header.pack(fill="x", padx=12, pady=(10, 5))
        ctk.CTkCheckBox(timer_header, text="작동시간 설정", variable=self.var_timer_enabled,
                        font=ctk.CTkFont(weight="bold"),
                        checkbox_width=20, checkbox_height=20).pack(side="left")

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

        # ═══════════════════════════════════════════
        #  밴드 URL 입력
        # ═══════════════════════════════════════════
        url_label = ctk.CTkLabel(main_frame, text="밴드 URL 목록",
                                 font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        url_label.pack(fill="x", pady=(4, 2))

        self.text_urls = ctk.CTkTextbox(main_frame, height=130, corner_radius=8,
                                        font=ctk.CTkFont(size=12))
        self.text_urls.pack(fill="x", pady=(0, 8))

        # ═══════════════════════════════════════════
        #  시작 / 중지 버튼
        # ═══════════════════════════════════════════
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 8))

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

        # ═══════════════════════════════════════════
        #  로그 영역
        # ═══════════════════════════════════════════
        log_label = ctk.CTkLabel(main_frame, text="실행 로그",
                                 font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        log_label.pack(fill="x", pady=(4, 2))

        self.text_log = ctk.CTkTextbox(main_frame, height=120, corner_radius=8,
                                       font=ctk.CTkFont(size=11),
                                       state="disabled")
        self.text_log.pack(fill="both", expand=True)

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
        self.automation.open_login_page()
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

        # GoLogin 인스턴스 저장 (나중에 stop용)
        self.gologin_instances = []
        self.gologin_automations = []

        def _launch():
            for p_idx, profile_id in enumerate(selected):
                profile_name = next(
                    (p["name"] for p in self.gologin_profiles if p["id"] == profile_id),
                    profile_id)

                try:
                    gl = GoLogin({"token": api_key, "profile_id": profile_id})
                    debugger_address = gl.start()
                    self.log(f"[{profile_name}] 브라우저 시작: {debugger_address}")

                    time.sleep(3)  # GoLogin 브라우저 완전 로드 대기

                    automation = BandAutomation(
                        system_delay=float(self.var_system_delay.get()),
                        log_callback=self.log
                    )
                    if automation.connect_gologin(debugger_address):
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
                        self.log(f"[{profile_name}] 밴드 로그인 페이지 열림 - 로그인해주세요.")
                    else:
                        self.log(f"[{profile_name}] 연결 실패 - 브라우저는 유지됩니다.")

                except Exception as e:
                    self.log(f"[{profile_name}] 시작 실패: {e}")

                time.sleep(2)  # 프로필 간 시작 간격

            self.log(f"\n총 {len(self.gologin_automations)}개 브라우저 실행 완료. 각 브라우저에서 로그인해주세요.")

        threading.Thread(target=_launch, daemon=True).start()

    def fetch_band_urls(self):
        """가입된 밴드 URL을 가져옵니다."""
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

    def capture_area(self):
        """영역 캡처 기능입니다."""
        self.log("영역 캡처: 브라우저의 새로고침 버튼을 드래그하여 캡처해주세요.")

        import pyautogui

        self.root.iconify()
        time.sleep(0.5)

        try:
            messagebox.showinfo("영역 캡처",
                "확인을 누른 뒤 브라우저의 새로고침 버튼 영역을 마우스로 드래그해주세요.\n"
                "3초 뒤 캡처가 시작됩니다.")
            time.sleep(3)

            screenshot = pyautogui.screenshot()
            browser = self.var_browser.get()
            save_name = f"{browser}_loading.png"
            save_path = os.path.join(SYSTEM_DIR, save_name)
            screenshot.save(save_path)
            self.log(f"캡처 저장됨: {save_path}")
        except Exception as e:
            self.log(f"캡처 실패: {e}")
        finally:
            self.root.deiconify()

    # ──────────────────────────────────────────────
    #  백업
    # ──────────────────────────────────────────────
    def _get_settings(self):
        """현재 설정값을 딕셔너리로 반환합니다."""
        return {
            "delay": self.var_delay.get(),
            "image_first": self.var_image_first.get(),
            "random_post": self.var_random_post.get(),
            "repeat_count": self.var_repeat_count.get(),
            "system_delay": self.var_system_delay.get(),
            "final_delay": self.var_final_delay.get(),
            "random_phrase": self.var_random_phrase.get(),
            "board_index": self.var_board_index.get(),
            "browser": self.var_browser.get(),
            "incognito": self.var_incognito.get(),
            "band_urls": self.text_urls.get("1.0", "end").strip(),
            "timer_enabled": self.var_timer_enabled.get(),
            "start_hour": self.var_start_hour.get(),
            "start_minute": self.var_start_minute.get(),
            "end_hour": self.var_end_hour.get(),
            "end_minute": self.var_end_minute.get(),
        }

    def _apply_settings(self, settings):
        """딕셔너리로부터 설정값을 적용합니다."""
        self.var_delay.set(settings.get("delay", "150~250"))
        self.var_image_first.set(settings.get("image_first", True))
        self.var_random_post.set(settings.get("random_post", False))
        self.var_repeat_count.set(settings.get("repeat_count", "10"))
        self.var_system_delay.set(settings.get("system_delay", "1.5"))
        self.var_final_delay.set(settings.get("final_delay", "10"))
        self.var_random_phrase.set(settings.get("random_phrase", True))
        self.var_board_index.set(settings.get("board_index", "2"))
        self.var_browser.set(settings.get("browser", "chrome"))
        self.var_incognito.set(settings.get("incognito", False))
        self.text_urls.delete("1.0", "end")
        self.text_urls.insert("1.0", settings.get("band_urls", ""))
        self.var_timer_enabled.set(settings.get("timer_enabled", False))
        self.var_start_hour.set(settings.get("start_hour", "09"))
        self.var_start_minute.set(settings.get("start_minute", "00"))
        self.var_end_hour.set(settings.get("end_hour", "18"))
        self.var_end_minute.set(settings.get("end_minute", "00"))

    def export_backup(self):
        """설정을 백업 파일로 내보냅니다."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Data_{timestamp}.json"
        filepath = os.path.join(SYSTEM_DIR, filename)

        settings = self._get_settings()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

        self.log(f"백업 내보내기 완료: {filename}")
        self._load_backup_list()

    def import_backup(self):
        """선택된 백업 파일에서 설정을 가져옵니다."""
        selected = self.var_backup_list.get()
        if not selected:
            self.log("백업 파일을 선택해주세요.")
            return

        filepath = os.path.join(SYSTEM_DIR, selected)
        if not os.path.exists(filepath):
            self.log("백업 파일이 존재하지 않습니다.")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                settings = json.load(f)
            self._apply_settings(settings)
            self.log(f"백업 가져오기 완료: {selected}")
        except Exception as e:
            self.log(f"백업 가져오기 실패: {e}")

    def _load_backup_list(self):
        """백업 파일 목록을 로드합니다."""
        files = []
        if os.path.exists(SYSTEM_DIR):
            for f in sorted(os.listdir(SYSTEM_DIR)):
                if f.startswith("Data_") and f.endswith(".json"):
                    files.append(f)
        self.combo_backup.configure(values=files)
        if files:
            self.var_backup_list.set(files[-1])

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
            if os.path.isdir(path):
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
        urls_text = self.text_urls.get("1.0", "end").strip()
        if not urls_text:
            messagebox.showwarning("경고", "밴드 URL을 입력해주세요.")
            return

        band_urls = []
        for line in urls_text.split("\n"):
            line = line.strip()
            if line.startswith("https://band.us/band/"):
                band_urls.append(line)
        if not band_urls:
            messagebox.showwarning("경고", "유효한 밴드 URL이 없습니다.\nhttps://band.us/band/... 형식으로 입력해주세요.")
            return

        content_folders = self._load_content_folders()
        if not content_folders:
            messagebox.showwarning("경고", "글작성 폴더(content/)에 컨텐츠 폴더를 만들어주세요.")
            return

        use_gologin = self.var_use_gologin.get()

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
            delay_min, delay_max = 150, 250

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
            final_delay_min = 10

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
                        band_urls, content_folders,
                        repeat_count, delay_min, delay_max,
                        system_delay, final_delay_min, board_index,
                        image_first, random_post, use_random_phrase)
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
                          image_first, random_post, use_random_phrase):
        """포스팅 반복 루프 (일반/GoLogin 공용)."""
        for cycle in range(1, repeat_count + 1):
            if self.stop_event.is_set():
                break

            if random_post:
                folder = random.choice(content_folders)
            else:
                folder = content_folders[(cycle - 1) % len(content_folders)]

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
                        self.log(f"딜레이 : {delay * 1000}")
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

    def _run_gologin_macro(self, band_urls, content_folders,
                           repeat_count, delay_min, delay_max,
                           system_delay, final_delay_min, board_index,
                           image_first, random_post, use_random_phrase):
        """GoLogin 멀티 프로필 매크로 - 이미 열린 브라우저들을 동시 병렬 실행."""
        automations = self.gologin_automations

        self.log("=" * 40)
        self.log(f"GoLogin 매크로 시작! 브라우저 {len(automations)}개 (동시 실행)")
        self.log(f"밴드 URL: {len(band_urls)}개")
        self.log(f"컨텐츠 폴더: {len(content_folders)}개")
        self.log("=" * 40)

        def _run_single(automation, idx):
            """개별 브라우저 실행 (별도 스레드)."""
            prefix = f"[브라우저{idx+1}]"
            orig_log = automation.log
            automation.log = lambda msg: self.log(f"{prefix} {msg}")

            try:
                # 밴드 URL 가져오기
                if not band_urls or band_urls == [""]:
                    automation.log("밴드 주소 자동 가져오기...")
                    urls = automation.fetch_band_urls()
                else:
                    urls = band_urls

                self._run_posting_loop(
                    automation, urls, content_folders,
                    repeat_count, delay_min, delay_max,
                    system_delay, final_delay_min, board_index,
                    image_first, random_post, use_random_phrase)

                automation.log("완료!")
            except Exception as e:
                automation.log(f"오류: {e}")
            finally:
                automation.log = orig_log

        # 모든 브라우저를 동시에 스레드로 실행
        threads = []
        for idx, automation in enumerate(automations):
            t = threading.Thread(target=_run_single, args=(automation, idx), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.log("\n모든 브라우저 매크로 완료!")

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


if __name__ == "__main__":
    app = BandMacroApp()
    app.run()
