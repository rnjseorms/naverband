"""네이버 밴드 자동화 모듈 - Selenium 기반 브라우저 제어"""

import os
import re
import json
import urllib.request
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    UnexpectedAlertPresentException, NoAlertPresentException
)

BAND_LOGIN_URL = "https://auth.band.us/login_page"
BROWSER_NAMES = {"chrome": "크롬", "edge": "엣지"}


def explain_driver_error(error):
    """브라우저/드라이버 오류를 사용자가 할 일이 보이는 한국어 안내로 바꿉니다."""
    raw = (getattr(error, "msg", None) or str(error) or "").strip()
    first_line = raw.splitlines()[0].split("; For documentation")[0] if raw else "알 수 없는 오류"
    text = raw.lower()
    if "only supports" in text or ("version" in text and "session not created" in text):
        hint = "브라우저와 드라이버 버전이 맞지 않습니다. 브라우저를 최신으로 업데이트한 뒤 다시 시도해주세요."
    elif ("cannot find" in text and "binary" in text) or "no such file" in text:
        hint = "브라우저가 설치되어 있지 않습니다. 크롬이나 엣지를 설치하거나 다른 브라우저를 선택해주세요."
    elif "unable to obtain" in text or "selenium manager" in text or "failed to download" in text:
        hint = ("브라우저 드라이버를 내려받지 못했습니다. 처음 실행할 때는 인터넷 연결이 필요합니다. "
                "회사망이라면 방화벽/보안 프로그램을 확인해주세요.")
    elif "not reachable" in text or "cannot connect" in text:
        hint = "열린 브라우저에 연결하지 못했습니다. 브라우저 창을 닫고 ④ 로그인 하기를 다시 눌러주세요."
    else:
        hint = "브라우저를 모두 닫고 다시 시도해주세요."
    return f"{hint} [{first_line[:150]}]"
DORMANT_FOLDER_TEXT = "방문이 뜸한 밴드"

# 화면에서 글자가 정확히 일치하는 가장 안쪽 요소를 찾는 스크립트 (없으면 null)
FIND_TEXT_ELEMENT_JS = r"""
const text = arguments[0];
return Array.from(document.querySelectorAll('body *')).find(el =>
    el.children.length === 0 && (el.textContent || '').trim() === text) || null;
"""

# 내 밴드 페이지에서 가입한 밴드 링크만 반환하는 스크립트.
# 첫 번째 AD(광고/추천 게시글) 카드 또는 "이런 밴드는 어때요" 영역을 경계로,
# 그보다 앞에 있는 밴드 링크만 문서 순서대로 돌려줍니다. 경계를 못 찾으면 null.
JOINED_BAND_LINKS_JS = r"""
const isMarker = t => t === 'AD' || /^AD\s*·/.test(t) ||
    t.includes('추천 게시글') || t.includes('이런 밴드는 어때요');
const bandId = a => ((a.getAttribute('href') || '').match(/\/band\/(\d+)/) || [])[1];
const anchors = Array.from(document.querySelectorAll('a[href*="/band/"]')).filter(bandId);

// 1) 경계: 광고 카드(class에 adBand 포함 — 광고 문구가 바뀌어도 유지됨) +
//    경계 문구가 들어있는 가장 안쪽 요소들
const isAd = el => !!el.closest('[class*="adBand"]');
const markers = Array.from(document.querySelectorAll('[class*="adBand"]')).concat(
    Array.from(document.querySelectorAll('body *')).filter(el =>
        el.children.length === 0 && isMarker((el.textContent || '').trim())));
if (markers.length === 0) return null;

// 2) 문구 요소를 카드 단위까지 키움: 밴드가 2개 이상 들어있는 영역 직전 조상까지 올라감
const idsIn = el => new Set(anchors.filter(a => el.contains(a) || a.contains(el)).map(bandId));
const toCard = el => {
    let node = el;
    while (node.parentElement && node.parentElement !== document.body &&
           idsIn(node.parentElement).size <= 1) {
        node = node.parentElement;
    }
    return node;
};

// 3) 문서 순서상 가장 앞선 경계
let cutoff = null;
for (const m of markers) {
    const card = toCard(m);
    if (!cutoff || (card.compareDocumentPosition(cutoff) & Node.DOCUMENT_POSITION_FOLLOWING)) {
        cutoff = card;
    }
}

return anchors
    .filter(a => !isAd(a) && !cutoff.contains(a) && !a.contains(cutoff) &&
                 (a.compareDocumentPosition(cutoff) & Node.DOCUMENT_POSITION_FOLLOWING))
    .map(a => a.href);
"""


