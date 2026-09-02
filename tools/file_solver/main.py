# ============================================================
# ĐỨC DẠY BẠN HỌC NHÉ<3
# Sang Ngành AI Học Với Đức Đi<3
# ============================================================

import ctypes
from ctypes import wintypes
import os
import io
import json
import time
import base64
import threading

from pathlib import Path
from typing import Literal, List

import keyboard
import pyautogui
from colorama import Fore, Style, init

from google import genai
from pydantic import BaseModel, Field




# ============================================================
# MÀU TERMINAL
# ============================================================

init(autoreset=True)

PINK = Fore.MAGENTA + Style.BRIGHT
CYAN = Fore.CYAN + Style.BRIGHT
GREEN = Fore.GREEN + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
BLUE = Fore.BLUE + Style.BRIGHT
WHITE = Fore.WHITE + Style.BRIGHT
RESET = Style.RESET_ALL


# ============================================================
# DUC TOOL BANNER - dùng cho mọi tool hiện tại và tool mới
# ============================================================

DUC_TOOL_BANNER = r"""╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║ ██████╗  ██╗   ██╗  ██████╗    ████████╗  ██████╗   ██████╗  ██╗      ║
║ ██╔══██╗ ██║   ██║ ██╔════╝    ╚══██╔══╝ ██╔═══██╗ ██╔═══██╗ ██║      ║
║ ██║  ██║ ██║   ██║ ██║            ██║    ██║   ██║ ██║   ██║ ██║      ║
║ ██║  ██║ ██║   ██║ ██║            ██║    ██║   ██║ ██║   ██║ ██║      ║
║ ██████╔╝ ╚██████╔╝ ╚██████╗       ██║    ╚██████╔╝ ╚██████╔╝ ███████╗ ║
║ ╚═════╝   ╚═════╝   ╚═════╝       ╚═╝     ╚═════╝   ╚═════╝  ╚══════╝ ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝"""


def print_duc_tool_banner():
    print(PINK + DUC_TOOL_BANNER + RESET)


# ============================================================
# WINDOWS UTF-8
# ============================================================

if os.name == "nt":
    os.system("chcp 65001 > nul")
    try:
        os.system("title Duc Day Ban Hoc Nhe - Sang Ngành AI Học Với Đức Đi<3")
    except Exception:
        pass


# ============================================================
# DPI WINDOWS
# ============================================================

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ============================================================
# THƯ MỤC LƯU TOÀN BỘ DỮ LIỆU
# ============================================================

BASE_DIR = Path(r"C:\duc")
BASE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = BASE_DIR / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "file_solver.json"
LEGACY_CONFIG_FILE = BASE_DIR / "tool_config.json"
KEY_FILE = BASE_DIR / "key.txt"

# Nguồn dữ liệu cần gửi lên Gemini.
# Hỗ trợ:
#   1) C:\duc\file là một FILE trực tiếp
#   2) C:\duc\file là một THƯ MỤC chứa file
#      -> tool sẽ lấy file mới nhất trong thư mục đó
FILE_SOURCE = BASE_DIR / "file"



# ============================================================
# MODEL
# ============================================================

MODEL_MAP = {
    "1": {
        "name": "Gemini 3.5 Flash-Lite",
        "model": "gemini-3.5-flash-lite",
        "daily_limit": 500
    },
    "2": {
        "name": "Gemini 3.5 Flash",
        "model": "gemini-3.5-flash",
        "daily_limit": 20
    },
    "3": {
        "name": "Gemini 3.6 Flash",
        "model": "gemini-3.6-flash",
        "daily_limit": 20
    },
    "4": {
        "name": "Gemini 3.7 Flash",
        "model": "gemini-3.7-flash",
        "daily_limit": 20
    }
}


# ============================================================
# CẤU HÌNH TOOL
# ============================================================

HOTKEY = "/"
CLICK_HOTKEY = "'"
EXIT_KEY = "esc"

