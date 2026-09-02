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

CONFIG_FILE = CONFIG_DIR / "seb.json"
LEGACY_CONFIG_FILE = BASE_DIR / "tool_config.json"
KEY_FILE = BASE_DIR / "key.txt"

PICTURE_DIR = BASE_DIR / "picture"
PICTURE_DIR.mkdir(parents=True, exist_ok=True)

ANSWER_FILE = BASE_DIR / "dapan.txt"



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
    answers: List[Literal["A", "B", "C", "D"]] = Field(
        description=(
            "Danh sách tất cả đáp án đúng. "
            "Nếu câu chỉ có 1 đáp án đúng thì vẫn trả về mảng có 1 phần tử."
        )
    )

    boxes_2d: List[List[int]] = Field(
        description=(
            "Danh sách bounding box tương ứng với từng đáp án đúng. "
            "Mỗi box có dạng [ymin, xmin, ymax, xmax], tọa độ chuẩn hóa 0-1000."
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

last_click_points = []
last_answers = []

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
Đây là ảnh chụp giao diện quiz DEMO.

Trong ảnh có một câu hỏi trắc nghiệm và
các lựa chọn A, B, C, D.

Nhiệm vụ:
1. Đọc kỹ câu hỏi.
2. Đọc đầy đủ tất cả lựa chọn.
3. Giải câu hỏi.
4. Nếu câu chỉ có 1 đáp án đúng, trả về đúng 1 đáp án.
5. Nếu câu có NHIỀU đáp án đúng, phải trả về TẤT CẢ đáp án đúng.
6. Với MỖI đáp án đúng, xác định vị trí của TOÀN BỘ HÀNG chứa đáp án đó.

Trả về JSON theo dạng:
answers: ["A"] hoặc ["A", "C"] hoặc ["A", "B", "D"]
boxes_2d: [[ymin, xmin, ymax, xmax], ...]

Quy tắc:
- Số phần tử của answers và boxes_2d phải bằng nhau.
- Thứ tự answers phải khớp với thứ tự boxes_2d.
- Nếu câu có nhiều đáp án đúng, trả về theo thứ tự từ trên xuống dưới.
- Mỗi box_2d phải nằm trên hàng đáp án đúng tương ứng.
- Ưu tiên bao trọn toàn bộ hàng đáp án.
- Tọa độ chuẩn hóa từ 0 đến 1000.
- 0,0 là góc trái trên. 1000,1000 là góc phải dưới.
- Không chọn Next.
- Không chọn Previous.
- Không chọn Submit.
- Không chọn navigation.
- Không chọn số câu.
- Không chọn button khác.
"""


# ============================================================
# CHỌN TÊN ẢNH 1.JPG -> 100.JPG
#
# Luôn lấy số NHỎ NHẤT đang thiếu.
#
# Ví dụ:
# - Có 2.jpg, 3.jpg nhưng không có 1.jpg -> dùng 1.jpg
# - Có 1.jpg, 3.jpg nhưng không có 2.jpg -> dùng 2.jpg
# - Có đủ 1.jpg -> 100.jpg -> báo đầy, không ghi đè
# ============================================================

def get_next_screenshot_path():

    for number in range(1, 101):

        image_path = PICTURE_DIR / f"{number}.jpg"

        if not image_path.exists():
            return image_path

    raise RuntimeError(
        "C:\\\\duc\\\\picture đã có đủ ảnh từ 1.jpg đến 100.jpg. "
        "Hãy xóa ít nhất một ảnh; tool sẽ tự dùng lại số nhỏ nhất đang thiếu."
    )


# ============================================================
# LƯU ĐÁP ÁN THEO TỪNG ẢNH
#
# Ví dụ trong C:\duc\dapan.txt:
# 1.jpg = A
# 2.jpg = C
#
# Nếu ảnh đã có dòng trong file, cập nhật lại dòng đó.
# ============================================================

def save_answer_for_image(image_path, answer_values):

    image_name = Path(image_path).name

    stored_answers = {}

    if ANSWER_FILE.exists():
        try:
            for line in ANSWER_FILE.read_text(
                encoding="utf-8"
            ).splitlines():

                if "=" not in line:
                    continue

                name, value = line.split(
                    "=",
                    1
                )

                name = name.strip()
                value = value.strip().upper()

                if name:
                    stored_answers[name] = value

        except Exception:
            stored_answers = {}

    if isinstance(answer_values, (list, tuple)):
        answer_text = ",".join(
            str(item).strip().upper()
            for item in answer_values
            if str(item).strip()
        )
    else:
        answer_text = str(answer_values).strip().upper()

    stored_answers[image_name] = answer_text

    def image_number(name):
        try:
            return int(
                Path(name).stem
            )
        except Exception:
            return 999999

    ordered_names = sorted(
        stored_answers.keys(),
        key=image_number
    )

    content = "\n".join(
        f"{name} = {stored_answers[name]}"
        for name in ordered_names
    )

    if content:
        content += "\n"

    ANSWER_FILE.write_text(
        content,
        encoding="utf-8"
    )


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
# PARSE KẾT QUẢ GEMINI
# Hỗ trợ cả format cũ (1 đáp án) và mới (nhiều đáp án).
# ============================================================

def parse_quiz_result(output_text):
    raw = json.loads(output_text)

    if not isinstance(raw, dict):
        raise ValueError("Gemini trả về JSON không hợp lệ")

    if "answers" in raw and "boxes_2d" in raw:
        answers = raw.get("answers") or []
        boxes = raw.get("boxes_2d") or []
    elif "answer" in raw and "box_2d" in raw:
        answers = [raw.get("answer")]
        boxes = [raw.get("box_2d")]
    else:
        raise ValueError("Gemini không trả đúng keys answers/boxes_2d")

    cleaned_answers = []
    for item in answers:
        value = str(item).strip().upper()
        if value not in {"A", "B", "C", "D"}:
            raise ValueError(f"Đáp án không hợp lệ: {item}")
        cleaned_answers.append(value)

    cleaned_boxes = []
    for box in boxes:
        if not isinstance(box, list) or len(box) != 4:
            raise ValueError(f"box_2d không hợp lệ: {box}")
        cleaned_boxes.append([int(v) for v in box])

    if not cleaned_answers:
        raise ValueError("Gemini không trả về đáp án nào")

    if len(cleaned_answers) != len(cleaned_boxes):
        raise ValueError("Số lượng answers và boxes_2d không khớp")

    return cleaned_answers, cleaned_boxes


# ============================================================
# SOLVE + CLICK
# ============================================================

def solve_and_click():
    global busy, last_click_points, last_answers

    try:
        print()

        print_box(
            "BẮT ĐẦU PHÂN TÍCH",
            [
                "Đang chụp vùng màn hình và chuẩn bị gửi Gemini"
            ],
            color=YELLOW,
            width=62
        )

        start_time = time.perf_counter()

        screen_width, screen_height = pyautogui.size()

        # ====================================================
        # CHỤP 4/5 BÊN PHẢI + 4/5 PHÍA DƯỚI
        #
        # Bỏ 1/5 bên trái
        # Bỏ 1/5 phía trên
        # ====================================================

        left = screen_width // 5
        top = screen_height // 5

        crop_width = screen_width - left
        crop_height = screen_height - top

        image = pyautogui.screenshot(
            region=(
                left,
                top,
                crop_width,
                crop_height
            )
        )

        capture_time = time.perf_counter()

        # ====================================================
        # LƯU ẢNH VÀO C:\duc\picture
        #
        # Chọn số nhỏ nhất đang thiếu từ 1 -> 100.
        # File đã lưu chính là file được gửi sang Gemini.
        # ====================================================

        screenshot_path = get_next_screenshot_path()

        image.save(
            screenshot_path,
            format="JPEG",
            quality=JPEG_QUALITY
        )

        print(
            "🖼 Đã lưu ảnh:",
            screenshot_path
        )

        # Đọc CHÍNH file vừa lưu để gửi Gemini
        image_bytes = screenshot_path.read_bytes()

        image_base64 = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        process_time = time.perf_counter()

        print()

        print_box(
            "GỬI ẢNH SANG GEMINI",
            [
                f"Model : {CONFIG.get('model_name', MODEL)}",
                f"Ảnh   : {screenshot_path}",
                f"Crop  : {crop_width} x {crop_height}",
                "Trạng thái: Đang xử lý..."
            ],
            color=CYAN,
            width=62
        )

        interaction = client.interactions.create(
            model=MODEL,

            input=[
                {
                    "type": "image",
                    "data": image_base64,
                    "mime_type": "image/jpeg"
                },
                {
                    "type": "text",
                    "text": QUIZ_PROMPT
                }
            ],

            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": QuizResult.model_json_schema()
            }
        )

        api_time = time.perf_counter()

        answers, boxes = parse_quiz_result(
            interaction.output_text
        )

        # Gemini đã trả đáp án -> báo hiệu bằng con trỏ loading 1 lần.
        show_loading_cursor_once(
            duration=0.6
        )

        # Lưu đáp án đúng theo chính file ảnh vừa gửi Gemini.
        save_answer_for_image(
            screenshot_path,
            answers
        )

        LEFT_OF_TEXT_PADDING = 10  # đơn vị normalized 0-1000
        click_data = []

        for answer, box in zip(answers, boxes):
            ymin = max(0, min(1000, box[0]))
            xmin = max(0, min(1000, box[1]))
            ymax = max(0, min(1000, box[2]))

            center_y_norm = (ymin + ymax) / 2
            click_x_norm = max(0, xmin - LEFT_OF_TEXT_PADDING)

            crop_x = (
                click_x_norm
                / 1000
                * crop_width
            )

            crop_y = (
                center_y_norm
                / 1000
                * crop_height
            )

            screen_x = int(left + crop_x) + 30
            screen_y = int(top + crop_y)

            click_data.append(
                {
                    "answer": answer,
                    "x": screen_x,
                    "y": screen_y,
                }
            )

        # Sắp xếp từ trên xuống dưới để click đúng thứ tự.
        click_data.sort(key=lambda item: (item["y"], item["x"]))

        with coordinate_lock:
            last_click_points = [
                (item["x"], item["y"])
                for item in click_data
            ]
            last_answers = [
                item["answer"]
                for item in click_data
            ]

        display_lines = [
            f"Đáp án  : {','.join(last_answers)}",
            f"Ảnh     : {screenshot_path.name}",
            f"Số click: {len(click_data)}",
            f"Đã ghi  : {ANSWER_FILE}",
            "Đã lưu tất cả tọa độ",
            f"Bấm {CLICK_HOTKEY} để click"
        ]

        for idx, item in enumerate(click_data, start=1):
            display_lines.append(
                f"{idx}. {item['answer']} -> ({item['x']}, {item['y']})"
            )

        print()

        print_box(
            "GEMINI ĐÃ XỬ LÝ XONG",
            display_lines,
            color=GREEN,
            width=72
        )

        finish_time = time.perf_counter()

        print(
            "⏱ Gemini:",
            f"{api_time - process_time:.2f}s"
        )

        print(
            "⏱ Tổng:",
            f"{finish_time - start_time:.2f}s"
        )

    except pyautogui.FailSafeException:
        print()
        print("🛑 Đã dừng bằng FAILSAFE.")

    except Exception as e:
        print()
        print("❌ Có lỗi:")
        print(e)

    finally:
        with busy_lock:
            busy = False


# ============================================================
# CLICK TỌA ĐỘ ĐÃ LƯU
#
# Bấm ' để click trực tiếp vào tọa độ gần nhất.
# Không moveTo trước.
# ============================================================

def click_saved_coordinate():

    with coordinate_lock:
        points = list(last_click_points)
        answers = list(last_answers)

    if not points:
        print()
        print("⚠️ Chưa có tọa độ.")
        print(
            f"Hãy bấm {ANALYZE_HOTKEY} trước để Gemini xác định vị trí."
        )
        return

    try:
        click_lines = [
            f"Số click : {len(points)}",
            "Kiểu      : Di chuột + click từng tọa độ",
        ]

        for idx, (point, answer) in enumerate(zip(points, answers), start=1):
            x, y = point

            pyautogui.moveTo(
                x,
                y,
                duration=MOVE_DURATION
            )

            time.sleep(CLICK_DELAY)
            pyautogui.click()
            time.sleep(CLICK_DELAY)

            click_lines.append(
                f"{idx}. {answer} -> ({x}, {y})"
            )

        print()

        print_box(
            "ĐÃ CLICK",
            click_lines,
            color=PINK,
            width=72
        )

    except pyautogui.FailSafeException:
        print()
        print("🛑 Đã dừng bằng FAILSAFE.")

    except Exception as e:
        print()
        print("❌ Không click được:")
        print(e)


# ============================================================
# HOTKEY
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
    "TOOL ĐÃ SẴN SÀNG",
    [
        f"Thư mục ảnh  : {PICTURE_DIR}",
        f"File đáp án  : {ANSWER_FILE}",
        f"Model        : {CONFIG.get('model_name', MODEL)}",
        f"Giới hạn     : {CONFIG.get('daily_limit', '?')} request/ngày",
        f"Phân tích : {ANALYZE_HOTKEY}",
        f"Click     : {CLICK_HOTKEY}",
        "Thoát     : ESC"
    ],
    color=PINK,
    width=68
)

print()
print(GREEN + "Tool đã sẵn sàng <3")
print()


keyboard.add_hotkey(
    ANALYZE_HOTKEY,
    trigger,
    suppress=True
)

keyboard.add_hotkey(
    CLICK_HOTKEY,
    click_saved_coordinate,
    suppress=True
)

keyboard.wait(EXIT_KEY)

print()
print(PINK + "✦ Đã đóng tool. Học vui nhé <3 ✦")
