# ============================================================
# ĐỨC DẠY BẠN HỌC NHÉ<3
# Tool 3: Chụp nhiều ảnh -> gửi tất cả -> đáp án Clipboard
# ============================================================

import ctypes
import os
import json
import time
import base64
import threading
from pathlib import Path

import keyboard
import pyautogui
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
        os.system("title Tool Chup Man - Dap An Ve Clipboard")
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
CONFIG_FILE = CONFIG_DIR / "screenshot_clipboard.json"
KEY_FILE = BASE_DIR / "key.txt"
PICTURE_DIR = BASE_DIR / "picture" / "screenshot_clipboard"
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
EXIT_KEY = "esc"
JPEG_QUALITY = 88

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


# ============================================================
# HIỂN THỊ
# ============================================================

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_box(title, lines=None, color=PINK, width=66, indent=2):
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
        "TOOL CHỤP MÀN -> ĐÁP ÁN VỀ CLIPBOARD",
        [
            "Nút 1: Chụp thêm ảnh (bấm bao nhiêu lần cũng được)",
            "Nút 2: Gửi toàn bộ ảnh đang chờ sang Gemini",
        ],
        color=PINK,
        width=72,
    )
    print()


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
    print(CYAN + "⟳ Đang xác nhận API...")
    try:
        test_client = genai.Client(api_key=api_key)
        response = test_client.interactions.create(
            model="gemini-3.5-flash-lite",
            input="Chỉ trả lời: OK",
        )
        _ = response.output_text
        return True
    except Exception as e:
        print(RED + "❌ API không hợp lệ hoặc hiện không sử dụng được.")
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
            print(GREEN + "✔ Đã xác nhận API thành công.")
            return api_key


def get_api():
    old = load_api_key()
    if old and validate_api(old):
        print(GREEN + "✔ Đang dùng API đã lưu.")
        return old
    return input_new_api()


def choose_model():
    print()
    print(CYAN + "✦ Chọn model Gemini 1, 2, 3, 4:")
    for key, item in MODEL_MAP.items():
        print(f" [{key}] {item['name']} | {item['daily_limit']} request/ngày")
    while True:
        choice = input(WHITE + "➤ Lựa chọn: " + RESET).strip()
        if choice in MODEL_MAP:
            item = MODEL_MAP[choice]
            return {
                "level": choice,
                "model": item["model"],
                "model_name": item["name"],
                "daily_limit": item["daily_limit"],
            }
        print(RED + "❌ Chỉ chọn 1, 2, 3 hoặc 4.")


def choose_hotkeys():
    print()
    print(CYAN + "✦ Chọn 2 nút cho Tool 3:")
    capture = input(
        WHITE + f"Nút 1 - Chụp thêm ảnh [mặc định {DEFAULT_CAPTURE_HOTKEY}]: " + RESET
    ).strip() or DEFAULT_CAPTURE_HOTKEY

    send = input(
        WHITE + f"Nút 2 - Gửi tất cả ảnh [mặc định {DEFAULT_SEND_HOTKEY}]: " + RESET
    ).strip() or DEFAULT_SEND_HOTKEY

    if capture == send:
        print(YELLOW + "⚠ Hai nút không được giống nhau. Nút 2 được đặt về mặc định '.")
        send = DEFAULT_SEND_HOTKEY

    return capture, send


def create_new_config():
    api_key = get_api()
    model = choose_model()
    capture_hotkey, send_hotkey = choose_hotkeys()
    config = {
        **model,
        # Giữ tên key cũ để tương thích launcher hiện tại.
        "hotkey": capture_hotkey,
        "click_hotkey": send_hotkey,
        # Thêm tên mới để code dễ hiểu và tương thích về sau.
        "capture_hotkey": capture_hotkey,
        "send_hotkey": send_hotkey,
    }
    save_config(config)
    return api_key, config


def setup():
    show_banner()
    old = load_config()
    print(CYAN + "✦ SETUP TOOL - Y: cấu hình mới | N: dùng cấu hình đã lưu")
    while True:
        option = input(WHITE + "➤ Lựa chọn Y/N: " + RESET).strip().upper()
        if option == "Y":
            return create_new_config()
        if option == "N":
            if not old:
                print(YELLOW + "⚠ Chưa có cấu hình cũ, chuyển sang tạo mới.")
                return create_new_config()
            api_key = get_api()
            return api_key, old
        print(RED + "❌ Chỉ nhập Y hoặc N.")


API_KEY, CONFIG = setup()
client = genai.Client(api_key=API_KEY)
MODEL = CONFIG.get("model", "gemini-3.5-flash-lite")
CAPTURE_HOTKEY = CONFIG.get("hotkey", CONFIG.get("capture_hotkey", DEFAULT_CAPTURE_HOTKEY))
SEND_HOTKEY = CONFIG.get("click_hotkey", CONFIG.get("send_hotkey", DEFAULT_SEND_HOTKEY))


# ============================================================
# DANH SÁCH ẢNH CỦA LÔ HIỆN TẠI
# ============================================================

pending_images = []
pending_lock = threading.Lock()
busy = False
busy_lock = threading.Lock()


def get_next_screenshot_path():
    stamp = time.strftime("%Y%m%d_%H%M%S")
    index = 1
    while True:
        path = PICTURE_DIR / f"{stamp}_{index:03d}.jpg"
        if not path.exists():
            return path
        index += 1