DO_CLICK = False
MOVE_DURATION = 0.15
CLICK_DELAY = 0.05
JPEG_QUALITY = 85

# Click ở phía đầu ô bên trái theo trục X
CLICK_X_RATIO = 0.03


# ============================================================
# PYAutoGUI
# ============================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


# ============================================================
# FORMAT GEMINI TRẢ VỀ
# ============================================================

class QuizResult(BaseModel):
    answer: Literal["A", "B", "C", "D"]

    box_2d: List[int] = Field(
        description=(
            "Bounding box của hàng chứa đáp án đúng "
            "theo [ymin, xmin, ymax, xmax], "
            "tọa độ chuẩn hóa 0-1000."
        )
    )


# ============================================================
# TERMINAL + KHUNG
# ============================================================

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_box(title, lines=None, color=PINK, width=62, indent=2):
    """
    In khung Unicode cố định.
    Không đưa emoji vào bên trong để hạn chế lệch khung trên CMD.
    """
    if lines is None:
        lines = []

    title = str(title)
    lines = [str(line) for line in lines]

    # Nếu nội dung dài, tự tăng chiều rộng khung.
    longest = max(
        [len(title)] + [len(line) for line in lines] + [0]
    )

    box_width = max(width, longest + 4)

    print(color + "╔" + "═" * box_width + "╗")
    print(
        color + "║" +
        WHITE + title.center(box_width) +
        color + "║"
    )

    if lines:
        print(color + "╠" + "═" * box_width + "╣")

        for line in lines:
            print(
                color + "║" +
                WHITE + ((" " * indent) + line).ljust(box_width) +
                color + "║"
            )

    print(color + "╚" + "═" * box_width + "╝")


def show_banner():
    clear()
    print()
    print_duc_tool_banner()
    print()


# ============================================================
# CONFIG
# ============================================================

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=4)


def load_config():
    # Ưu tiên config riêng của tool.
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return None

    # Tự migrate config cũ C:\duc\tool_config.json nếu có.
    if LEGACY_CONFIG_FILE.exists():
        try:
            with open(LEGACY_CONFIG_FILE, "r", encoding="utf-8") as file:
                legacy = json.load(file)

            if isinstance(legacy, dict):
                save_config(legacy)
                return legacy
        except Exception:
            pass

    return None


# ============================================================
# API KEY
# ============================================================

def save_api_key(api_key):
    # Dùng ngay trong phiên chạy hiện tại
    os.environ["GEMINI_API_KEY"] = api_key

    # Lưu API key vào C:\duc\key.txt
    # Lưu ý: file này chứa key dạng plain text.
    KEY_FILE.write_text(
        api_key,
        encoding="utf-8"
    )


def load_api_key():
    # Ưu tiên đọc từ C:\duc\key.txt
    if KEY_FILE.exists():
        try:
            api_key = KEY_FILE.read_text(
                encoding="utf-8"
            ).strip()

            if api_key:
                os.environ["GEMINI_API_KEY"] = api_key
                return api_key

        except Exception:
            pass

    return None


def validate_api(api_key):
    print()
    print(CYAN + "⟳ Đang xác nhận API...")

    try:
        test_client = genai.Client(api_key=api_key)

        response = test_client.interactions.create(
            model="gemini-3.5-flash-lite",
            input="Chỉ trả lời: OK"
        )

        _ = response.output_text
        return True

    except Exception as e:
        print()
        print("❌ API không hợp lệ hoặc hiện không sử dụng được.")
        print("Lỗi:")
        print(e)
        return False


