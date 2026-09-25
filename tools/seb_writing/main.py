# ============================================================
# ĐỨC DẠY BẠN HỌC NHÉ<3
# Tool Chụp Màn V2 -> SEB writing
# Hỗ trợ: Chụp ảnh gom lô + Ctrl+Shift+R bôi đen đề thi
# Trả kết quả: Tự gõ đáp án bằng phím riêng hoặc Ctrl+V
# ============================================================

import ctypes
from ctypes import wintypes
import os
import json
import time
import base64
import threading
import urllib.error
from pathlib import Path

import keyboard
import pyautogui
import pyperclip
from colorama import Fore, Style, init
from google import genai


# ============================================================
# MÀU TERMINAL
# ============================================================

init(autoreset=True)
PINK = Fore.MAGENTA + Style.BRIGHT
CYAN = Fore.CYAN + Style.BRIGHT
GREEN = Fore.GREEN + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
WHITE = Fore.WHITE + Style.BRIGHT
RESET = Style.RESET_ALL

if os.name == "nt":
    os.system("chcp 65001 > nul")
    try:
        os.system("title Tool Chụp Màn V2 -> SEB Writing")
    except Exception:
        pass

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ============================================================
# THƯ MỤC / CONFIG
# ============================================================

BASE_DIR = Path(r"C:\duc")
CONFIG_DIR = BASE_DIR / "configs"
CONFIG_FILE = CONFIG_DIR / "seb_writing.json"
KEY_FILE = BASE_DIR / "key.txt"
PICTURE_DIR = BASE_DIR / "picture" / "seb_writing"
ANSWER_FILE = BASE_DIR / "dapan.txt"

for folder in (BASE_DIR, CONFIG_DIR, PICTURE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

MODEL_MAP = {
    "1": {"name": "Gemini 3.5 Flash-Lite", "model": "gemini-3.5-flash-lite", "daily_limit": 500},
    "2": {"name": "Gemini 3.5 Flash", "model": "gemini-3.5-flash", "daily_limit": 20},
    "3": {"name": "Gemini 3.6 Flash", "model": "gemini-3.6-flash", "daily_limit": 20},
    "4": {"name": "Gemini 3.7 Flash", "model": "gemini-3.7-flash", "daily_limit": 20},
}

DEFAULT_CAPTURE_HOTKEY = "/"
DEFAULT_SEND_HOTKEY = "'"
DEFAULT_SELECTION_HOTKEY = "ctrl+shift+r"
DEFAULT_TYPE_HOTKEY = "-"
DEFAULT_STOP_HOTKEY = "f9"
EXIT_KEY = "esc"

JPEG_QUALITY = 88
TYPING_DELAY = 0.012

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


# ============================================================
# HỖ TRỢ GÕ TỰ ĐỘNG CHỐNG CHẶN PASTE (SEB / WEB QUIZ)
# Sử dụng đa tầng: Win32 SendInput Unicode, keybd_event & keyboard
# ============================================================

def type_char_safe(char):
    """Gõ 1 ký tự chuẩn xác vào ô nhập liệu hiện tại (hỗ trợ 100% tiếng Việt)."""
    if char == "\r":
        return
    if char == "\n":
        try:
            keyboard.send("enter")
            return
        except Exception:
            pass
        try:
            # VK_RETURN = 0x0D
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x0D, 0, 0x0002, 0)
            return
        except Exception:
            pass
    if char == "\t":
        # Tránh phím Tab làm nhảy sang nút Submit/Next của SEB
        for _ in range(4):
            type_char_safe(" ")
        return

    # Tầng 1: Native Windows Unicode thông qua keyboard._winkeyboard
    try:
        import keyboard._winkeyboard as wk
        wk.type_unicode(char)
        return
    except Exception:
        pass

    # Tầng 2: Native keybd_event với flag KEYEVENTF_UNICODE (0x0004)
    try:
        code = ord(char)
        ctypes.windll.user32.keybd_event(0, code, 0x0004, 0)
        ctypes.windll.user32.keybd_event(0, code, 0x0004 | 0x0002, 0)
        return
    except Exception:
        pass

    # Tầng 3: Fallback qua pyautogui
    try:
        pyautogui.write(char)
    except Exception:
        pass


# ============================================================
# HIỂN THỊ
# ============================================================

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_box(title, lines=None, color=PINK, width=68, indent=2):
    if lines is None:
        lines = []
    title = str(title)
    lines = [str(x) for x in lines]
    longest = max([len(title)] + [len(x) for x in lines] + [0])
    box_width = max(width, longest + 4)

    print(color + "╔" + "═" * box_width + "╗")
    print(color + "║" + WHITE + title.center(box_width) + color + "║")
    if lines:
        print(color + "╠" + "═" * box_width + "╣")
        for line in lines:
            print(color + "║" + WHITE + ((" " * indent) + line).ljust(box_width) + color + "║")
    print(color + "╚" + "═" * box_width + "╝")