class BandAutomation:
    """네이버 밴드 자동 글쓰기 클래스"""

    def __init__(self, browser_type="chrome", incognito=False, system_delay=1.5, log_callback=None):
        self.driver = None
        self.browser_type = browser_type
        self.incognito = incognito
        self.system_delay = system_delay
        self.log = log_callback or print

    # ──────────────────────────────────────────────
    #  유틸
    # ──────────────────────────────────────────────
    def _dismiss_alert(self):
        """Alert가 있으면 닫는다."""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            self.log(f"알림 닫음: {alert_text}")
            return True
        except (NoAlertPresentException, Exception):
            return False

    def _safe_click(self, element):
        """클릭 시도. 실패하면 JS로 클릭."""
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

    # ──────────────────────────────────────────────
    #  브라우저
    # ──────────────────────────────────────────────
    def _new_driver(self, browser_type):
        """크롬/엣지 드라이버를 만듭니다. 드라이버는 Selenium Manager가 브라우저 버전에 맞춰 자동으로 받습니다."""
        if browser_type == "chrome":
            options = ChromeOptions()
            private_flag, driver_cls = "--incognito", webdriver.Chrome
        else:
            options = EdgeOptions()
            private_flag, driver_cls = "--inprivate", webdriver.Edge
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        if self.incognito:
            options.add_argument(private_flag)
        return driver_cls(options=options)

    def start_browser(self):
        """브라우저를 시작합니다. 선택한 브라우저가 안 되면 다른 브라우저(크롬↔엣지)로 자동 전환합니다."""
        first = self.browser_type if self.browser_type in ("chrome", "edge") else "chrome"
        second = "edge" if first == "chrome" else "chrome"
        errors = []
        for browser_type in (first, second):
            try:
                self.driver = self._new_driver(browser_type)
            except Exception as e:
                errors.append((browser_type, e))
                self.log(f"{BROWSER_NAMES[browser_type]} 시작 실패: {explain_driver_error(e)}")
                continue

            if browser_type != first:
                self.log(f"{BROWSER_NAMES[first]} 대신 {BROWSER_NAMES[browser_type]}로 실행했습니다.")
            self.browser_type = browser_type
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self.log("브라우저가 시작되었습니다.")
            return True

        self.log("크롬과 엣지 모두 실행하지 못했습니다. 위 안내를 확인해주세요.")
        return False

    def connect_gologin(self, debugger_address, browser_path=None):
        """GoLogin 프로필의 debugger_address로 Selenium을 연결합니다.

        chromedriver는 브라우저 버전과 맞아야 붙을 수 있는데, GoLogin 브라우저(Orbita)는
        PC에 설치된 크롬과 버전이 다르고 프로필마다도 다를 수 있습니다. 그래서
        ① Orbita 실행 파일 기준 → ② 브라우저에 직접 물어본 버전 기준 → ③ 기본값 순으로 시도합니다.
        """
        attempts = []
        if browser_path and os.path.exists(browser_path):
            attempts.append(("실행 파일 기준", {"binary_location": browser_path}))
        version = self._debugger_browser_version(debugger_address)
        if version:
            attempts.append((f"버전 {version} 기준", {"browser_version": version}))
        attempts.append(("기본값", {}))

        last_error = None
        for label, settings in attempts:
            options = ChromeOptions()
            options.add_experimental_option("debuggerAddress", debugger_address)
            for key, value in settings.items():
                setattr(options, key, value)
            try:
                self.driver = webdriver.Chrome(options=options)
            except Exception as e:
                last_error = e
                continue
            try:
                self.driver.maximize_window()
            except Exception:
                pass  # 창 크기 조절 실패는 연결과 무관
            self.log(f"GoLogin 프로필 연결 완료 ({label}): {debugger_address}")
            return True

        self.log(f"GoLogin 연결 실패: {explain_driver_error(last_error)}")
        return False

    @staticmethod
    def _debugger_browser_version(debugger_address):
        """디버그 포트로 브라우저에 버전을 물어 주 버전(예: '144')을 반환합니다. 실패 시 None."""
        try:
            with urllib.request.urlopen(f"http://{debugger_address}/json/version", timeout=5) as resp:
                browser = json.loads(resp.read().decode("utf-8")).get("Browser", "")
            match = re.search(r"/(\d+)\.", browser)
            return match.group(1) if match else None
        except Exception:
            return None

    def disconnect(self):
        """Selenium 연결만 해제합니다 (GoLogin 프로필은 유지)."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def open_login_page(self):
        """로그인 페이지를 엽니다."""
        if not self.driver:
            if not self.start_browser():
                return False
        try:
            self.driver.get(BAND_LOGIN_URL)
            self.log("로그인 페이지가 열렸습니다. 수동으로 로그인해주세요.")
            return True
        except Exception as e:
            self.log(f"로그인 페이지 열기 실패: {e}")
            return False

    # ──────────────────────────────────────────────
    #  밴드 주소 가져오기
    # ──────────────────────────────────────────────
    def fetch_band_urls(self):
        """가입된 밴드 URL 목록을 가져옵니다."""
        if not self.driver:
            self.log("브라우저가 시작되지 않았습니다.")
            return []
        try:
            self.driver.get("https://band.us/bands")
            time.sleep(self.system_delay * 3)

            # 스크롤하여 모두 로드
            last_count = 0
            for _ in range(20):
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/band/']")
                if len(links) == last_count:
                    break
                last_count = len(links)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(self.system_delay)

            # URL 추출 (가입한 밴드 목록만: AD 카드 / 추천 밴드 영역부터는 제외)
            hrefs = self.driver.execute_script(JOINED_BAND_LINKS_JS)
            if hrefs is None:
                self.log("AD/추천 영역을 찾지 못해 페이지 전체 링크를 가져옵니다.")
                hrefs = [link.get_attribute("href") for link in
                         self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/band/']")]
            # '방문이 뜸한 밴드' 폴더 안의 가입 밴드도 추가
            hrefs = list(hrefs) + self._fetch_dormant_folder_hrefs()

            seen = set()
            band_urls = []
            for href in hrefs:
                if href and "/band/" in href:
                    parts = href.split("/band/")
                    if len(parts) > 1:
                        band_id = parts[1].split("/")[0].split("?")[0]
                        if band_id and band_id.isdigit() and band_id not in seen:
                            seen.add(band_id)
                            band_urls.append(f"https://band.us/band/{band_id}")

            self.log(f"총 {len(band_urls)}개의 밴드를 찾았습니다.")
            return band_urls
        except Exception as e:
            self.log(f"밴드 주소 가져오기 실패: {e}")
            return []

    def _fetch_dormant_folder_hrefs(self):
        """'방문이 뜸한 밴드' 폴더를 열어 그 안의 밴드 링크를 가져옵니다."""
        try:
            folder = self.driver.execute_script(FIND_TEXT_ELEMENT_JS, DORMANT_FOLDER_TEXT)
            if not folder:
                return []

            # 클릭 전 링크에 표시 → 클릭 후 표시 없는 링크 = 폴더에서 새로 나온 링크
            start_url = self.driver.current_url
            self.driver.execute_script(
                "document.querySelectorAll('a').forEach(a => a.dataset.bmSeen = '1');")
            self._safe_click(folder)
            time.sleep(self.system_delay * 2)

            if self.driver.current_url != start_url:
                # 별도 페이지로 이동한 경우: 그 페이지의 밴드 링크
                hrefs = self.driver.execute_script(JOINED_BAND_LINKS_JS)
                if hrefs is None:
                    hrefs = [a.get_attribute("href") for a in
                             self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/band/']")]
                self.driver.back()
                time.sleep(self.system_delay)
            else:
                # 팝업으로 열린 경우: 목록 끝까지 스크롤하며 새 링크 수집
                last_count = -1
                for _ in range(20):
                    new_links = self.driver.find_elements(
                        By.CSS_SELECTOR, "a[href*='/band/']:not([data-bm-seen])")
                    if len(new_links) == last_count:
                        break
                    last_count = len(new_links)
                    if new_links:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'end'});", new_links[-1])
                    time.sleep(self.system_delay)
                hrefs = [a.get_attribute("href") for a in new_links]
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

            hrefs = [h for h in hrefs if h and re.search(r"/band/\d+", h)]
            if hrefs:
                self.log(f"'{DORMANT_FOLDER_TEXT}' 폴더에서 링크 {len(hrefs)}개를 찾았습니다.")
            else:
                self.log(f"'{DORMANT_FOLDER_TEXT}' 폴더를 열었지만 밴드 링크를 찾지 못했습니다.")
            return hrefs
        except Exception as e:
            self.log(f"'{DORMANT_FOLDER_TEXT}' 폴더 읽기 실패: {e}")
            return []

    # ──────────────────────────────────────────────
    #  글쓰기 메인 흐름
    # ──────────────────────────────────────────────
    def write_post(self, band_url, text_content, image_paths=None,
                   image_first=False, board_index=0, random_phrase="",
                   system_delay=1.5):
        """
        밴드 페이지 접속 → 글쓰기 버튼 클릭 → 사진 첨부 → 텍스트 입력 → 게시
        흐름: 사진버튼 클릭 → 이미지 선택 → 첨부하기 → 텍스트 입력 → 게시
        """
        if not self.driver:
            self.log("브라우저가 시작되지 않았습니다.")
            return False

        band_id = band_url.split("/band/")[1].split("/")[0].split("#")[0].split("?")[0]
        band_page = f"https://band.us/band/{band_id}"

        try:
            # ① 밴드 페이지 접속
            self._dismiss_alert()
            self.driver.get(band_page)
            time.sleep(system_delay * 2)
            self._dismiss_alert()

            # ② "글쓰기" 버튼 찾아서 클릭
            if not self._click_write_button(system_delay):
                self.log(f"글쓰기 버튼 없음 (스킵): {band_id}")
                return False

            time.sleep(system_delay * 2)

            # ③ 에디터가 열렸는지 확인 (placeholder: "새로운 소식을 남겨보세요.")
            editor_found = False
            editor_selectors = [
                ".cke_editable[contenteditable='true']",
                "[contenteditable='true'].contentEditor",
                "[contenteditable='true']",
            ]
            for sel in editor_selectors:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    editor_found = True
                    break
                except TimeoutException:
                    continue

            if not editor_found:
                self.log(f"에디터 로드 실패 (스킵): {band_id}")
                return False

            # ④ 이미지 업로드 (사진 버튼 클릭 → 파일 대화상자 → 첨부하기)
            if image_paths:
                self._upload_images(image_paths, system_delay)
                time.sleep(system_delay * 2)

            # ⑥ 텍스트 입력
            self._write_text(text_content, random_phrase, system_delay)
            time.sleep(system_delay * 2)

            # ⑦ "게시" 버튼 클릭
            if self._click_submit(system_delay):
                return True
            else:
                self.log(f"게시 실패: {band_id}")
                return False

        except UnexpectedAlertPresentException:
            self._dismiss_alert()
            self.log(f"알림 발생, 스킵: {band_id}")
            return False
        except Exception as e:
            self._dismiss_alert()
            self.log(f"글쓰기 실패 ({band_id}): {e}")
            return False

    # ──────────────────────────────────────────────
    #  ② 글쓰기 버튼 클릭
    # ──────────────────────────────────────────────
    def _click_write_button(self, system_delay):
        """밴드 페이지에서 '글쓰기' 버튼을 찾아 클릭합니다."""

        # 방법 1: XPath로 "글쓰기" 텍스트가 포함된 버튼/링크 찾기
        xpath_selectors = [
            "//button[contains(text(),'글쓰기')]",
            "//a[contains(text(),'글쓰기')]",
            "//span[contains(text(),'글쓰기')]/parent::*",
            "//div[contains(text(),'글쓰기')]",
        ]
        for xpath in xpath_selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                self._safe_click(btn)
                self.log("글쓰기 버튼 클릭")
                return True
            except (TimeoutException, NoSuchElementException):
                continue

        # 방법 2: CSS 셀렉터로 글쓰기 관련 버튼 찾기
        css_selectors = [
            "a.postWriteBtn",
            "button.postWriteBtn",
            "a._btnPostWrite",
            "button._btnPostWrite",
            ".postWrite a",
            ".writeBtn",
            "a[href*='post/create']",
        ]
        for sel in css_selectors:
            try:
                btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                self._safe_click(btn)
                self.log("글쓰기 버튼 클릭")
                return True
            except (TimeoutException, NoSuchElementException):
                continue

        # 방법 3: 에디터 영역 직접 클릭 (이미 글쓰기 입력창이 보이는 경우)
        try:
            editor = self.driver.find_element(
                By.CSS_SELECTOR,
                ".cke_editable[contenteditable='true'], "
                "[contenteditable='true'].contentEditor"
            )
            self._safe_click(editor)
            self.log("에디터 영역 직접 클릭")
            return True
        except NoSuchElementException:
            pass

        return False

    # ──────────────────────────────────────────────
    #  ④ 게시판 선택
    # ──────────────────────────────────────────────
    def _select_board_if_exists(self, board_index, system_delay):
        """에디터 팝업 내부의 게시판 선택 드롭다운이 있으면 게시판을 선택합니다."""
        try:
            # 먼저 에디터 팝업 컨테이너를 찾기 (에디터 안에서만 검색하기 위해)
            editor_popup = self.driver.execute_script("""
                // contenteditable 에디터를 포함하는 가장 가까운 팝업/다이얼로그 찾기
                var editor = document.querySelector('[contenteditable="true"]');
                if (!editor) return null;
                var parent = editor;
                for (var i = 0; i < 20; i++) {
                    parent = parent.parentElement;
                    if (!parent) break;
                    var cls = (parent.className || '').toLowerCase();
                    var role = parent.getAttribute('role') || '';
                    if (cls.indexOf('layer') >= 0 || cls.indexOf('popup') >= 0 ||
                        cls.indexOf('modal') >= 0 || cls.indexOf('dialog') >= 0 ||
                        cls.indexOf('write') >= 0 || role === 'dialog') {
                        return parent;
                    }
                }
                // 못 찾으면 에디터에서 10단계 위 부모 반환
                parent = editor;
                for (var j = 0; j < 10; j++) {
                    if (parent.parentElement) parent = parent.parentElement;
                }
                return parent;
            """)

            if not editor_popup:
                return

            # 에디터 팝업 내부에서 "게시판 선택" 텍스트가 있는 요소 찾기
            btn = None
            try:
                candidates = editor_popup.find_elements(By.XPATH,
                    ".//*[contains(text(),'게시판 선택')]")
                for c in candidates:
                    try:
                        if c.is_displayed():
                            btn = c
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            if not btn:
                # 게시판 선택이 없는 밴드 → 정상, 스킵
                return

            self.log("게시판 선택 드롭다운 발견 (에디터 내부)")
            self._safe_click(btn)
            time.sleep(system_delay)

            # 목록에서 선택 (board_index: 0이면 첫 번째 게시판)
            target_index = max(board_index, 1) - 1  # 0-based
            items = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".layerPopup li, .uSelectLayer li, ul.boardList li, "
                "[class*='boardList'] li, [class*='CategoryList'] li, "
                "[role='listbox'] li, [role='option'], "
                ".uDropdownLayer li, .dropdownList li"
            )
            if items:
                try:
                    visible_items = [item for item in items if item.is_displayed()]
                except Exception:
                    visible_items = []
                if not visible_items:
                    visible_items = items
                if target_index < len(visible_items):
                    self._safe_click(visible_items[target_index])
                    self.log(f"게시판 선택: {target_index + 1}번째 항목")
                else:
                    self._safe_click(visible_items[0])
                    self.log("게시판 선택: 첫 번째 항목 (기본)")
                time.sleep(system_delay)
            else:
                self.log("게시판 목록을 찾을 수 없습니다.")
        except Exception as e:
            self.log(f"게시판 선택 실패: {e}")

    # ──────────────────────────────────────────────
    #  ⑤-1 텍스트 입력
    # ──────────────────────────────────────────────
    def _write_text(self, text_content, random_phrase, system_delay, preserve_images=False):
        """에디터에 텍스트를 입력합니다.
        이미지 아래에 텍스트 → (랜덤문구 있으면) 한줄 공백 후 랜덤문구."""
        try:
            # 에디터 찾기
            editor = None
            for sel in [".cke_editable[contenteditable='true']",
                        "[contenteditable='true'].contentEditor",
                        "[contenteditable='true']"]:
                try:
                    editor = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                    break
                except TimeoutException:
                    continue

            if not editor:
                self.log("에디터를 찾을 수 없습니다.")
                return

            # 텍스트 조합: 본문 + (한줄 공백 + 랜덤문구)
            full_text = text_content
            if random_phrase:
                full_text += "\n\n" + random_phrase

            # 방법 1: ActionChains로 에디터 맨 끝으로 이동 → 키보드 입력
            try:
                # 에디터 포커스 (ActionChains 사용)
                ActionChains(self.driver).move_to_element(editor).click().perform()
                time.sleep(0.5)

                # Ctrl+End로 커서를 에디터 맨 끝으로 이동 (이미지 뒤)
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys(
                    Keys.END).key_up(Keys.CONTROL).perform()
                time.sleep(0.3)

                # Enter로 이미지 뒤에 새 줄 시작
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                time.sleep(0.3)

                # 텍스트 줄 단위 입력 (ActionChains 사용)
                lines = full_text.split("\n")
                for i, line in enumerate(lines):
                    if line:
                        ActionChains(self.driver).send_keys(line).perform()
                    if i < len(lines) - 1:
                        ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(
                            Keys.ENTER).key_up(Keys.SHIFT).perform()
                    time.sleep(0.05)

                time.sleep(system_delay)
                self.log("텍스트 입력 완료")
                return
            except Exception as e:
                self.log(f"ActionChains 입력 실패 ({e}), JS 입력으로 전환")

            # 방법 2: JavaScript로 텍스트 삽입 (기존 내용 보존 - 이미지 포함)
            html_text = full_text.replace("\n", "<br>")
            self.driver.execute_script("""
                var editor = arguments[0];
                editor.focus();
                // 기존 내용(이미지 포함) 뒤에 텍스트 추가
                var existing = editor.innerHTML || '';
                editor.innerHTML = existing + '<br>' + arguments[1];
                // input 이벤트 발생시켜서 Band이 인식하도록
                var event = new Event('input', { bubbles: true });
                editor.dispatchEvent(event);
                // 커서를 맨 끝으로
                var range = document.createRange();
                var sel = window.getSelection();
                range.selectNodeContents(editor);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            """, editor, html_text)
            time.sleep(system_delay)
            self.log("텍스트 입력 완료 (JS)")

        except Exception as e:
            self.log(f"텍스트 입력 실패: {e}")

    # ──────────────────────────────────────────────
    #  ⑤ 이미지 업로드
    #  사람처럼: 사진 버튼 클릭 → 파일 대화상자 → 첨부하기
    # ──────────────────────────────────────────────
    def _upload_images(self, image_paths, system_delay):
        """사진 버튼 클릭 → 네이티브 파일 대화상자 → 첨부하기."""
        if not image_paths:
            return

        try:
            abs_paths = [os.path.abspath(p) for p in image_paths]

            # ── 1단계: 사진 첨부용 file input 찾기 (label._btnAttachPhoto 안의 input) ──
            file_input = self.driver.execute_script("""
                // 방법 1: _btnAttachPhoto label 안의 file input (정확한 셀렉터)
                var label = document.querySelector('label._btnAttachPhoto');
                if (label) {
                    var input = label.querySelector('input[type="file"]');
                    if (input) return input;
                }
                // 방법 2: name="attachment"이고 accept="image/*"인 file input
                var inputs = document.querySelectorAll('input[type="file"][name="attachment"]');
                for (var i = 0; i < inputs.length; i++) {
                    if ((inputs[i].accept || '').indexOf('image') >= 0) return inputs[i];
                }
                // 방법 3: accept에 image가 있는 아무 file input
                var allInputs = document.querySelectorAll('input[type="file"]');
                for (var i = 0; i < allInputs.length; i++) {
                    if ((allInputs[i].accept || '').indexOf('image') >= 0) return allInputs[i];
                }
                return null;
            """)

            if not file_input:
                self.log("사진 file input을 찾을 수 없습니다.")
                return

            self.log("사진 file input 발견 (label._btnAttachPhoto)")

            # ── 2단계: file input에 직접 파일 경로 전달 ──
            file_input.send_keys(abs_paths[0])
            self.log(f"이미지 파일 전달 완료: {abs_paths[0]}")

            # ── 4단계: "사진 올리기" 팝업 → "첨부하기" 대기 & 클릭 ──
            time.sleep(system_delay * 3)

            attach_btn = None
            for i in range(20):
                try:
                    btns = self.driver.find_elements(
                        By.XPATH, "//button[contains(text(),'첨부하기')]")
                    for btn in btns:
                        try:
                            if btn.is_displayed() and btn.is_enabled():
                                attach_btn = btn
                                break
                        except Exception:
                            continue
                    if attach_btn:
                        self.log(f"첨부하기 버튼 발견 ({i+1}초)")
                        break
                except Exception:
                    pass
                time.sleep(1)

            if attach_btn:
                time.sleep(1)
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", attach_btn)
                    time.sleep(0.3)
                    ActionChains(self.driver).move_to_element(attach_btn).pause(0.3).click().perform()
                    self.log("첨부하기 클릭 완료")
                except Exception as e1:
                    self.log(f"ActionChains 실패 ({e1}), JS 클릭")
                    self.driver.execute_script("arguments[0].click();", attach_btn)

                time.sleep(system_delay * 3)
                self._wait_popup_close(system_delay)
                self.log("이미지 업로드 완료")
            else:
                self.log("첨부하기 버튼을 찾지 못했습니다.")

        except Exception as e:
            self.log(f"이미지 업로드 실패: {e}")

    def _wait_popup_close(self, system_delay):
        """사진 올리기 팝업이 닫힐 때까지 대기합니다."""
        for _ in range(10):
            # 팝업이 아직 열려있는지 확인
            popups = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".layerPopup, .uModal, .popupLayer")
            visible_popup = False
            for popup in popups:
                try:
                    if popup.is_displayed():
                        visible_popup = True
                        break
                except Exception:
                    pass
            if not visible_popup:
                return True
            time.sleep(0.5)
        return False

    # ──────────────────────────────────────────────
    #  ⑥ 게시 버튼
    # ──────────────────────────────────────────────
    def _click_submit(self, system_delay):
        """에디터 우하단의 '게시' 버튼을 클릭합니다."""
        # 방법 1: _btnSubmitPost 클래스
        for sel in ["button._btnSubmitPost", "button.uButton._btnSubmitPost"]:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                self._safe_click(btn)
                self.log("게시 버튼 클릭")
                time.sleep(system_delay * 3)
                self._dismiss_alert()
                return True
            except TimeoutException:
                continue

        # 방법 2: "게시" 텍스트 버튼 (정확히 일치 + 포함)
        submit_xpaths = [
            "//button[text()='게시']",
            "//button[normalize-space(text())='게시']",
            "//button[contains(text(),'게시')]",
            "//span[text()='게시']/parent::button",
            "//button[contains(@class,'submit') or contains(@class,'Submit')]",
        ]
        for xpath in submit_xpaths:
            try:
                btns = self.driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        self._safe_click(btn)
                        self.log("게시 버튼 클릭")
                        time.sleep(system_delay * 3)
                        self._dismiss_alert()
                        return True
            except Exception:
                continue

        # 방법 3: "완료", "올리기" 텍스트 (fallback)
        try:
            btn = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(text(),'완료') or contains(text(),'올리기')]"
                )))
            self._safe_click(btn)
            self.log("게시 버튼 클릭 (완료/올리기)")
            time.sleep(system_delay * 3)
            self._dismiss_alert()
            return True
        except TimeoutException:
            self.log("게시 버튼을 찾을 수 없습니다.")
            return False

    # ──────────────────────────────────────────────
    #  종료
    # ──────────────────────────────────────────────
    def close(self):
        """브라우저를 종료합니다."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            self.log("브라우저가 종료되었습니다.")