def input_new_api():
    while True:
        print()
        print(CYAN + "⌨ Bạn có thể Ctrl+V hoặc chuột phải để dán API.")
        print("📁 API sẽ được lưu tại C:\\duc\\key.txt")
        print(YELLOW + "⚠ Vào https://aistudio.google.com/api-keys")

        # QUAN TRỌNG:
        # Dùng input() thay vì getpass để paste bình thường.
        api_key = input(WHITE + "🔑 Nhập API : " + RESET).strip()

        # Phòng trường hợp người dùng copy cả dấu nháy
        api_key = api_key.strip('"').strip("'").strip()

        if not api_key:
            print("❌ API không được để trống.")
            continue

        print()
        print(
            "✅ Đã nhận API:",
            api_key[:6] + "..." if len(api_key) > 6 else "***"
        )

        if validate_api(api_key):
            save_api_key(api_key)

            print()
            print(GREEN + "✔ Đã xác nhận API thành công ♥")
            return api_key

        print()
        print("Vui lòng nhập lại API.")


def get_old_api():
    api_key = load_api_key()

    if not api_key:
        print()
        print("❌ Không tìm thấy API cũ tại C:\\duc\\key.txt.")
        print("Vui lòng nhập API mới.")
        return input_new_api()

    if validate_api(api_key):
        print()
        print(GREEN + "✔ Đã xác nhận API thành công ♥")
        return api_key

    print()
    print("API cũ không sử dụng được.")
    return input_new_api()


# ============================================================
# MODEL
# ============================================================

def choose_model():
    print()
    print(CYAN + "✦ Vui lòng chọn độ thông minh của Gemini 1,2,3,4 :")
    print()
    print(GREEN + " [1] ⚡ Gemini 3.5 Flash-Lite - Nhanh nhất              | 500 request/ngày")
    print(CYAN + " [2] ✦ Gemini 3.5 Flash      - Nhanh                   | 20 request/ngày")
    print(YELLOW + " [3] ★ Gemini 3.6 Flash      - Thông minh + đọc ảnh tốt | 20 request/ngày")
    print(PINK + " [4] ✪ Gemini 3.7 Flash      - Mạnh nhất               | 20 request/ngày")
    print()

    while True:
        choice = input(WHITE + "➤ Lựa chọn : " + RESET).strip()

        if choice in MODEL_MAP:
            selected = MODEL_MAP[choice]

            print()
            print("✅ Đã chọn:", selected["name"])

            return {
                "level": choice,
                "model": selected["model"],
                "model_name": selected["name"],
                "daily_limit": selected["daily_limit"]
            }

        print("❌ Vui lòng chọn 1, 2, 3 hoặc 4.")


# ============================================================
# CHỌN PHÍM TẮT
# ============================================================

def choose_hotkeys():

    print()
    print(CYAN + "✦ Tùy chỉnh phím tắt:")

    analyze_hotkey = input(
        WHITE + "Phím Phân Tích / Gửi Gemini [mặc định /] : " + RESET
    ).strip()

    if not analyze_hotkey:
        analyze_hotkey = "/"

    click_hotkey = input(
        WHITE + "Phím Click [mặc định '] : " + RESET
    ).strip()

    if not click_hotkey:
        click_hotkey = "'"

    if analyze_hotkey == click_hotkey:
        print(YELLOW + "⚠ Hai phím không được giống nhau.")
        print(YELLOW + "Đặt phím Click về mặc định: '")
        click_hotkey = "'"

    print()
    print(GREEN + f"✔ Phím Phân Tích/Gửi Gemini : {analyze_hotkey}")
    print(GREEN + f"✔ Phím Click                : {click_hotkey}")

    return analyze_hotkey, click_hotkey


# ============================================================
# SETUP
# ============================================================

def create_new_config():
    api_key = input_new_api()
    model_config = choose_model()
    analyze_hotkey, click_hotkey = choose_hotkeys()

    config = {
        "model": model_config["model"],
        "model_name": model_config["model_name"],
        "level": model_config["level"],
        "daily_limit": model_config["daily_limit"],
        "hotkey": analyze_hotkey,
        "click_hotkey": click_hotkey,
        "crop_left_ratio": 0.20,
        "crop_top_ratio": 0.20,
        "click_x_ratio": 0.03
    }

    save_config(config)
    return api_key, config