def show_banner():
    clear()
    print()
    print_box(
        "TOOL CHỤP MÀN V2 -> SEB WRITING",
        [
            "Chuyên viết bài Writing, bài luận & giải đề thi SEB",
            "Hỗ trợ: Chụp ảnh đề bài gom lô + Bôi đen đề thi gửi Gemini",
            "Tự động gõ phím vào SEB (chống chặn paste) hoặc dán Ctrl+V",
        ],
        color=PINK,
        width=74,
    )
    print()


# ============================================================
# CON TRỎ CHUỘT LOADING
# ============================================================

def show_loading_cursor_once(duration=0.5):
    if os.name != "nt":
        return
    try:
        user32 = ctypes.windll.user32
        IDC_WAIT = 32514
        OCR_NORMAL = 32512
        SPI_SETCURSORS = 0x0057

        wait_cursor = user32.LoadCursorW(None, IDC_WAIT)
        if not wait_cursor:
            return
        copied_cursor = user32.CopyImage(wait_cursor, 2, 0, 0, 0)
        if not copied_cursor:
            return
        user32.SetSystemCursor(copied_cursor, OCR_NORMAL)
        time.sleep(duration)
        user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
    except Exception:
        pass


# ============================================================
# CONFIG + API
# ============================================================

def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=4), encoding="utf-8")


def load_config():
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return None


def save_api_key(api_key):
    os.environ["GEMINI_API_KEY"] = api_key
    KEY_FILE.write_text(api_key, encoding="utf-8")


def load_api_key():
    try:
        if KEY_FILE.exists():
            key = KEY_FILE.read_text(encoding="utf-8").strip()
            if key:
                os.environ["GEMINI_API_KEY"] = key
                return key
    except Exception:
        pass
    return None


def validate_api(api_key):
    print(CYAN + "⟳ Đang kiểm tra kết nối API Gemini...")
    try:
        test_client = genai.Client(api_key=api_key)
        response = test_client.interactions.create(
            model="gemini-3.5-flash-lite",
            input="Trả lời ngắn: OK",
        )
        _ = response.output_text
        return True
    except Exception as e:
        print(RED + "❌ API không hợp lệ hoặc hiện không kết nối được.")
        print(e)
        return False


def input_new_api():
    while True:
        print()
        print(CYAN + "⌨ Dán Gemini API key. API được lưu tại C:\\duc\\key.txt")
        api_key = input(WHITE + "🔑 Nhập API: " + RESET).strip().strip('"').strip("'")
        if not api_key:
            print(RED + "❌ API không được để trống.")
            continue
        if validate_api(api_key):
            save_api_key(api_key)
            print(GREEN + "✔ Đã lưu và xác nhận API Gemini thành công.")
            return api_key


def choose_model():
    print()
    print(CYAN + "✦ Chọn model Gemini 1, 2, 3, 4:")
    for key, item in MODEL_MAP.items():
        print(f" [{key}] {item['name']} | {item['daily_limit']} request/ngày")
    while True:
        choice = input(WHITE + "➤ Lựa chọn (1-4): " + RESET).strip()
        if choice in MODEL_MAP:
            item = MODEL_MAP[choice]
            return {
                "level": choice,
                "model": item["model"],
                "model_name": item["name"],
                "daily_limit": item["daily_limit"],
            }
        print(RED + "❌ Chỉ chọn 1, 2, 3 hoặc 4.")