def capture_image():
    """Nút 1: chụp thêm 1 ảnh và đưa vào lô hiện tại."""
    try:
        image = pyautogui.screenshot()
        path = get_next_screenshot_path()
        image.save(path, format="JPEG", quality=JPEG_QUALITY)

        with pending_lock:
            pending_images.append(path)
            count = len(pending_images)

        print()
        print_box(
            "ĐÃ CHỤP THÊM 1 ẢNH",
            [
                f"Ảnh: {path.name}",
                f"Đang chờ: {count} ảnh",
                f"Bấm {CAPTURE_HOTKEY} để chụp tiếp",
                f"Bấm {SEND_HOTKEY} để gửi toàn bộ {count} ảnh",
            ],
            color=GREEN,
        )
    except pyautogui.FailSafeException:
        print(RED + "🛑 Đã dừng bằng FAILSAFE.")
    except Exception as e:
        print(RED + "❌ Không chụp được ảnh:")
        print(e)


# ============================================================
# GEMINI PROMPT
# ============================================================

BATCH_PROMPT = """
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


def copy_text_to_clipboard(text):
    if os.name != "nt":
        raise RuntimeError("Clipboard của tool này hiện dành cho Windows.")

    text = "" if text is None else str(text)
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p

    data = (text + "\0").encode("utf-16-le")
    h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not h_global:
        raise RuntimeError("Không cấp phát được bộ nhớ clipboard.")

    locked = kernel32.GlobalLock(h_global)
    if not locked:
        kernel32.GlobalFree(h_global)
        raise RuntimeError("Không khóa được bộ nhớ clipboard.")

    ctypes.memmove(locked, data, len(data))
    kernel32.GlobalUnlock(h_global)

    opened = False
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
        result = user32.SetClipboardData(CF_UNICODETEXT, h_global)
        if not result:
            kernel32.GlobalFree(h_global)
            raise RuntimeError("Không ghi được dữ liệu vào clipboard.")
        h_global = None
    finally:
        user32.CloseClipboard()


def send_all_images():
    """Nút 2: gửi toàn bộ ảnh của lô hiện tại trong MỘT request Gemini."""
    global busy

    with pending_lock:
        batch = list(pending_images)

    if not batch:
        print()
        print(YELLOW + f"⚠ Chưa có ảnh nào. Bấm {CAPTURE_HOTKEY} để chụp trước.")
        return

    try:
        print()
        print_box(
            "GỬI TẤT CẢ ẢNH SANG GEMINI",
            [
                f"Số ảnh: {len(batch)}",
                f"Model: {CONFIG.get('model_name', MODEL)}",
                "Trạng thái: Đang xử lý...",
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
                "text": f"Ảnh {index}: {path.name}",
            })
            input_parts.append({
                "type": "image",
                "data": image_base64,
                "mime_type": "image/jpeg",
            })

        input_parts.append({"type": "text", "text": BATCH_PROMPT})

        interaction = client.interactions.create(
            model=MODEL,
            input=input_parts,
        )

        answer = (interaction.output_text or "").strip()
        if not answer:
            raise RuntimeError("Gemini không trả về đáp án.")

        copy_text_to_clipboard(answer)
        ANSWER_FILE.write_text(answer + "\n", encoding="utf-8")

        # Chỉ xóa danh sách chờ sau khi gửi + copy thành công.
        # File ảnh vẫn được giữ lại trong C:\duc\picture\screenshot_clipboard.
        with pending_lock:
            sent_set = set(batch)
            pending_images[:] = [p for p in pending_images if p not in sent_set]
            remaining = len(pending_images)

        elapsed = time.perf_counter() - start
        print()
        print_box(
            "GEMINI ĐÃ TRẢ ĐÁP ÁN",
            [
                f"Đã gửi: {len(batch)} ảnh",
                f"Đã copy Clipboard: {answer}",
                f"Đã ghi file: {ANSWER_FILE}",
                f"Ảnh còn chờ: {remaining}",
                f"Thời gian: {elapsed:.2f}s",
            ],
            color=GREEN,
            width=74,
        )

    except Exception as e:
        print()
        print(RED + "❌ Gửi Gemini thất bại. Danh sách ảnh vẫn được giữ nguyên để gửi lại.")
        print(e)
    finally:
        with busy_lock:
            busy = False


def trigger_send():
    global busy
    with busy_lock:
        if busy:
            print(YELLOW + "⏳ Gemini đang xử lý lô ảnh hiện tại...")
            return
        busy = True

    threading.Thread(target=send_all_images, daemon=True).start()


# ============================================================
# READY
# ============================================================

screen_width, screen_height = pyautogui.size()
print()
print_box(
    "TOOL 3 ĐÃ SẴN SÀNG",
    [
        f"Màn hình: {screen_width} x {screen_height}",
        f"Nút 1 - Chụp thêm ảnh    : {CAPTURE_HOTKEY}",
        f"Nút 2 - Gửi tất cả ảnh  : {SEND_HOTKEY}",
        f"Thư mục ảnh             : {PICTURE_DIR}",
        "Sau khi gửi thành công: đáp án tự copy vào Clipboard",
        "ESC: thoát tool",
    ],
    color=PINK,
    width=76,
)
print()
print(GREEN + "Bạn có thể bấm Nút 1 liên tục để gom bao nhiêu ảnh tùy ý.")
print(GREEN + "Khi đủ ảnh, bấm Nút 2 đúng 1 lần để gửi cả lô.")
print()

keyboard.add_hotkey(CAPTURE_HOTKEY, capture_image, suppress=True)
keyboard.add_hotkey(SEND_HOTKEY, trigger_send, suppress=True)
keyboard.wait(EXIT_KEY)

print()
print(PINK + "✦ Đã đóng Tool 3. ✦")