def setup():
    show_banner()
    old_config = load_config()

    print(CYAN + "✦ SETUP TOOL - chọn cấu hình mới hay dùng cấu hình đã lưu Y/N :")
    print(GREEN + "  [Y] SETUP / Cấu hình mới" + RESET + "   " + YELLOW + "[N] Dùng cấu hình đã lưu")
    while True:
        option = input(WHITE + "➤ Lựa chọn Y/N : " + RESET).strip().upper()

        if option == "Y":
            return create_new_config()

        if option == "N":
            if not old_config:
                print()
                print("❌ Chưa có cấu hình cũ.")
                print("Chuyển sang tạo cấu hình mới.")
                return create_new_config()

            api_key = get_old_api()

            print()
            print("✅ Đang dùng cấu hình cũ:")
            print(
                "Model:",
                old_config.get(
                    "model_name",
                    old_config.get("model", "Unknown")
                )
            )

            return api_key, old_config

        print("❌ Chỉ nhập Y hoặc N.")


# ============================================================
# KHỞI TẠO
# ============================================================

API_KEY, CONFIG = setup()

client = genai.Client(api_key=API_KEY)

MODEL = CONFIG.get(
    "model",
    "gemini-3.5-flash-lite"
)

ANALYZE_HOTKEY = CONFIG.get(
    "hotkey",
    "/"
)

CLICK_HOTKEY = CONFIG.get(
    "click_hotkey",
    "'"
)




# ============================================================
# MÀN HÌNH
# ============================================================

SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

print()

print_box(
    "KÍCH THƯỚC MÀN HÌNH",
    [
        f"Width  : {SCREEN_WIDTH}",
        f"Height : {SCREEN_HEIGHT}",
        f"Size   : {SCREEN_WIDTH} x {SCREEN_HEIGHT}"
    ],
    color=CYAN,
    width=62,
    indent=1
)




CLICK_X_RATIO = 0.03


# ============================================================
# TỌA ĐỘ ĐÃ XÁC ĐỊNH GẦN NHẤT
# ============================================================

last_screen_x = None
last_screen_y = None
last_answer = None

coordinate_lock = threading.Lock()


# ============================================================
# BUSY LOCK
# ============================================================

busy = False
busy_lock = threading.Lock()


# ============================================================
# PROMPT
# ============================================================

QUIZ_PROMPT = """
Đọc kỹ TOÀN BỘ nội dung đề bài được gửi kèm.
Dữ liệu đầu vào có thể gồm một hoặc nhiều ảnh chụp màn hình hoặc một file đề bài.

NHIỆM VỤ:
- Giải TẤT CẢ các câu hỏi/bài tập nhìn thấy trong dữ liệu được gửi.
- Không bỏ sót câu nào.
- Giữ đúng thứ tự câu như trong đề.
- Nếu cùng một câu xuất hiện lặp lại nhiều lần, chỉ trả đáp án cho câu đó một lần.

NẾU LÀ CÂU HỎI TRẮC NGHIỆM:
- Chỉ trả về số câu + chữ cái đáp án đúng.
- Nếu một câu có nhiều đáp án đúng, ghi đủ các chữ cái đúng liền nhau.
- Ví dụ: 1A 2C 3BD 4ACD
- Không giải thích đáp án trắc nghiệm.

NẾU LÀ SQL HOẶC BÀI TỰ LUẬN/CODE:
- Trả lời đầy đủ theo từng câu.
- Mỗi câu bắt đầu bằng đúng số/thứ tự của câu trong đề.
- Nếu là SQL, viết câu lệnh SQL hoàn chỉnh, chạy được.
- Giữ đúng tên bảng và tên cột trong đề.
- Dùng đúng hệ quản trị SQL mà đề yêu cầu.
- Nếu là SQL Server và có chuỗi Unicode tiếng Việt, dùng N'...'.

YÊU CẦU CHUNG:
- Trả lời trực tiếp đáp án.
- Không viết lời mở đầu hoặc kết luận.
- Không dùng Markdown code fence ```.
- Không thêm nội dung không cần thiết.
- Toàn bộ phản hồi sẽ được copy nguyên văn vào clipboard.
"""