def choose_hotkeys(old_config=None):
    old_config = old_config or {}
    print()
    print(CYAN + "✦ Tùy chỉnh danh sách phím tắt cho SEB Writing:")

    def_cap = old_config.get("capture_hotkey", old_config.get("hotkey", DEFAULT_CAPTURE_HOTKEY))
    def_send = old_config.get("send_hotkey", old_config.get("click_hotkey", DEFAULT_SEND_HOTKEY))
    def_sel = old_config.get("selection_hotkey", DEFAULT_SELECTION_HOTKEY)
    def_type = old_config.get("type_hotkey", DEFAULT_TYPE_HOTKEY)
    def_stop = old_config.get("stop_typing_hotkey", DEFAULT_STOP_HOTKEY)

    while True:
        cap = input(WHITE + f"1. Nút chụp thêm ảnh đề bài [mặc định {def_cap}]: " + RESET).strip() or def_cap
        send = input(WHITE + f"2. Nút gửi tất cả ảnh đề bài [mặc định {def_send}]: " + RESET).strip() or def_send
        sel = input(WHITE + f"3. Phím bôi đen đề thi [mặc định {def_sel}]: " + RESET).strip() or def_sel
        typ = input(WHITE + f"4. Phím tự động gõ vào SEB [mặc định {def_type}]: " + RESET).strip() or def_type
        stop = input(WHITE + f"5. Phím dừng gõ riêng biệt [mặc định {def_stop}]: " + RESET).strip() or def_stop

        keys = [cap.lower(), send.lower(), sel.lower(), typ.lower(), stop.lower()]
        if len(keys) != len(set(keys)) or "esc" in keys:
            print(YELLOW + "⚠ Lỗi: Các phím tắt không được trùng nhau và không được dùng phím 'esc'.")
            print(YELLOW + "Vui lòng nhập lại các phím tắt không bị trùng:")
            continue

        print()
        print(GREEN + "✔ Cấu hình phím tắt hợp lệ:")
        print(f"  • Chụp ảnh đề bài : {cap}")
        print(f"  • Gửi tất cả ảnh  : {send}")
        print(f"  • Bôi đen đề thi  : {sel}")
        print(f"  • Tự động gõ SEB  : {typ}")
        print(f"  • Dừng gõ phím    : {stop}")
        print(f"  • Thoát tool      : ESC")

        return {
            "capture_hotkey": cap,
            "send_hotkey": send,
            "hotkey": cap,
            "click_hotkey": send,
            "selection_hotkey": sel,
            "type_hotkey": typ,
            "stop_typing_hotkey": stop,
        }


def setup():
    show_banner()
    old_config = load_config()
    old_api = load_api_key()

    print(CYAN + "✦ BẮT ĐẦU CẤU HÌNH TOOL:")
    print()

    # --- CÂU HỎI 1: THAY ĐỔI API GEMINI ---
    api_key = None
    if old_api:
        masked = old_api[:6] + "..." + old_api[-4:] if len(old_api) > 10 else "***"
        print(WHITE + f"🔑 API Gemini hiện tại: {YELLOW}{masked}")
        print(CYAN + "✦ Bạn có muốn thay đổi API Gemini cũ không? (Y/N)")
        while True:
            ans = input(WHITE + "➤ Lựa chọn Y/N: " + RESET).strip().upper()
            if ans == "Y":
                api_key = input_new_api()
                break
            elif ans == "N":
                if validate_api(old_api):
                    api_key = old_api
                    print(GREEN + "✔ Tiếp tục sử dụng API Gemini cũ.")
                    break
                else:
                    print(YELLOW + "⚠ API cũ không sử dụng được. Vui lòng nhập API mới:")
                    api_key = input_new_api()
                    break
            print(RED + "❌ Chỉ nhập Y hoặc N.")
    else:
        print(YELLOW + "⚠ Chưa tìm thấy API Gemini cũ tại C:\\duc\\key.txt.")
        api_key = input_new_api()

    # --- CÂU HỎI 2: THAY LẠI HOTKEY MỚI ---
    config = None
    if old_config:
        print()
        print(CYAN + "✦ Bạn có muốn thay lại hotkey mới không? (Y/N)")
        while True:
            ans = input(WHITE + "➤ Lựa chọn Y/N: " + RESET).strip().upper()
            if ans == "Y":
                model_cfg = choose_model()
                hotkeys = choose_hotkeys(old_config)
                config = {**model_cfg, **hotkeys}
                save_config(config)
                break
            elif ans == "N":
                config = old_config
                # Đảm bảo có đủ key mới nếu config cũ chưa có
                needs_save = False
                for k, v in [
                    ("selection_hotkey", DEFAULT_SELECTION_HOTKEY),
                    ("type_hotkey", DEFAULT_TYPE_HOTKEY),
                    ("stop_typing_hotkey", DEFAULT_STOP_HOTKEY),
                    ("capture_hotkey", DEFAULT_CAPTURE_HOTKEY),
                    ("send_hotkey", DEFAULT_SEND_HOTKEY),
                ]:
                    if k not in config:
                        config[k] = v
                        needs_save = True
                if needs_save:
                    save_config(config)
                print(GREEN + "✔ Tiếp tục sử dụng cấu hình hotkey đã lưu.")
                break
            print(RED + "❌ Chỉ nhập Y hoặc N.")
    else:
        print()
        print(YELLOW + "⚠ Chưa có cấu hình hotkey cũ. Thiết lập hotkey ban đầu:")
        model_cfg = choose_model()
        hotkeys = choose_hotkeys()
        config = {**model_cfg, **hotkeys}
        save_config(config)

    return api_key, config


API_KEY, CONFIG = setup()
client = genai.Client(api_key=API_KEY)
MODEL = CONFIG.get("model", "gemini-3.5-flash-lite")

CAPTURE_HOTKEY = CONFIG.get("capture_hotkey", CONFIG.get("hotkey", DEFAULT_CAPTURE_HOTKEY))
SEND_HOTKEY = CONFIG.get("send_hotkey", CONFIG.get("click_hotkey", DEFAULT_SEND_HOTKEY))
SELECTION_HOTKEY = CONFIG.get("selection_hotkey", DEFAULT_SELECTION_HOTKEY)
TYPE_HOTKEY = CONFIG.get("type_hotkey", DEFAULT_TYPE_HOTKEY)
STOP_HOTKEY = CONFIG.get("stop_typing_hotkey", DEFAULT_STOP_HOTKEY)


# ============================================================
# BIẾN TOÀN CỤC & LOCKS
# ============================================================

pending_images = []
pending_lock = threading.Lock()
busy = False
busy_lock = threading.Lock()

last_answer = ""
answer_lock = threading.Lock()
typing_in_progress = False
stop_typing_flag = False

# Quản lý phiên hội thoại nối tiếp (Bản nháp riêng của từng phiên mở tool)
current_interaction_id = None
turn_count = 0
interaction_lock = threading.Lock()


# ============================================================
# GEMINI PROMPTS DÀNH CHO WRITING / TỰ LUẬN SEB
# ============================================================

WRITING_PROMPT_IMAGE = """
Bạn là chuyên gia giải đề thi và viết bài Writing chuyên nghiệp (IELTS, VSTEP, TOEFL, Tiếng Anh/Tiếng Việt, Văn học, Tự luận học thuật).
Đọc kỹ TOÀN BỘ hình ảnh đề bài được gửi kèm.

NHIỆM VỤ:
1. Đọc kỹ yêu cầu đề bài (dạng bài, chủ đề, số từ yêu cầu nếu có, ví dụ 150 từ, 250 từ).
2. Viết bài hoàn chỉnh, mạch lạc, ý tứ sâu sắc, từ vựng phong phú, chuẩn cấu trúc ngữ pháp.
3. Nếu đây là câu hỏi nối tiếp của phiên làm bài (ví dụ: sửa đổi bài trước, viết tiếp đoạn sau, giải thích câu trên, dịch, rút gọn, hoặc câu sau hỏi về phần trước): Hãy kết hợp hoàn toàn với ngữ cảnh đã trao đổi trước đó để trả lời chính xác nhất.
4. Nếu đề bài là câu hỏi trắc nghiệm hoặc bài tập cụ thể: Trả về trực tiếp đáp án chính xác.
5. Nếu đề bài có nhiều câu hỏi/nhiều phần: Làm lần lượt từng phần theo đúng thứ tự.

QUY TẮC BẮT BUỘC:
- Trực tiếp đưa ra nội dung bài viết/đáp án.
- TUYỆT ĐỐI KHÔNG thêm lời chào, mở đầu (như "Here is the essay", "Dưới đây là bài viết...") hoặc kết luận thừa thãi.
- KHÔNG dùng ký hiệu code block markdown ```.
- Xuất văn bản thuần túy để có thể gõ trực tiếp vào ô làm bài thi SEB.
"""

WRITING_PROMPT_TEXT = """
Bạn là chuyên gia giải đề thi và viết bài Writing chuyên nghiệp (IELTS, VSTEP, TOEFL, Tiếng Anh/Tiếng Việt, Văn học, Tự luận học thuật).
Đoạn văn bản sau đây được học sinh bôi đen từ màn hình đề thi:

=== ĐỀ BÀI / YÊU CẦU ===
{text}
========================

NHIỆM VỤ:
1. Phân tích yêu cầu đề bài vừa nhận được.
2. Viết bài hoàn chỉnh, mạch lạc, đúng chủ đề, từ vựng chuẩn xác và giàu liên kết.
3. Nếu đây là câu hỏi nối tiếp của phiên làm bài (ví dụ: sửa đổi bài trước, viết tiếp đoạn sau, giải thích câu trên, dịch, rút gọn, hoặc câu sau hỏi về phần trước): Hãy kết hợp hoàn toàn với ngữ cảnh đã trao đổi trước đó để trả lời chính xác nhất.
4. Nếu là dạng bài luận (Essay / Task 2 / Thư tín / Báo cáo): Viết đầy đủ Mở bài - Thân bài - Kết bài theo đúng độ dài tiêu chuẩn.
5. Nếu là câu hỏi trắc nghiệm hoặc bài tập ngắn: Trả lời đáp án ngắn gọn và chính xác nhất.

QUY TẮC BẮT BUỘC:
- Trực tiếp đưa ra nội dung bài viết/đáp án.
- TUYỆT ĐỐI KHÔNG thêm lời mở đầu hay kết thúc giao tiếp râu ria.
- KHÔNG dùng markdown code block ```.
- Xuất văn bản thuần túy để tự động gõ vào ô bài thi SEB.
"""