# ============================================================
# TÌM FILE CẦN GỬI
# ============================================================

def resolve_input_file():
    r"""
    Hỗ trợ 3 trường hợp:

    1) C:\duc\file là một file trực tiếp.
    2) C:\duc\file là một thư mục:
       lấy file mới nhất bên trong.
    3) Nếu C:\duc\file chưa tồn tại nhưng có file như
       C:\duc\file.pdf / file.docx / file.txt...
       thì lấy file file.* mới nhất.
    """

    if FILE_SOURCE.is_file():
        return FILE_SOURCE

    if FILE_SOURCE.is_dir():
        candidates = [
            p for p in FILE_SOURCE.iterdir()
            if p.is_file()
        ]

        if not candidates:
            raise RuntimeError(
                "Thư mục C:\\duc\\file đang trống. "
                "Hãy đặt file đề bài vào đó."
            )

        return max(
            candidates,
            key=lambda p: p.stat().st_mtime
        )

    # Hỗ trợ trường hợp người dùng đặt:
    # C:\duc\file.pdf, C:\duc\file.docx, ...
    candidates = [
        p for p in BASE_DIR.glob("file.*")
        if p.is_file()
    ]

    if candidates:
        return max(
            candidates,
            key=lambda p: p.stat().st_mtime
        )

    raise RuntimeError(
        "Không tìm thấy file tại C:\\duc\\file.\n"
        "Bạn có thể:\n"
        "- đặt một file trực tiếp tên C:\\duc\\file\n"
        "- hoặc tạo thư mục C:\\duc\\file rồi bỏ đề vào trong\n"
        "- hoặc dùng C:\\duc\\file.pdf / file.docx / file.txt ..."
    )


def wait_until_file_ready(uploaded_file):
    """
    Một số loại file cần Gemini xử lý trước khi sử dụng.
    Nếu SDK trả state thì chờ tới ACTIVE.
    """

    current = uploaded_file

    for _ in range(120):
        state = getattr(
            current,
            "state",
            None
        )

        if state is None:
            return current

        state_name = getattr(
            state,
            "name",
            str(state)
        )

        state_name = str(
            state_name
        ).upper()

        if state_name == "ACTIVE":
            return current

        if state_name in {
            "FAILED",
            "ERROR"
        }:
            raise RuntimeError(
                f"Gemini xử lý file thất bại: {state_name}"
            )

        time.sleep(0.5)

        current = client.files.get(
            name=current.name
        )

    raise RuntimeError(
        "Gemini xử lý file quá lâu hoặc chưa chuyển sang ACTIVE."
    )


def get_interaction_file_type(mime_type):
    """
    interactions.create phân biệt image/audio/video/document.
    File PDF, TXT, DOC... dùng document.
    """

    mime = (
        mime_type
        or "application/octet-stream"
    ).lower()

    if mime.startswith("image/"):
        return "image"

    if mime.startswith("audio/"):
        return "audio"

    if mime.startswith("video/"):
        return "video"

    return "document"


# ============================================================
# HIỆU ỨNG CON TRỎ LOADING KHI GEMINI TRẢ ĐÁP ÁN
# ============================================================