# ============================================================
# TỰ ĐỘNG GÕ ĐÁP ÁN BẰNG PYTHON (SendInput)
# ============================================================

def auto_type_worker():
    global typing_in_progress, stop_typing_flag

    with answer_lock:
        text_to_type = last_answer

    if not text_to_type or not text_to_type.strip():
        print()
        print(YELLOW + "⚠ Chưa có nội dung từ Gemini để gõ.")
        print(YELLOW + f"Hãy chụp ảnh ({CAPTURE_HOTKEY} -> {SEND_HOTKEY}) hoặc bôi đen đề bài rồi bấm {SELECTION_HOTKEY.upper()}.")
        return

    typing_in_progress = True
    stop_typing_flag = False

    print()
    print_box(
        "CHUẨN BỊ TỰ ĐỘNG GÕ VÀO SEB",
        [
            f"Độ dài bài viết: {len(text_to_type)} ký tự",
            "Bắt đầu gõ sau: 1.2 giây...",
            "👉 HÃY CLICK CHUỘT VÀO Ô BÀI THI SEB NGAY BÂY GIỜ!",
            f"Bấm phím '{STOP_HOTKEY.upper()}' để DỪNG GÕ bất cứ lúc nào.",
        ],
        color=CYAN,
        width=74,
    )

    # Âm báo nhẹ và thời gian 1.2s để người dùng click vào ô bài thi SEB
    try:
        import winsound
        winsound.Beep(1200, 120)
    except Exception:
        pass
    time.sleep(1.2)

    typed_count = 0
    try:
        for char in text_to_type:
            if stop_typing_flag:
                print(YELLOW + f"\n⏹ Phím dừng khẩn cấp '{STOP_HOTKEY.upper()}' đã được nhấn: Đã dừng gõ phím ({typed_count}/{len(text_to_type)} ký tự).")
                print(CYAN + f"👉 Khi cần gõ lại, bấm phím '{TYPE_HOTKEY}' để bắt đầu viết lại toàn bộ từ đầu.")
                break
            type_char_safe(char)
            typed_count += 1
            time.sleep(TYPING_DELAY)
    except Exception as e:
        print(RED + f"\n❌ Có lỗi khi gõ: {e}")
    finally:
        typing_in_progress = False
        stop_typing_flag = False

    if not stop_typing_flag and typed_count > 0:
        print()
        print(GREEN + f"✔ Đã hoàn thành tự động gõ {typed_count} ký tự vào bài thi!")
        try:
            import winsound
            winsound.Beep(1800, 150)
        except Exception:
            pass


def trigger_auto_type():
    global typing_in_progress, stop_typing_flag
    if typing_in_progress:
        return
    threading.Thread(target=auto_type_worker, daemon=True).start()


def trigger_stop_typing():
    global stop_typing_flag
    if typing_in_progress:
        stop_typing_flag = True
        print(YELLOW + f"\n⏹ Đang yêu cầu dừng gõ khẩn cấp...")


def reset_draft_session():
    global current_interaction_id, turn_count
    with interaction_lock:
        current_interaction_id = None
        turn_count = 0
    print()
    print_box(
        "ĐÃ KHỞI TẠO BẢN NHÁP MỚI (F8)",
        [
            "Đã xóa toàn bộ ngữ cảnh trao đổi của các câu hỏi trước.",
            "Lệnh tiếp theo sẽ bắt đầu một bản nháp độc lập mới hoàn toàn!",
        ],
        color=GREEN,
        width=72,
    )
    try:
        import winsound
        winsound.Beep(1600, 120)
    except Exception:
        pass


# ============================================================
# CHỤP ẢNH & GỬI LÔ ẢNH (NÚT 1 & NÚT 2)
# ============================================================

def get_next_screenshot_path():
    stamp = time.strftime("%Y%m%d_%H%M%S")
    index = 1
    while True:
        path = PICTURE_DIR / f"{stamp}_{index:03d}.jpg"
        if not path.exists():
            return path
        index += 1


def capture_image():
    """Nút 1: chụp thêm 1 ảnh và đưa vào danh sách chờ."""
    try:
        image = pyautogui.screenshot()
        path = get_next_screenshot_path()
        image.save(path, format="JPEG", quality=JPEG_QUALITY)

        with pending_lock:
            pending_images.append(path)
            count = len(pending_images)

        print()
        print_box(
            "ĐÃ CHỤP THÊM 1 ẢNH ĐỀ BÀI",
            [
                f"File: {path.name}",
                f"Đang chờ trong lô: {count} ảnh",
                f"Bấm '{CAPTURE_HOTKEY}' để chụp tiếp trang sau",
                f"Bấm '{SEND_HOTKEY}' để gửi toàn bộ {count} ảnh sang Gemini",
            ],
            color=GREEN,
        )
    except Exception as e:
        print(RED + f"❌ Không chụp được ảnh: {e}")


def send_all_images():
    """Nút 2: gửi toàn bộ ảnh của lô sang Gemini."""
    global busy, last_answer, current_interaction_id, turn_count

    with pending_lock:
        batch = list(pending_images)

    if not batch:
        print()
        print(YELLOW + f"⚠ Chưa có ảnh nào. Bấm '{CAPTURE_HOTKEY}' để chụp trước.")
        return

    try:
        print()
        print_box(
            "GỬI TOÀN BỘ ẢNH SANG GEMINI",
            [
                f"Số ảnh: {len(batch)}",
                f"Model: {CONFIG.get('model_name', MODEL)}",
                "Trạng thái: Đang phân tích đề và viết bài...",
            ],
            color=CYAN,
        )

        start = time.perf_counter()
        input_parts = []

        for index, path in enumerate(batch, start=1):
            image_bytes = path.read_bytes()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            input_parts.append({
                "type": "text",
                "text": f"Ảnh đề bài {index}: {path.name}",
            })
            input_parts.append({
                "type": "image",
                "data": image_base64,
                "mime_type": "image/jpeg",
            })

        input_parts.append({"type": "text", "text": WRITING_PROMPT_IMAGE})

        with interaction_lock:
            prev_id = current_interaction_id
            curr_turn = turn_count + 1

        extra_kwargs = {}
        if prev_id:
            extra_kwargs["previous_interaction_id"] = prev_id

        try:
            interaction = client.interactions.create(
                model=MODEL,
                input=input_parts,
                **extra_kwargs,
            )
        except Exception as api_err:
            if prev_id:
                print(YELLOW + "⚠ Không thể nối tiếp ngữ cảnh cũ trên server, đang khởi tạo bản nháp mới...")
                interaction = client.interactions.create(
                    model=MODEL,
                    input=input_parts,
                )
            else:
                raise api_err

        if hasattr(interaction, "id") and interaction.id:
            with interaction_lock:
                current_interaction_id = interaction.id
                turn_count = curr_turn

        answer = (interaction.output_text or "").strip()
        if not answer:
            raise RuntimeError("Gemini không trả về nội dung.")

        with answer_lock:
            last_answer = answer

        pyperclip.copy(answer)
        ANSWER_FILE.write_text(answer + "\n", encoding="utf-8")

        with pending_lock:
            sent_set = set(batch)
            pending_images[:] = [p for p in pending_images if p not in sent_set]
            remaining = len(pending_images)

        elapsed = time.perf_counter() - start

        threading.Thread(target=show_loading_cursor_once, args=(0.6,), daemon=True).start()

        preview = answer[:140] + "..." if len(answer) > 140 else answer
        lines_preview = preview.splitlines()[:3]

        session_status = f"Bản nháp lượt #{curr_turn}: " + ("Đã kết nối câu trước" if prev_id else "Bắt đầu bản nháp mới")

        print()
        print_box(
            "GEMINI ĐÃ HOÀN THÀNH BÀI VIẾT",
            [
                session_status,
                f"Đã gửi: {len(batch)} ảnh ({elapsed:.2f}s)",
                f"Số ký tự bài viết: {len(answer)}",
                "Nội dung xem trước:",
            ] + [f"  > {line}" for line in lines_preview] + [
                "",
                f"👉 Bấm phím '{TYPE_HOTKEY}' để TỰ ĐỘNG GÕ vào SEB (chống chặn paste)",
                f"👉 Bấm phím '{STOP_HOTKEY.upper()}' nếu muốn DỪNG GÕ phím",
                "👉 Phím F8: Bắt đầu bản nháp mới (xóa nhớ câu trước)",
                "👉 Hoặc bấm Ctrl + V để dán thủ công nếu ứng dụng cho phép",
            ],
            color=GREEN,
            width=76,
        )

    except urllib.error.URLError as e:
        print()
        print(RED + f"❌ Lỗi kết nối mạng: Không thể kết nối tới máy chủ Google Gemini ({e}).")
    except Exception as e:
        err_msg = str(e)
        print()
        if "API_KEY" in err_msg or "API key" in err_msg:
            print(RED + "❌ Lỗi: API Key Gemini không hợp lệ. Vui lòng kiểm tra file C:\\duc\\key.txt.")
        elif "quota" in err_msg.lower() or "429" in err_msg:
            print(RED + "❌ Lỗi: Model đã hết lượt request trong ngày (Quota Exceeded). Hãy đổi model khác.")
        else:
            print(RED + f"❌ Gửi Gemini thất bại: {e}")
    finally:
        with busy_lock:
            busy = False