def show_loading_cursor_once(duration=0.6):
    """
    Windows: đổi con trỏ mặc định thành biểu tượng WAIT trong chốc lát,
    sau đó khôi phục toàn bộ con trỏ hệ thống.
    """

    if os.name != "nt":
        return

    try:
        user32 = ctypes.windll.user32

        # IDC_WAIT = 32514
        # OCR_NORMAL = 32512
        IDC_WAIT = 32514
        OCR_NORMAL = 32512

        # SPI_SETCURSORS = 0x0057
        SPI_SETCURSORS = 0x0057

        wait_cursor = user32.LoadCursorW(
            None,
            IDC_WAIT
        )

        if not wait_cursor:
            return

        # Copy cursor vì SetSystemCursor sẽ sở hữu/destroy handle.
        copied_cursor = user32.CopyImage(
            wait_cursor,
            2,      # IMAGE_CURSOR
            0,
            0,
            0
        )

        if not copied_cursor:
            return

        user32.SetSystemCursor(
            copied_cursor,
            OCR_NORMAL
        )

        time.sleep(duration)

        # Khôi phục cursor mặc định theo Windows theme.
        user32.SystemParametersInfoW(
            SPI_SETCURSORS,
            0,
            None,
            0
        )

    except Exception:
        # Không để hiệu ứng cursor làm hỏng luồng chính.
        pass


# ============================================================
# COPY TOÀN BỘ PHẢN HỒI GEMINI VÀO CLIPBOARD
# Không cần cài thêm pyperclip.
# ============================================================

def copy_text_to_clipboard(text):
    if os.name != "nt":
        raise RuntimeError("Chức năng clipboard hiện được thiết kế cho Windows.")

    text = "" if text is None else str(text)

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    kernel32.GlobalAlloc.argtypes = [
        ctypes.c_uint,
        ctypes.c_size_t
    ]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p

    kernel32.GlobalLock.argtypes = [
        ctypes.c_void_p
    ]
    kernel32.GlobalLock.restype = ctypes.c_void_p

    kernel32.GlobalUnlock.argtypes = [
        ctypes.c_void_p
    ]

    kernel32.GlobalFree.argtypes = [
        ctypes.c_void_p
    ]

    user32.SetClipboardData.argtypes = [
        ctypes.c_uint,
        ctypes.c_void_p
    ]
    user32.SetClipboardData.restype = ctypes.c_void_p

    data = (text + "\0").encode("utf-16-le")

    h_global = kernel32.GlobalAlloc(
        GMEM_MOVEABLE,
        len(data)
    )

    if not h_global:
        raise RuntimeError("Không cấp phát được bộ nhớ clipboard.")

    locked = kernel32.GlobalLock(
        h_global
    )

    if not locked:
        kernel32.GlobalFree(h_global)
        raise RuntimeError("Không khóa được bộ nhớ clipboard.")

    ctypes.memmove(
        locked,
        data,
        len(data)
    )

    kernel32.GlobalUnlock(
        h_global
    )

    opened = False

    # Clipboard đôi khi đang bị ứng dụng khác giữ trong chốc lát.
    for _ in range(10):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.03)

    if not opened:
        kernel32.GlobalFree(h_global)
        raise RuntimeError("Không mở được clipboard.")

    try:
        user32.EmptyClipboard()

        result = user32.SetClipboardData(
            CF_UNICODETEXT,
            h_global
        )

        if not result:
            kernel32.GlobalFree(h_global)
            raise RuntimeError("Không ghi được dữ liệu vào clipboard.")

        # Khi SetClipboardData thành công, Windows sở hữu h_global.
        h_global = None

    finally:
        user32.CloseClipboard()


# ============================================================
# SOLVE + CLICK
# ============================================================