def trigger_send():
    global busy
    with busy_lock:
        if busy:
            print(YELLOW + "⏳ Gemini đang xử lý, vui lòng chờ trong giây lát...")
            return
        busy = True
    threading.Thread(target=send_all_images, daemon=True).start()


# ============================================================
# TÍNH NĂNG BÔI ĐEN VĂN BẢN VÀ BẤM SELECTION_HOTKEY
# ============================================================

def process_selected_text():
    """Hàm xử lý khi bấm SELECTION_HOTKEY: Tự copy text bôi đen -> gửi Gemini."""
    global busy, last_answer, current_interaction_id, turn_count

    with busy_lock:
        if busy:
            print(YELLOW + "⏳ Gemini đang xử lý yêu cầu trước, vui lòng chờ...")
            return
        busy = True

    try:
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        try:
            pyperclip.copy("")
        except Exception:
            pass

        time.sleep(0.08)
        pyautogui.hotkey("ctrl", "c")

        selected_text = ""
        deadline = time.time() + 0.4
        while time.time() < deadline:
            try:
                clip_val = pyperclip.paste()
                if clip_val and clip_val.strip():
                    selected_text = clip_val.strip()
                    break
            except Exception:
                pass
            time.sleep(0.04)

        if not selected_text:
            print()
            print_box(
                "CHƯA BÔI ĐEN VĂN BẢN",
                [
                    "Không thể lấy được nội dung đề bài!",
                    "Hãy dùng chuột bôi đen đoạn đề bài/câu hỏi trước,",
                    f"sau đó nhấn lại tổ hợp phím: {SELECTION_HOTKEY.upper()}",
                ],
                color=YELLOW,
                width=68,
            )
            if old_clipboard:
                pyperclip.copy(old_clipboard)
            return

        if not API_KEY or not API_KEY.strip():
            print(RED + "❌ Lỗi: Chưa cấu hình API Key. Kiểm tra file C:\\duc\\key.txt.")
            return

        print()
        preview_text = selected_text[:120] + "..." if len(selected_text) > 120 else selected_text
        print_box(
            "ĐÃ LẤY VĂN BẢN BÔI ĐEN",
            [
                f"Độ dài: {len(selected_text)} ký tự",
                f"Trích đoạn: {preview_text}",
                "Đang gửi sang Gemini để giải đề / viết bài...",
            ],
            color=CYAN,
            width=72,
        )

        start = time.perf_counter()
        prompt_content = WRITING_PROMPT_TEXT.format(text=selected_text)

        with interaction_lock:
            prev_id = current_interaction_id
            curr_turn = turn_count + 1

        extra_kwargs = {}
        if prev_id:
            extra_kwargs["previous_interaction_id"] = prev_id

        try:
            interaction = client.interactions.create(
                model=MODEL,
                input=prompt_content,
                **extra_kwargs,
            )
        except Exception as api_err:
            if prev_id:
                print(YELLOW + "⚠ Không thể nối tiếp ngữ cảnh cũ trên server, đang khởi tạo bản nháp mới...")
                interaction = client.interactions.create(
                    model=MODEL,
                    input=prompt_content,
                )
            else:
                raise api_err

        if hasattr(interaction, "id") and interaction.id:
            with interaction_lock:
                current_interaction_id = interaction.id
                turn_count = curr_turn

        answer = (interaction.output_text or "").strip()
        if not answer:
            raise RuntimeError("Gemini không trả về kết quả.")

        with answer_lock:
            last_answer = answer

        pyperclip.copy(answer)
        ANSWER_FILE.write_text(answer + "\n", encoding="utf-8")

        elapsed = time.perf_counter() - start

        threading.Thread(target=show_loading_cursor_once, args=(0.6,), daemon=True).start()

        lines_preview = answer.splitlines()[:4]
        session_status = f"Bản nháp lượt #{curr_turn}: " + ("Đã kết nối câu trước" if prev_id else "Bắt đầu bản nháp mới")

        print()
        print_box(
            "GEMINI ĐÃ HOÀN THÀNH BÀI VIẾT (TỪ VĂN BẢN)",
            [
                session_status,
                f"Thời gian: {elapsed:.2f}s | Số ký tự: {len(answer)}",
                "Trích đoạn kết quả:",
            ] + [f"  > {line}" for line in lines_preview] + [
                "",
                f"👉 Bấm phím '{TYPE_HOTKEY}' để TỰ ĐỘNG GÕ vào SEB (chống chặn paste)",
                f"👉 Bấm phím '{STOP_HOTKEY.upper()}' nếu muốn DỪNG GÕ phím",
                "👉 Phím F8: Bắt đầu bản nháp mới (xóa nhớ câu trước)",
                "👉 Hoặc bấm Ctrl + V để dán thủ công nếu ứng dụng cho phép",
            ],
            color=GREEN,
            width=76,
        )

    except urllib.error.URLError as e:
        print()
        print(RED + f"❌ Lỗi kết nối mạng: Không thể kết nối tới Google Gemini ({e}).")
    except Exception as e:
        err_msg = str(e)
        print()
        if "API_KEY" in err_msg or "API key" in err_msg:
            print(RED + "❌ Lỗi: API Key Gemini không hợp lệ hoặc đã hết hạn.")
        elif "quota" in err_msg.lower() or "429" in err_msg:
            print(RED + "❌ Lỗi: Đã hết giới hạn request Gemini trong ngày (Quota Exceeded).")
        else:
            print(RED + f"❌ Lỗi xử lý: {e}")
    finally:
        with busy_lock:
            busy = False