def solve_and_click():
    global busy

    uploaded_file = None

    try:
        start_time = time.perf_counter()

        input_file = resolve_input_file()

        print()

        print_box(
            "ĐANG GỬI FILE LÊN GEMINI",
            [
                f"File       : {input_file.name}",
                f"Đường dẫn  : {input_file}",
                "Yêu cầu    : Giải tất cả các câu trong file",
                "Clipboard  : Copy nguyên văn đáp án"
            ],
            color=CYAN,
            width=72
        )

        upload_start = time.perf_counter()

        # Upload file qua Gemini Files API.
        uploaded_file = client.files.upload(
            file=str(input_file)
        )

        uploaded_file = wait_until_file_ready(
            uploaded_file
        )

        upload_end = time.perf_counter()

        mime_type = getattr(
            uploaded_file,
            "mime_type",
            None
        )

        file_uri = getattr(
            uploaded_file,
            "uri",
            None
        )

        if not file_uri:
            raise RuntimeError(
                "Gemini đã upload file nhưng không trả về file URI."
            )

        input_type = get_interaction_file_type(
            mime_type
        )

        api_start = time.perf_counter()

        interaction = client.interactions.create(
            model=MODEL,
            input=[
                {
                    "type": "text",
                    "text": QUIZ_PROMPT
                },
                {
                    "type": input_type,
                    "uri": file_uri,
                    "mime_type": mime_type
                }
            ]
        )

        api_end = time.perf_counter()

        full_response = interaction.output_text

        if full_response is None:
            full_response = ""

        full_response = str(
            full_response
        ).strip()

        if not full_response:
            raise RuntimeError(
                "Gemini không trả về nội dung đáp án."
            )

        # Copy NGUYÊN VĂN toàn bộ câu trả lời vào clipboard.
        copy_text_to_clipboard(
            full_response
        )

        # Hiệu ứng con trỏ loading 1 lần khi đã có đáp án.
        show_loading_cursor_once(
            duration=0.6
        )

        finish_time = time.perf_counter()

        print()

        print_box(
            "ĐÃ GIẢI TẤT CẢ CÁC CÂU",
            [
                f"File       : {input_file.name}",
                f"Clipboard  : Đã copy {len(full_response)} ký tự",
                "Nội dung    : Tất cả câu hỏi/bài tập trong file",
                "Ctrl+V      : Dán đáp án"
            ],
            color=GREEN,
            width=72
        )

        print(
            "⏱ Upload:",
            f"{upload_end - upload_start:.2f}s"
        )

        print(
            "⏱ Gemini:",
            f"{api_end - api_start:.2f}s"
        )

        print(
            "⏱ Tổng:",
            f"{finish_time - start_time:.2f}s"
        )

    except Exception as e:
        print()
        print("❌ Có lỗi:")
        print(e)

    finally:
        # Xóa file tạm trên Gemini nếu có thể.
        # Nếu xóa lỗi cũng không ảnh hưởng kết quả chính.
        try:
            if uploaded_file is not None:
                uploaded_name = getattr(
                    uploaded_file,
                    "name",
                    None
                )

                if uploaded_name:
                    client.files.delete(
                        name=uploaded_name
                    )
        except Exception:
            pass

        with busy_lock:
            busy = False


# ============================================================
# HOTKEY GỬI FILE
# ============================================================

def trigger():
    global busy

    with busy_lock:
        if busy:
            print("⏳ Gemini đang xử lý...")
            return

        busy = True

    threading.Thread(
        target=solve_and_click,
        daemon=True
    ).start()


# ============================================================
# READY
# ============================================================

print()

print_box(
    "TOOL GEMINI - FILE -> GIẢI TẤT CẢ -> CLIPBOARD",
    [
        f"Nguồn file  : {FILE_SOURCE}",
        f"Model       : {CONFIG.get('model_name', MODEL)}",
        f"Phím gửi    : {ANALYZE_HOTKEY}",
        "Gemini      : Giải tất cả các câu trong file",
        "Clipboard   : Copy nguyên văn đáp án",
        "Thoát       : ESC"
    ],
    color=PINK,
    width=76
)

print()
print(GREEN + "Tool đã sẵn sàng <3")
print()


keyboard.add_hotkey(
    ANALYZE_HOTKEY,
    trigger,
    suppress=True
)

keyboard.wait(EXIT_KEY)

print()
print(PINK + "✦ Đã đóng tool. Học vui nhé <3 ✦")