def trigger_selection_hotkey():
    threading.Thread(target=process_selected_text, daemon=True).start()


# ============================================================
# SẴN SÀNG HOẠT ĐỘNG
# ============================================================

screen_width, screen_height = pyautogui.size()
print()
print_box(
    "TOOL CHỤP MÀN V2 -> SEB WRITING ĐÃ SẴN SÀNG",
    [
        f"Màn hình: {screen_width} x {screen_height} | Model: {CONFIG.get('model_name', MODEL)}",
        f"1. Nút chụp thêm ảnh      : {CAPTURE_HOTKEY}",
        f"2. Nút gửi tất cả ảnh     : {SEND_HOTKEY}",
        f"3. Bôi đen đề thi và bấm  : {SELECTION_HOTKEY.upper()} (Tự copy & gửi Gemini)",
        f"4. Tự động gõ vào SEB     : Phím '{TYPE_HOTKEY}' (Chống bị chặn Ctrl+V)",
        f"5. Dừng gõ khẩn cấp       : Phím '{STOP_HOTKEY.upper()}' (Bấm lại để viết từ đầu)",
        f"6. Làm mới bản nháp       : Phím F8 (Xóa nhớ câu trước, làm đề mới)",
        f"7. Dán nhanh bằng tay     : Phím Ctrl + V (Kết quả đã sẵn ở Clipboard)",
        f"8. Thoát tool hoàn toàn   : Phím ESC",
    ],
    color=PINK,
    width=78,
)
print()
print(GREEN + "✦ Hướng dẫn sử dụng:")
print(WHITE + f"  • Chụp ảnh đề bài bằng '{CAPTURE_HOTKEY}', gửi ảnh bằng '{SEND_HOTKEY}'.")
print(WHITE + f"  • Hoặc bôi đen đề bài rồi bấm '{SELECTION_HOTKEY.upper()}'.")
print(CYAN + "  • TỰ ĐỘNG NHỚ NGỮ CẢNH: Mỗi phiên mở tool là 1 bản nháp riêng biệt,")
print(CYAN + "    các câu lệnh sau tự động nối tiếp câu trước (hỏi tiếp, yêu cầu sửa bài, dịch...).")
print(GREEN + f"  • Click chuột vào bài thi và bấm '{TYPE_HOTKEY}' để tool tự động gõ vào SEB!")
print(YELLOW + f"  • Dừng khẩn cấp khi đang gõ  : Bấm phím '{STOP_HOTKEY.upper()}'.")
print(CYAN + f"  • Sau khi dừng, bấm lại '{TYPE_HOTKEY}' để viết lại toàn bộ từ đầu.")
print(WHITE + "  • Muốn xóa ngữ cảnh cũ làm đề mới: Bấm phím F8.")
print()

keyboard.add_hotkey(CAPTURE_HOTKEY, capture_image, suppress=True)
keyboard.add_hotkey(SEND_HOTKEY, trigger_send, suppress=True)
keyboard.add_hotkey(SELECTION_HOTKEY, trigger_selection_hotkey, suppress=False)
keyboard.add_hotkey(TYPE_HOTKEY, trigger_auto_type, suppress=True)
keyboard.add_hotkey(STOP_HOTKEY, trigger_stop_typing, suppress=True)
keyboard.add_hotkey("f8", reset_draft_session, suppress=True)

keyboard.wait(EXIT_KEY)

print()
print(PINK + "✦ Đã đóng Tool Chụp Màn V2 -> SEB writing. ✦")
