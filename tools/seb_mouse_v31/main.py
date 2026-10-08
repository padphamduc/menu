# -*- coding: utf-8 -*-
# ==============================================================================
# TOOL V3.1 DÙNG CHUỘT ( THÊM TÍNH NĂNG HIỂN THỊ ĐÁP ÁN TỰ LUẬN )
# ĐỨC DẠY BẠN HỌC NHÉ <3
# ==============================================================================
# Chức năng:
# - Bấm 2 lần chuột phải liên tục : Chụp full màn hình gửi Gemini giải bài
# - Bấm 4 lần chuột trái liên tục  : Tự động gõ đáp án tự luận vào bài thi (Unicode, không Clipboard)
# - Bấm 2 lần chuột trái liên tục  : Hiển thị chấm đỏ trắc nghiệm + chữ tự luận
# - Bấm 1 lần chuột trái ngoài chữ: Ẩn ngay lập tức toàn bộ dấu và chữ đáp án
# ==============================================================================

import os
import sys
import json
import time
import ctypes
from ctypes import wintypes
import threading
import re
import base64
from pathlib import Path
from io import BytesIO
from typing import List, Dict, Any, Tuple, Literal, Optional

# Thêm đường dẫn project C:\duc để nạp core modules
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(Path(r"C:\duc")) not in sys.path:
    sys.path.insert(0, r"C:\duc")

import tkinter as tk
from tkinter import font as tkfont
import keyboard
from colorama import Fore, Style, init

from core.screen_capture import capture_screen
from core.ai_client import get_ai_client, get_ai_config, UnifiedAIClient

from pydantic import BaseModel, Field


# ==============================================================================
# KHỞI TẠO TERMINAL & WINDOWS DPI
# ==============================================================================

init(autoreset=True)

PINK = Fore.MAGENTA + Style.BRIGHT
CYAN = Fore.CYAN + Style.BRIGHT
GREEN = Fore.GREEN + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
BLUE = Fore.BLUE + Style.BRIGHT
WHITE = Fore.WHITE + Style.BRIGHT
RESET = Style.RESET_ALL

TOOL_TITLE = "Tool v3.1 Dùng Chuột ( Thêm tính năng hiển thị đáp án tự luận )"

if os.name == "nt":
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
        ctypes.windll.kernel32.SetConsoleTitleW(TOOL_TITLE)
    except Exception:
        pass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ==============================================================================
# THƯ MỤC LƯU DỮ LIỆU & CONFIG RIÊNG CHO V3.1
# ==============================================================================

BASE_DIR = Path(r"C:\duc")
BASE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = BASE_DIR / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "seb_mouse_v31.json"
KEY_FILE = BASE_DIR / "key.txt"
PICTURE_DIR = BASE_DIR / "picture"
PICTURE_DIR.mkdir(parents=True, exist_ok=True)
ANSWER_FILE = BASE_DIR / "dapan_v31.txt"

DEFAULT_CONFIG: Dict[str, Any] = {
    "model": "gemini-3.5-flash-lite",
    "model_name": "Gemini 3.5 Flash-Lite",
    "level": "1",
    "daily_limit": 500,
    "double_click_interval": 0.35,
    "load_cursor_duration": 1.0,
    "dot_percent": 12,
    "number_opacity": 20,
    "text_opacity": 20,
    "text_font_size": 11,
    "text_fg": "#111111",
}

CONFIG: Dict[str, Any] = dict(DEFAULT_CONFIG)


def percent_to_diameter(percent: int) -> int:
    try:
        p = float(percent)
    except Exception:
        p = 12.0
    p = max(1.0, min(100.0, p))
    return max(2, int(round(2 + (p - 1) * (30 - 2) / 99)))


def load_config() -> Dict[str, Any]:
    global CONFIG
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                CONFIG.update(saved)
                # Độ mờ chữ dùng chung với tùy chỉnh độ mờ số câu
                if "number_opacity" in saved:
                    CONFIG["text_opacity"] = saved["number_opacity"]
        except Exception:
            pass
    return CONFIG


def save_config(data: Dict[str, Any]):
    global CONFIG
    CONFIG.update(data)
    try:
        CONFIG_FILE.write_text(json.dumps(CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


load_config()


# ==============================================================================
# CON TRỎ CHUỘT LOADING KHI ĐANG XỬ LÝ
# ==============================================================================

def show_loading_cursor_once(duration: float = None):
    if os.name != "nt":
        return
    if duration is None:
        duration = float(CONFIG.get("load_cursor_duration", 1.0))
    if duration <= 0:
        return
    try:
        user32 = ctypes.windll.user32
        IDC_WAIT = 32514
        OCR_NORMAL = 32512
        SPI_SETCURSORS = 0x0057
        wait_cursor = user32.LoadCursorW(None, IDC_WAIT)
        if not wait_cursor:
            return
        copy_cursor = user32.CopyImage(wait_cursor, 2, 0, 0, 0)
        if not copy_cursor:
            return
        user32.SetSystemCursor(copy_cursor, OCR_NORMAL)

        def restore():
            time.sleep(duration)
            try:
                user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            except Exception:
                pass

        threading.Thread(target=restore, daemon=True).start()
    except Exception:
        pass


# ==============================================================================
# LỚP GIAO DIỆN HIỂN THỊ DẤU CHẤM TRẮC NGHIỆM & KHUNG ĐÁP ÁN TỰ LUẬN
# (WIN32 DWM TOPMOST, KHÔNG GIÀNH FOCUS, BÁM GÓC DƯỚI PHẢI)
# ==============================================================================

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080

class DotOverlay:
    """
    Quản lý các lớp phủ giao diện độc quyền cho Tool v3.1:
    1. Chấm đỏ trắc nghiệm tại tọa độ câu hỏi (click-through).
    2. Lớp chữ nổi trong suốt ở góc dưới bên phải màn hình cho câu tự luận/điền ngắn
       (Hoàn toàn không có khung, nền, viền, tiêu đề, nút hoặc thanh cuộn.
        Click-through hoàn toàn, không cướp focus, hỗ trợ chỉnh độ mờ).
    3. Số câu hỏi trắc nghiệm đen mờ ở góc dưới phải nếu có câu trắc nghiệm.
    """

    def __init__(self):
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._ready = threading.Event()
        self._root = None
        self._windows = []
        self._q_badge_win = None
        self._text_win = None
        self._text_region_rect = None  # (x1, y1, x2, y2)
        self.last_show_time = 0.0

        self._thread.start()
        self._ready.wait(timeout=3)

    def _run_loop(self):
        self._root = tk.Tk()
        self._root.withdraw()
        self._ready.set()
        self._root.mainloop()

    def is_visible(self) -> bool:
        return bool(self._windows or self._q_badge_win or self._text_win)

    def is_point_in_text_region(self, x: int, y: int) -> bool:
        """Kiểm tra con trỏ chuột có đang nằm bên trong vùng hiển thị chữ đáp án hay không."""
        if not self._text_win or not self._text_region_rect:
            return False
        x1, y1, x2, y2 = self._text_region_rect
        return (x1 <= x <= x2) and (y1 <= y <= y2)

    def show_results(
        self,
        points: List[Tuple[int, int]],
        diameter: int = None,
        question_number: str = "",
        written_items: List[Dict[str, Any]] = None,
        status_message: str = "",
        is_waiting: bool = False,
    ):
        if not self._root:
            return
        self._root.after(
            0,
            self._show_results_on_ui_thread,
            points,
            diameter,
            question_number,
            written_items or [],
            status_message,
            is_waiting,
        )

    def hide_all(self):
        if not self._root:
            return
        self._root.after(0, self._hide_all_on_ui_thread)

    def _hide_all_on_ui_thread(self):
        for w in self._windows:
            try:
                w.destroy()
            except Exception:
                pass
        self._windows.clear()

        if self._q_badge_win:
            try:
                self._q_badge_win.destroy()
            except Exception:
                pass
            self._q_badge_win = None

        if self._text_win:
            try:
                self._text_win.destroy()
            except Exception:
                pass
            self._text_win = None

        self._text_region_rect = None

    def _get_toplevel_hwnd(self, win):
        try:
            f = win.frame()
            if f:
                return int(f, 16)
        except Exception:
            pass
        try:
            user32 = ctypes.windll.user32
            child = win.winfo_id()
            p = user32.GetParent(child)
            return p if p else child
        except Exception:
            return win.winfo_id()

    def _show_results_on_ui_thread(
        self,
        points: List[Tuple[int, int]],
        diameter: int,
        question_number: str,
        written_items: List[Dict[str, Any]],
        status_message: str,
        is_waiting: bool,
    ):
        self._hide_all_on_ui_thread()
        load_config()

        self.last_show_time = time.time()
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()

        # ----------------------------------------------------------------------
        # 1. HIỂN THỊ CÁC DẤU CHẤM ĐỎ TRẮC NGHIỆM TẠI ĐÁP ÁN ĐÚNG
        # ----------------------------------------------------------------------
        dot_p = int(CONFIG.get("dot_percent", 12))
        d = max(2, int(diameter)) if diameter else percent_to_diameter(dot_p)
        pad = 2
        win_size = d + pad * 2

        for (x, y) in points:
            try:
                win = tk.Toplevel(self._root)
                win.overrideredirect(True)
                win.attributes("-topmost", True)
                win.lift()
                wx = int(x - win_size // 2)
                wy = int(y - win_size // 2)
                win.geometry(f"{win_size}x{win_size}+{wx}+{wy}")

                bg_color = "#010101"
                win.configure(bg=bg_color)
                win.attributes("-transparentcolor", bg_color)

                canvas = tk.Canvas(win, width=win_size, height=win_size, bg=bg_color, highlightthickness=0)
                canvas.pack()
                canvas.create_oval(pad, pad, pad + d, pad + d, fill="#FF0000", outline="#FF0000")
                win.update_idletasks()

                top_hwnd = self._get_toplevel_hwnd(win)
                user32 = ctypes.windll.user32
                style = user32.GetWindowLongW(top_hwnd, GWL_EXSTYLE)
                style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
                user32.SetWindowLongW(top_hwnd, GWL_EXSTYLE, style)
                user32.SetLayeredWindowAttributes(top_hwnd, 0x00010101, 0, 1)

                self._windows.append(win)
            except Exception:
                pass

        # ----------------------------------------------------------------------
        # ----------------------------------------------------------------------
        # 2. ĐÁP ÁN TỰ LUẬN / ĐIỀN NGẮN: CHỈ HIỂN THỊ CHỮ Ở GÓC DƯỚI BÊN PHẢI
        # Hoàn toàn không có khung, nền, viền, tiêu đề, nút hoặc thanh cuộn.
        # Có số câu để phân biệt khi có nhiều đáp án. Giữ xuống dòng, tự ngắt dòng.
        # Không giành focus và không chặn click chuột với nội dung phía dưới.
        # ----------------------------------------------------------------------
        work_l, work_t, work_r, work_b = 0, 0, screen_w, screen_h
        if os.name == "nt":
            try:
                rect = wintypes.RECT()
                SPI_GETWORKAREA = 0x0030
                if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                    work_l = int(rect.left)
                    work_t = int(rect.top)
                    work_r = int(rect.right)
                    work_b = int(rect.bottom)
            except Exception:
                pass

        has_text_content = bool(written_items or status_message or is_waiting)
        text_y_top = work_b - 40

        if has_text_content:
            try:
                lines = []
                if is_waiting:
                    lines.append("⏳ Đang phân tích bài thi...")
                elif written_items:
                    if len(written_items) == 1:
                        it = written_items[0]
                        q_num_item = str(it.get("question_number", "")).strip() or str(question_number).strip()
                        ans_content = str(it.get("answer_text", "")).strip()
                        if not ans_content and it.get("answers"):
                            ans_content = ", ".join(str(a) for a in it.get("answers"))
                        if ans_content:
                            if q_num_item:
                                lines.append(f"Câu {q_num_item}: {ans_content}")
                            else:
                                lines.append(ans_content)
                    else:
                        for idx, it in enumerate(written_items):
                            q_num_item = str(it.get("question_number", "")).strip() or str(idx + 1)
                            ans_content = str(it.get("answer_text", "")).strip()
                            if not ans_content and it.get("answers"):
                                ans_content = ", ".join(str(a) for a in it.get("answers"))
                            if ans_content:
                                lines.append(f"Câu {q_num_item}: {ans_content}")

                if status_message and not is_waiting:
                    lines.append(f"[{status_message}]")

                full_text = "\n".join(lines).strip()

                if full_text:
                    font_size = int(CONFIG.get("text_font_size", CONFIG.get("text_box_font_size", 11)))
                    font_size = max(8, min(40, font_size))
                    text_fg = str(CONFIG.get("text_fg", CONFIG.get("text_box_fg", "#111111")))
                    # Độ mờ của chữ (0% - 100%): 0% trong suốt hoàn toàn, 100% rõ hoàn toàn
                    text_op_val = int(CONFIG.get("text_opacity", 90))
                    text_op_val = max(0, min(100, text_op_val))
                    alpha_ratio = float(text_op_val) / 100.0

                    wrap_w = min(560, max(280, work_r - 60))

                    t_win = tk.Toplevel(self._root)
                    t_win.overrideredirect(True)
                    t_win.attributes("-topmost", True)
                    t_win.lift()

                    bg_chroma = "#FF00FE"
                    t_win.configure(bg=bg_chroma)
                    t_win.attributes("-transparentcolor", bg_chroma)
                    t_win.attributes("-alpha", alpha_ratio)

                    canvas = tk.Canvas(t_win, bg=bg_chroma, highlightthickness=0)
                    canvas.pack(fill="both", expand=True)

                    t_item = canvas.create_text(
                        6, 6,
                        text=full_text,
                        font=("Segoe UI", font_size, "bold"),
                        fill=text_fg,
                        anchor="nw",
                        width=wrap_w
                    )

                    t_win.update_idletasks()
                    bbox = canvas.bbox(t_item)
                    if bbox:
                        content_w = (bbox[2] - bbox[0]) + 14
                        content_h = (bbox[3] - bbox[1]) + 14
                    else:
                        content_w = 340
                        content_h = 100

                    margin_r = 20
                    margin_b = 20
                    tx = max(10, work_r - content_w - margin_r)
                    ty = max(10, work_b - content_h - margin_b)
                    text_y_top = ty

                    t_win.geometry(f"{content_w}x{content_h}+{tx}+{ty}")
                    t_win.update_idletasks()

                    top_t_hwnd = self._get_toplevel_hwnd(t_win)
                    user32 = ctypes.windll.user32
                    t_style = user32.GetWindowLongW(top_t_hwnd, GWL_EXSTYLE)
                    t_style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
                    user32.SetWindowLongW(top_t_hwnd, GWL_EXSTYLE, t_style)
                    alpha_byte = max(0, min(255, int(round(255 * alpha_ratio))))
                    user32.SetLayeredWindowAttributes(top_t_hwnd, 0x00FE00FF, alpha_byte, 1 | 2)

                    self._text_win = t_win
                    self._text_region_rect = (tx, ty, tx + content_w, ty + content_h)

                    try:
                        preview_txt = full_text.replace('\n', ' ')[:40]
                        print(f"[DEBUG UI] Đã tạo lớp chữ đáp án: '{preview_txt}...' | Kích thước: {content_w}x{content_h} | Tọa độ: ({tx}, {ty}) | Độ mờ: {text_op_val}%")
                    except Exception:
                        pass

            except Exception as e:
                try:
                    print(f"Warning: Lỗi tạo lớp chữ tự luận: {e}")
                except Exception:
                    pass

        # 3. HIỂN THỊ SỐ CÂU HỎI TRẮC NGHIỆM ĐEN MỜ (NẾU CÓ TRẮC NGHIỆM)
        # ----------------------------------------------------------------------
        num_opacity = int(CONFIG.get("number_opacity", 20))
        q_text = str(question_number).strip()

        # Chỉ hiện số câu trắc nghiệm khi có câu trắc nghiệm (points không rỗng)
        if q_text and num_opacity > 0 and points:
            try:
                font_size = 22
                w = max(50, len(q_text) * 20 + 20)
                h = 44
                x = screen_w - w - 25

                # Nếu lớp chữ tự luận đang hiện, đưa số câu trắc nghiệm nằm phía trên lớp chữ
                if self._text_win:
                    y = max(10, text_y_top - h - 6)
                else:
                    y = screen_h - h - 30

                q_win = tk.Toplevel(self._root)
                q_win.overrideredirect(True)
                q_win.attributes("-topmost", True)
                q_win.lift()
                q_win.geometry(f"{w}x{h}+{x}+{y}")

                alpha_ratio = max(0.01, min(1.0, float(num_opacity) / 100.0))
                q_win.attributes("-alpha", alpha_ratio)

                bg_key = "#FF00FF"
                q_win.configure(bg=bg_key)
                q_win.attributes("-transparentcolor", bg_key)

                q_canvas = tk.Canvas(q_win, width=w, height=h, bg=bg_key, highlightthickness=0)
                q_canvas.pack(fill="both", expand=True)
                q_canvas.create_text(w // 2, h // 2, text=q_text, fill="#000000", font=("Segoe UI", font_size, "bold"))

                q_win.update_idletasks()
                top_q_hwnd = self._get_toplevel_hwnd(q_win)
                user32 = ctypes.windll.user32
                q_style = user32.GetWindowLongW(top_q_hwnd, GWL_EXSTYLE)
                q_style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
                user32.SetWindowLongW(top_q_hwnd, GWL_EXSTYLE, q_style)
                alpha_byte = max(1, min(255, int(round(255 * alpha_ratio))))
                user32.SetLayeredWindowAttributes(top_q_hwnd, 0x00FF00FF, alpha_byte, 1 | 2)

                self._q_badge_win = q_win
            except Exception:
                pass

dot_overlay = DotOverlay()


# ==============================================================================
# ĐỊNH NGHĨA PYDANTIC MODEL VÀ PROMPT CHO GEMINI
# (HỖ TRỢ TRẮC NGHIỆM, ĐIỀN NGẮN, TỰ LUẬN, VÀ THIẾU DỮ KIỆN)
# ==============================================================================

class QuestionItem(BaseModel):
    question_number: str = Field(
        ...,
        description="Mã hoặc số thứ tự câu hỏi (ví dụ '1', '22', 'Câu 3'). Nếu không tìm thấy số câu thì để chuỗi rỗng ''."
    )
    question_type: Literal["multiple_choice", "short_answer", "essay", "unknown"] = Field(
        ...,
        description="Loại câu hỏi: 'multiple_choice' (trắc nghiệm), 'short_answer' (câu điền ngắn/từ/số), 'essay' (tự luận/lời giải/đoạn văn), hoặc 'unknown' (không rõ)."
    )
    answers: list[str] = Field(
        ...,
        description="Với trắc nghiệm (multiple_choice): danh sách các chữ cái đáp án đúng (ví dụ ['A'] hoặc ['A', 'C']). Với loại khác: để trống []."
    )
    boxes_2d: list[list[int]] = Field(
        ...,
        description="Với trắc nghiệm (multiple_choice): danh sách các box 2D [ymin, xmin, ymax, xmax] 0-1000 bao quanh thật sát ô chọn/chữ cái đáp án đúng. Với loại khác: để trống []."
    )
    answer_text: str = Field(
        ...,
        description="BẮT BUỘC TRẢ LỜI ĐÁP ÁN: Bạn phải trực tiếp suy nghĩ giải quyết câu hỏi trong ảnh và ghi đáp án vào đây! Với short_answer: trả trực tiếp đáp án cần điền, ngắn gọn, đúng định dạng và đơn vị nếu có. Với essay: trả nội dung trả lời hoàn chỉnh, chính xác, đủ ý theo yêu cầu câu hỏi; chỉ đưa lời giải hoặc lập luận khi đề yêu cầu hoặc cần thiết để trả lời đầy đủ. Với multiple_choice: có thể để trống ''. Tuyệt đối KHÔNG bỏ trống đối với short_answer/essay và KHÔNG ghi các mô tả chung chung như 'câu tự luận'!"
    )


class QuizResultV31(BaseModel):
    questions: list[QuestionItem] = Field(
        ...,
        description="Danh sách tất cả các câu hỏi nhận diện và giải được trong ảnh."
    )
    question_number: str = Field(
        default="",
        description="Tương thích ngược: số thứ tự câu hỏi chính hoặc danh sách câu (ví dụ '22' hoặc '1, 2')."
    )
    question_type: Literal["multiple_choice", "short_answer", "essay", "mixed", "unknown"] = Field(
        default="multiple_choice",
        description="Tương thích ngược: 'multiple_choice', 'short_answer', 'essay', 'mixed', hoặc 'unknown'."
    )
    answers: list[str] = Field(
        default_factory=list,
        description="Tương thích ngược: danh sách các chữ cái đáp án đúng của các câu trắc nghiệm nếu có."
    )
    boxes_2d: list[list[int]] = Field(
        default_factory=list,
        description="Tương thích ngược: danh sách các box 2D [ymin, xmin, ymax, xmax] 0-1000 cho các đáp án trắc nghiệm."
    )
    answer_text: str = Field(
        default="",
        description="Tương thích ngược: nội dung đáp án chữ tổng hợp nếu có."
    )
    needs_more_info: bool = Field(
        default=False,
        description="true nếu ảnh mờ, bị che khuất hoặc thiếu dữ kiện quan trọng khiến không thể giải đáp án; ngược lại false."
    )
    status_message: str = Field(
        default="",
        description="Thông báo ngắn gọn, rõ ràng nếu ảnh mờ, thiếu dữ kiện hoặc cần bổ sung thông tin. Để trống '' nếu giải bình thường."
    )


QUIZ_PROMPT_V31 = """
Bạn là trợ lý giải đề thi và bài tập từ ảnh chụp màn hình bài thi trực tiếp.
Nhiệm vụ của bạn:
1. Đọc đầy đủ toàn bộ câu hỏi, dữ kiện và yêu cầu trả lời xuất hiện trong ảnh chụp.
2. Trực tiếp giải bài và đưa ra câu trả lời chính xác nhất:
   - Nhận diện riêng từng câu hỏi thuộc một trong các loại: 'multiple_choice', 'short_answer', 'essay', 'unknown'.
   - Với câu trắc nghiệm ('multiple_choice'): xác định đáp án đúng trong 'answers' và tọa độ box 2D 'boxes_2d' [ymin, xmin, ymax, xmax] theo thang 0-1000 bao quanh sát ô chọn/chữ cái đáp án đúng để đặt dấu chấm đỏ.
   - Với câu điền ngắn ('short_answer'): BẮT BUỘC giải bài và trả trực tiếp vào 'answer_text' nội dung ngắn gọn cần điền, đúng định dạng và đúng đơn vị (nếu có).
   - Với câu tự luận ('essay'): BẮT BUỘC giải bài và trả trực tiếp vào 'answer_text' nội dung trả lời hoàn chỉnh, chính xác, mạch lạc và đủ ý theo đúng yêu cầu đề bài. Chỉ đưa lời giải, các bước giải hoặc lập luận khi đề yêu cầu hoặc cần thiết để trả lời đầy đủ.
3. Quy tắc nghiêm ngặt về nội dung:
   - BẮT BUỘC phải trực tiếp giải bài và sinh nội dung câu trả lời đầy đủ vào 'answer_text' cho câu tự luận và điền ngắn.
   - Tuyệt đối KHÔNG bỏ trống 'answer_text' đối với câu tự luận (essay) và điền ngắn (short_answer).
   - Tuyệt đối KHÔNG ghi các mô tả chung chung như 'câu tự luận', 'short_answer', 'câu hỏi viết', 'điền vào ô'. Phải là NỘI DUNG ĐÁP ÁN THỰC TẾ do bạn trực tiếp giải!
   - KHÔNG mở đầu bằng lời xã giao (như 'Chào bạn', 'Dưới đây là đáp án...').
   - KHÔNG lặp lại toàn bộ đề bài trong câu trả lời.
   - KHÔNG đoán mò khi ảnh mờ, thiếu dữ kiện hoặc không đọc được; khi đó hãy đặt needs_more_info = true và báo rõ trong status_message cần ảnh chụp rõ hơn hoặc bổ sung thông tin.
   - KHÔNG gắn nhãn 'đã xác minh' giả tạo khi chưa kiểm tra kỹ.

Trả về DUY NHẤT định dạng JSON tuân thủ schema:
{
  "questions": [
    {
      "question_number": "1",
      "question_type": "short_answer",
      "answers": [],
      "boxes_2d": [],
      "answer_text": "Đáp án cần điền"
    }
  ],
  "question_number": "1",
  "question_type": "short_answer",
  "answers": [],
  "boxes_2d": [],
  "answer_text": "Đáp án cần điền",
  "needs_more_info": false,
  "status_message": ""
}
Tuyệt đối chỉ trả về JSON hợp lệ, không dùng markdown codeblocks.
"""


def parse_quiz_result_v31(json_text: str) -> Dict[str, Any]:
    """Phân tích cú pháp JSON phản hồi từ Gemini và chuẩn hóa dữ liệu."""
    clean_text = str(json_text).strip()
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s*```$", "", clean_text)
    m = re.search(r"(\{.*\})", clean_text, flags=re.DOTALL)
    if m:
        clean_text = m.group(1).strip()

    data = None
    try:
        data = json.loads(clean_text)
    except Exception:
        try:
            data = json.loads(clean_text, strict=False)
        except Exception:
            try:
                sanitized = re.sub(r'(?<!\\)\n', r'\\n', clean_text)
                data = json.loads(sanitized, strict=False)
            except Exception:
                pass

    if not isinstance(data, dict):
        return {
            "questions": [],
            "mc_answers": [],
            "mc_boxes": [],
            "written_items": [],
            "question_num": "",
            "needs_more_info": False,
            "status_message": "Không thể phân tích cú pháp phản hồi từ Gemini.",
            "unanswered_count": 0,
        }

    raw_questions = data.get("questions", [])
    if not isinstance(raw_questions, list):
        raw_questions = []

    # Tương thích ngược nếu Gemini trả dạng phẳng không có mảng questions
    if not raw_questions:
        q_num = str(data.get("question_number", "")).strip()
        q_type = str(data.get("question_type", "multiple_choice")).strip().lower()
        ans = data.get("answers", [])
        if not ans and "answer" in data:
            ans = [data["answer"]]
        bxs = data.get("boxes_2d", [])
        if not bxs and "box_2d" in data:
            bxs = [data["box_2d"]]
        ans_txt = str(data.get("answer_text", "")).strip()

        raw_questions.append({
            "question_number": q_num,
            "question_type": q_type,
            "answers": ans,
            "boxes_2d": bxs,
            "answer_text": ans_txt,
        })

    mc_answers = []
    mc_boxes = []
    written_items = []
    detected_numbers = []
    placeholder_patterns = {
        "câu tự luận", "tự luận", "essay", "short_answer",
        "short answer", "điền vào ô", "câu hỏi điền", "câu hỏi viết",
        "(không có nội dung)", "không có nội dung", "none", "n/a", "null"
    }

    detected_unanswered_count = 0

    for item in raw_questions:
        if not isinstance(item, dict):
            continue
        q_num = str(item.get("question_number", "")).strip()
        if q_num:
            detected_numbers.append(q_num)

        q_type = str(item.get("question_type", "")).strip().lower()
        item_answers = item.get("answers", []) or []
        item_boxes = item.get("boxes_2d", []) or []

        # Trích xuất nội dung đáp án qua nhiều tên trường có thể có
        item_text = str(
            item.get("answer_text") or
            item.get("answer") or
            item.get("solution") or
            item.get("text") or
            item.get("content") or
            item.get("essay_answer") or
            item.get("short_answer") or
            ""
        ).strip()

        # Fallback từ data cấp cao nếu chỉ có 1 câu và cấp con trống
        if not item_text and not item_boxes and len(raw_questions) == 1 and data.get("answer_text"):
            item_text = str(data.get("answer_text", "")).strip()

        # Lọc bỏ các mô tả mẫu giả tạo
        if item_text.lower() in placeholder_patterns:
            item_text = ""

        # Phân loại câu hỏi
        is_mc = (q_type == "multiple_choice") or (bool(item_boxes) and bool(item_answers))
        is_written_type = ("short" in q_type) or ("essay" in q_type) or ("điền" in q_type) or ("tự luận" in q_type)

        if is_mc:
            mc_answers.extend([str(a) for a in item_answers])
            mc_boxes.extend(item_boxes)

        if is_written_type or (not is_mc and bool(item_text)):
            if item_text:
                written_items.append({
                    "question_number": q_num,
                    "question_type": "short_answer" if ("short" in q_type or "điền" in q_type) else ("essay" if ("essay" in q_type or "tự luận" in q_type) else q_type),
                    "answer_text": item_text,
                    "answers": item_answers,
                })
            else:
                detected_unanswered_count += 1

    top_q_num = str(data.get("question_number", "")).strip()
    if not top_q_num and detected_numbers:
        top_q_num = ", ".join(dict.fromkeys(detected_numbers))

    needs_info = bool(data.get("needs_more_info", False))
    status_msg = str(data.get("status_message", "")).strip()

    if not status_msg and detected_unanswered_count > 0 and not written_items and not mc_boxes:
        status_msg = "Gemini đã nhận diện được câu hỏi tự luận/điền nhưng chưa trả nội dung đáp án thực tế."

    return {
        "questions": raw_questions,
        "mc_answers": mc_answers,
        "mc_boxes": mc_boxes,
        "written_items": written_items,
        "question_num": top_q_num,
        "needs_more_info": needs_info,
        "status_message": status_msg,
        "unanswered_count": detected_unanswered_count,
    }


# ==============================================================================
# QUẢN LÝ TRẠNG THÁI KẾT QUẢ & CÁC LẦN GỌI PHÂN TÍCH (REQUEST ID)
# ==============================================================================

_current_request_id = 0
_request_lock = threading.Lock()

last_click_points: List[Tuple[int, int]] = []
last_answers: List[str] = []
last_written_items: List[Dict[str, Any]] = []
last_question_num: str = ""
last_status_message: str = ""

state_lock = threading.Lock()
busy = False
busy_lock = threading.Lock()


def get_next_screenshot_path() -> Path:
    for number in range(1, 101):
        image_path = PICTURE_DIR / f"{number}.jpg"
        if not image_path.exists():
            return image_path
    return PICTURE_DIR / "1.jpg"


def print_box(title: str, lines: list = None, color=PINK, width: int = 74, indent: int = 2):
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
    os.system("cls" if os.name == "nt" else "clear")
    print()
    load_config()
    model_name = CONFIG.get("model_name", "Gemini 3.5 Flash-Lite")
    dot_p = CONFIG.get("dot_percent", 12)
    num_op = CONFIG.get("number_opacity", 20)
    cursor_dur = CONFIG.get("load_cursor_duration", 1.0)
    show_box = "BẬT" if CONFIG.get("show_text_box", True) else "TẮT"

    print_box(
        "ĐỨC DẠY BẠN HỌC NHÉ <3",
        [
            "TOOL V3.1 DÙNG CHUỘT (THÊM HIỂN THỊ ĐÁP ÁN TỰ LUẬN & ĐIỀN NGẮN)",
            "----------------------------------------------------------------------",
            "Chuột Phải x2 : Chụp toàn màn hình & gửi Gemini phân tích",
            "Chuột Trái x4  : Tự động gõ đáp án tự luận vào ô đang có con trỏ",
            f"Chuột Trái x2  : Hiện kết quả (Chấm đỏ, số câu & chữ tự luận)",
            "Chuột Trái x1  : Ẩn kết quả khi nhấp ngoài vùng chữ đáp án",
            f"Chữ tự luận    : Lớp chữ nổi không viền (Độ mờ: {CONFIG.get('text_opacity', 90)}%)",
            f"Load chuột     : {cursor_dur}s • Độ mờ số MC: {num_op}%",
            f"Model AI       : {model_name} (Google Gemini)",
            "Phím ESC       : Thoát khỏi tool",
        ],
        color=PINK,
        width=76,
    )
    print()


# ==============================================================================
# HÀM PHÂN TÍCH ẢNH BẰNG GEMINI & LƯU KẾT QUẢ
# ==============================================================================

def solve_and_save():
    global busy, _current_request_id
    global last_click_points, last_answers, last_written_items, last_question_num, last_status_message

    with _request_lock:
        _current_request_id += 1
        my_req_id = _current_request_id

    # 1. XÓA NGAY KẾT QUẢ CŨ & ẨN OVERLAY ĐỂ TRÁNH NHẦM LẪN
    with state_lock:
        last_click_points = []
        last_answers = []
        last_written_items = []
        last_question_num = ""
        last_status_message = ""

    dot_overlay.hide_all()

    with busy_lock:
        if busy:
            print(YELLOW + "⏳ Đang có yêu cầu phân tích đang chạy, hủy phiên cũ và bắt đầu phân tích ảnh mới...")
        busy = True

    try:
        load_config()
        active_model = str(CONFIG.get("model", "gemini-3.5-flash-lite")).strip()

        # Khởi tạo AI Client chuyên dụng cho Gemini
        try:
            client = UnifiedAIClient(provider="gemini")
        except Exception as e:
            err_msg = f"Lỗi khởi tạo Gemini Client: {e}"
            print(RED + f"❌ {err_msg}")
            with state_lock:
                if my_req_id == _current_request_id:
                    last_status_message = err_msg
            return

        start_time = time.time()
        show_loading_cursor_once(float(CONFIG.get("load_cursor_duration", 1.0)))

        print()
        print(CYAN + f"📸 [Chuột Phải x2] Đã chụp toàn bộ màn hình, đang gửi Gemini ({active_model})...")

        screenshot = capture_screen()
        screen_w, screen_h = screenshot.size

        # Lưu ảnh vào C:\duc\picture
        image_path = get_next_screenshot_path()
        try:
            screenshot.save(image_path, "JPEG", quality=88)
        except Exception:
            pass

        buf = BytesIO()
        screenshot.save(buf, format="JPEG", quality=85)
        image_bytes = buf.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        quiz_schema = {
            "type": "text",
            "mime_type": "application/json",
            "schema": QuizResultV31.model_json_schema()
        }

        try:
            res_inter = client.generate_quiz_interaction(
                model=active_model,
                inputs=[
                    {"type": "image", "data": image_b64},
                    {"type": "text", "text": QUIZ_PROMPT_V31}
                ],
                response_format=quiz_schema
            )
            raw_output_text = res_inter.output_text
        except Exception as api_err:
            err_str = f"Lỗi gọi Gemini API: {api_err}"
            print(RED + f"❌ {err_str}")
            with state_lock:
                if my_req_id == _current_request_id:
                    last_status_message = err_str
            return

        # Kiểm tra tính hợp lệ của phiên gọi (nếu có yêu cầu mới đã bấm thì bỏ qua bản cũ)
        with _request_lock:
            if my_req_id != _current_request_id:
                print(YELLOW + "ℹ Bỏ qua kết quả do đã có yêu cầu chụp mới hơn.")
                return

        # Hiển thị loading ngắn báo hiệu đã nhận dữ liệu
        show_loading_cursor_once(float(CONFIG.get("load_cursor_duration", 1.0)))

        # Ghi log debug an toàn (không ghi API key)
        clean_preview = raw_output_text.strip().replace('\r', '')
        print(f"[DEBUG GEMINI] Nhận {len(clean_preview)} ký tự phản hồi từ Gemini.")

        parsed = parse_quiz_result_v31(raw_output_text)
        mc_boxes = parsed.get("mc_boxes", [])
        mc_answers = parsed.get("mc_answers", [])
        written_items = parsed.get("written_items", [])
        q_num = parsed.get("question_num", "")
        needs_more_info = parsed.get("needs_more_info", False)
        status_msg = parsed.get("status_message", "")
        unanswered_cnt = parsed.get("unanswered_count", 0)
        print(f"[DEBUG PARSE] Trắc nghiệm: {len(mc_boxes)} boxes, {len(mc_answers)} ans | Tự luận/Điền: {len(written_items)} câu hợp lệ (thiếu text: {unanswered_cnt})")

        # Chuyển đổi tọa độ 0..1000 sang pixel thực tế của màn hình
        click_points = []
        for box in mc_boxes:
            try:
                ymin, xmin, ymax, xmax = [int(round(float(v))) for v in box]
            except Exception:
                continue
            ymin = max(0, min(1000, ymin))
            ymax = max(0, min(1000, ymax))
            xmin = max(0, min(1000, xmin))
            xmax = max(0, min(1000, xmax))

            top = int(round((ymin / 1000.0) * screen_h))
            bottom = int(round((ymax / 1000.0) * screen_h))
            left = int(round((xmin / 1000.0) * screen_w))
            right = int(round((xmax / 1000.0) * screen_w))
            center_x = int(round((left + right) / 2.0))
            center_y = int(round((top + bottom) / 2.0))
            click_points.append((center_x, center_y))

        # Nếu Gemini báo thiếu dữ kiện hoặc không đọc được đề bài
        if needs_more_info and not status_msg:
            status_msg = "Ảnh mờ hoặc thiếu dữ kiện; cần chụp lại ảnh rõ hơn."

        # Cập nhật trạng thái dùng chung
        with state_lock:
            if my_req_id == _current_request_id:
                last_click_points = list(click_points)
                last_answers = list(mc_answers)
                last_written_items = list(written_items)
                last_question_num = str(q_num).strip()
                last_status_message = str(status_msg).strip()

        # Ghi log đáp án ra file C:\duc\dapan_v31.txt
        try:
            log_lines = [
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Câu: {q_num or 'Không rõ'}",
            ]
            if mc_answers:
                log_lines.append(f"  Trắc nghiệm: {', '.join(mc_answers)}")
            if written_items:
                for w in written_items:
                    log_lines.append(f"  {w.get('question_type', 'Tự luận')} (Câu {w.get('question_number', q_num)}): {w.get('answer_text')}")
            if status_msg:
                log_lines.append(f"  Thông báo: {status_msg}")
            log_lines.append("-" * 50 + "\n")
            with open(ANSWER_FILE, "a", encoding="utf-8") as f:
                f.write("\n".join(log_lines))
        except Exception:
            pass

        elapsed = round(time.time() - start_time, 2)
        try:
            import winsound
            winsound.Beep(1800, 120)
        except Exception:
            pass

        print()
        summary_lines = [
            f"Model AI  : {active_model} (Gemini)",
            f"Thời gian : {elapsed}s",
        ]
        if q_num:
            summary_lines.append(f"Số câu    : {q_num}")
        if mc_answers:
            summary_lines.append(f"Trắc nghiệm: {', '.join(mc_answers)} ({len(click_points)} điểm chấm đỏ)")
        if written_items:
            summary_lines.append(f"Tự luận/Điền: {len(written_items)} câu (Chữ nổi góc dưới phải)")
        elif parsed.get("unanswered_count", 0) > 0:
            summary_lines.append("⚠️ Phát hiện câu tự luận/điền nhưng chưa có nội dung đáp án từ AI")
        if status_msg:
            summary_lines.append(f"Thông báo : {status_msg}")

        summary_lines.extend([
            "👉 BẤM 2 LẦN CHUỘT TRÁI để hiện kết quả (Chấm đỏ, số câu & chữ tự luận)!",
            "👉 BẤM 1 LẦN CHUỘT TRÁI ngoài vùng chữ để ẩn kết quả.",
        ])

        print_box(
            "GEMINI ĐÃ GIẢI XONG ĐỀ THI",
            summary_lines,
            color=GREEN,
            width=76,
        )

    except Exception as e:
        print()
        print(RED + f"❌ Lỗi xử lý: {e}")
        with state_lock:
            if my_req_id == _current_request_id:
                last_status_message = f"Lỗi xử lý: {e}"
    finally:
        with busy_lock:
            busy = False


# ==============================================================================
# CƠ CHẾ GÕ ĐÁP ÁN TỰ LUẬN TRỰC TIẾP (UNICODE WIN32, KHÔNG DÙNG CLIPBOARD)
# ==============================================================================

is_typing = False
typing_lock = threading.Lock()

def type_char_safe(char: str):
    """
    Gõ trực tiếp 1 ký tự vào ô đang có con trỏ nhập liệu.
    Tuyệt đối không dùng Ctrl+V hoặc clipboard.
    Hỗ trợ đầy đủ tiếng Việt có dấu và Unicode bằng Win32 SendInput / keybd_event.
    """
    if char == "\r":
        return
    if char == "\n":
        # Xuống dòng trong khung soạn thảo (không nộp bài)
        try:
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x0D, 0, 0x0002, 0)
            return
        except Exception:
            pass
        return

    if char == "\t":
        # Thay thế Tab bằng 4 khoảng trắng để tránh nhảy focus sang nút submit/nộp bài
        for _ in range(4):
            type_char_safe(" ")
        return

    # Tầng 1: Win32 SendInput Unicode thông qua keyboard._winkeyboard
    try:
        import keyboard._winkeyboard as wk
        wk.type_unicode(char)
        return
    except Exception:
        pass

    # Tầng 2: Win32 keybd_event với cờ KEYEVENTF_UNICODE (0x0004)
    try:
        code = ord(char)
        ctypes.windll.user32.keybd_event(0, code, 0x0004, 0)
        ctypes.windll.user32.keybd_event(0, code, 0x0004 | 0x0002, 0)
        return
    except Exception:
        pass


def get_valid_note_answers() -> str:
    """Trích xuất đáp án hợp lệ từ các câu tự luận / điền ngắn đang hiển thị trong note."""
    with state_lock:
        items = list(last_written_items)

    valid_answers = []
    for it in items:
        txt = str(it.get("answer_text", "")).strip()
        if not txt and it.get("answers"):
            txt = ", ".join(str(a).strip() for a in it.get("answers") if str(a).strip())
        if txt and txt != "(Không có nội dung trả lời)":
            valid_answers.append(txt)

    if not valid_answers:
        return ""

    return "\n".join(valid_answers)


def auto_type_note_answer():
    """
    Tự động gõ đáp án đang hiển thị trong khung note vào ô đang có con trỏ nhập liệu.
    Kích hoạt khi nhấp chuột trái 4 lần liên tiếp.
    """
    global is_typing

    with typing_lock:
        if is_typing:
            print(YELLOW + "⏳ Đang trong tiến trình gõ phím, vui lòng đợi hoàn thành...")
            return
        is_typing = True

    try:
        with busy_lock:
            is_currently_busy = busy

        if is_currently_busy:
            print()
            print(YELLOW + "⏳ Gemini đang phân tích đề thi, chưa có đáp án để gõ.")
            try:
                import winsound
                winsound.Beep(800, 150)
            except Exception:
                pass
            return

        text_to_type = get_valid_note_answers()
        if not text_to_type:
            print()
            print(YELLOW + "⚠️ [Chuột Trái x4] Chưa có đáp án tự luận/điền ngắn hợp lệ để gõ!")
            try:
                import winsound
                winsound.Beep(800, 200)
            except Exception:
                pass
            return

        # Âm thanh báo hiệu bắt đầu gõ
        try:
            import winsound
            winsound.Beep(1600, 60)
            winsound.Beep(2000, 60)
        except Exception:
            pass

        print()
        print_box(
            "TỰ ĐỘNG GÕ ĐÁP ÁN TỰ LUẬN (CHUỘT TRÁI x4)",
            [
                f"Độ dài ký tự  : {len(text_to_type)} ký tự",
                "Phương thức nhập: Win32 Unicode (SendInput / keybd_event)",
                "Bảo mật phím   : KHÔNG dùng Ctrl+V, KHÔNG lưu/đọc Clipboard",
                "Cơ chế an toàn : KHÔNG tự động ấn gửi hoặc nộp bài",
                "👉 Đang tiến hành gõ trực tiếp vào ô có con trỏ...",
            ],
            color=CYAN,
            width=76,
        )

        # Chờ 0.25s để chuột nhả hoàn toàn và ô input nhận focus ổn định
        time.sleep(0.25)

        # Gõ từng ký tự với độ trễ tự nhiên (15ms mỗi ký tự)
        for char in text_to_type:
            if not is_typing:
                break
            type_char_safe(char)
            time.sleep(0.015)

        try:
            import winsound
            winsound.Beep(2200, 100)
        except Exception:
            pass

        print(GREEN + "✔ [Chuột Trái x4] Đã gõ xong toàn bộ đáp án vào ô nhập liệu!")

    except Exception as e:
        print(RED + f"❌ Lỗi khi tự động gõ đáp án: {e}")
    finally:
        with typing_lock:
            is_typing = False


# ==============================================================================
# HÀM HIỂN THỊ KẾT QUẢ KHI NHẤP ĐÚP CHUỘT TRÁI
# ==============================================================================

def mark_saved_coordinate():
    global last_click_points, last_answers, last_written_items, last_question_num, last_status_message, busy

    with busy_lock:
        is_currently_busy = busy

    with state_lock:
        points = list(last_click_points)
        answers = list(last_answers)
        written = list(last_written_items)
        q_num = str(last_question_num).strip()
        status_msg = str(last_status_message).strip()

    # Nếu đang phân tích câu hỏi mà người dùng nhấp chuột trái: CHỈ dùng con trỏ loading, KHÔNG hiện khung/chữ chờ trên màn hình
    if is_currently_busy:
        show_loading_cursor_once(float(CONFIG.get("load_cursor_duration", 1.0)))
        print(YELLOW + "⏳ Gemini đang phân tích đề thi... Con trỏ chuột đang ở trạng thái loading.")
        return

    # Nếu không có kết quả nào và không có thông báo lỗi
    if not points and not written and not status_msg:
        print()
        print(YELLOW + "⚠️ Chưa có dữ liệu đáp án cho bài thi này.")
        print(YELLOW + "👉 Hãy BẤM 2 LẦN CHUỘT PHẢI trước để Gemini chụp và giải đề.")
        return

    try:
        dot_p = int(CONFIG.get("dot_percent", 12))
        dot_d = percent_to_diameter(dot_p)

        dot_overlay.show_results(
            points=points,
            diameter=dot_d,
            question_number=q_num,
            written_items=written,
            status_message=status_msg,
            is_waiting=False,
        )

        try:
            import winsound
            winsound.Beep(1500, 80)
        except Exception:
            pass

        print()
        info_lines = []
        if q_num:
            info_lines.append(f"Câu số       : {q_num}")
        if points:
            info_lines.append(f"Trắc nghiệm  : {len(points)} chấm đỏ ({','.join(answers)})")
        if written:
            info_lines.append(f"Tự luận/Điền : {len(written)} câu chữ nổi ở góc dưới phải")
        if status_msg:
            info_lines.append(f"Thông báo    : {status_msg}")
        info_lines.extend([
            "Trạng thái   : Đang hiển thị",
            "👉 BẤM 1 LẦN CHUỘT TRÁI ngoài vùng chữ để ẩn kết quả.",
        ])

        print_box(
            "ĐÃ HIỂN THỊ KẾT QUẢ ĐÁP ÁN (CHUỘT TRÁI x2)",
            info_lines,
            color=PINK,
            width=74,
        )

    except Exception as e:
        print(RED + f"❌ Không hiển thị được kết quả: {e}")


def hide_saved_coordinate():
    if dot_overlay.is_visible():
        dot_overlay.hide_all()
        print(YELLOW + "✔ [Chuột Trái x1] Đã ẩn toàn bộ dấu chấm và chữ đáp án.")


# ==============================================================================
# BỘ LẮNG NGHE SỰ KIỆN CHUỘT TOÀN CỤC (WIN32 NATIVE HOOK)
# ==============================================================================

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MOUSEWHEEL = 0x020A
WM_QUIT = 0x0012

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

win_user32 = ctypes.windll.user32
win_kernel32 = ctypes.windll.kernel32

win_user32.SetWindowsHookExW.restype = wintypes.HHOOK
win_user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, wintypes.HINSTANCE, wintypes.DWORD]
win_user32.UnhookWindowsHookEx.restype = wintypes.BOOL
win_user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
win_user32.CallNextHookEx.restype = ctypes.c_ssize_t
win_user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
win_user32.GetMessageW.restype = wintypes.BOOL
win_user32.GetMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT]
win_user32.PostThreadMessageW.restype = wintypes.BOOL
win_user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

last_right_time = 0.0
last_left_time = 0.0
right_click_count = 0
left_click_count = 0
pending_left_show_timer = None
pending_left_hide_timer = None
mouse_lock = threading.Lock()

def low_level_mouse_handler(nCode, wParam, lParam):
    global last_right_time, last_left_time, right_click_count, left_click_count
    global pending_left_show_timer, pending_left_hide_timer
    if nCode >= 0:
        now = time.time()
        dbl_interval = float(CONFIG.get("double_click_interval", 0.35))
        wait_sec = max(0.18, dbl_interval * 0.70)

        # Lấy tọa độ con trỏ chuột hiện tại từ cấu trúc hook
        ms_info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
        cursor_x = int(ms_info.pt.x)
        cursor_y = int(ms_info.pt.y)

        # 1. CHUỘT PHẢI: Bỏ kích hoạt 4 lần. Chỉ dùng nhấp 2 lần liên tiếp -> Chụp màn hình & giải đề
        if wParam == WM_RBUTTONDOWN:
            with mouse_lock:
                if is_typing:
                    right_click_count = 0
                    last_right_time = 0.0
                else:
                    if now - last_right_time <= dbl_interval:
                        right_click_count += 1
                    else:
                        right_click_count = 1
                    last_right_time = now

                    # NHẤP 2 LẦN CHUỘT PHẢI: Kích hoạt ngay lập tức
                    if right_click_count == 2:
                        right_click_count = 0
                        last_right_time = 0.0
                        try:
                            import winsound
                            winsound.Beep(1200, 80)
                        except Exception:
                            pass
                        threading.Thread(target=solve_and_save, daemon=True).start()

        # 2. CHUỘT TRÁI:
        # - 4 lần liên tiếp : Tự động gõ đáp án vào ô đang có con trỏ
        # - 2 lần liên tiếp : Hiện kết quả (chấm đỏ, số câu, chữ tự luận)
        # - 1 lần           : Ẩn kết quả (khi kết quả đang hiện và nhấp ngoài vùng chữ)
        elif wParam == WM_LBUTTONDOWN:
            with mouse_lock:
                # Nếu đang trong tiến trình gõ phím -> bỏ qua click để tránh kích hoạt trùng
                if is_typing:
                    left_click_count = 0
                    last_left_time = 0.0
                    return win_user32.CallNextHookEx(None, nCode, wParam, lParam)

                if now - last_left_time <= dbl_interval:
                    left_click_count += 1
                else:
                    left_click_count = 1
                last_left_time = now

                # KÍCH HOẠT: 4 LẦN LIÊN TIẾP -> TỰ ĐỘNG GÕ ĐÁP ÁN
                if left_click_count == 4:
                    if pending_left_show_timer:
                        pending_left_show_timer.cancel()
                        pending_left_show_timer = None
                    if pending_left_hide_timer:
                        pending_left_hide_timer.cancel()
                        pending_left_hide_timer = None

                    left_click_count = 0
                    last_left_time = 0.0
                    threading.Thread(target=auto_type_note_answer, daemon=True).start()

                # CLICK THỨ 3: Người dùng đang bấm tiếp lên 4 lần -> Hủy timer hiện/ẩn
                elif left_click_count == 3:
                    if pending_left_show_timer:
                        pending_left_show_timer.cancel()
                        pending_left_show_timer = None
                    if pending_left_hide_timer:
                        pending_left_hide_timer.cancel()
                        pending_left_hide_timer = None

                # CLICK THỨ 2: Có thể là nhấp đúp hiện kết quả, hoặc đang bấm 4 lần để gõ
                elif left_click_count == 2:
                    if pending_left_hide_timer:
                        pending_left_hide_timer.cancel()
                        pending_left_hide_timer = None

                    def _execute_show_if_no_further():
                        global left_click_count, pending_left_show_timer, last_left_time
                        with mouse_lock:
                            if left_click_count == 2:
                                left_click_count = 0
                                last_left_time = 0.0
                                pending_left_show_timer = None
                                threading.Thread(target=mark_saved_coordinate, daemon=True).start()

                    pending_left_show_timer = threading.Timer(wait_sec, _execute_show_if_no_further)
                    pending_left_show_timer.daemon = True
                    pending_left_show_timer.start()

                # CLICK THỨ 1: Có thể là nhấp 1 lần để ẩn (nếu đang hiện), hoặc là click đầu của chuỗi 2/4 lần
                elif left_click_count == 1:
                    if dot_overlay.is_visible():
                        # Nếu nhấp trong vùng chữ đáp án -> KHÔNG ẩn
                        if dot_overlay.is_point_in_text_region(cursor_x, cursor_y):
                            pass
                        else:
                            grace_period = max(0.40, dbl_interval + 0.1)
                            if now - dot_overlay.last_show_time >= grace_period:
                                def _execute_hide_if_no_further():
                                    global left_click_count, pending_left_hide_timer, last_left_time
                                    with mouse_lock:
                                        if left_click_count == 1:
                                            left_click_count = 0
                                            last_left_time = 0.0
                                            pending_left_hide_timer = None
                                            hide_saved_coordinate()

                                pending_left_hide_timer = threading.Timer(wait_sec, _execute_hide_if_no_further)
                                pending_left_hide_timer.daemon = True
                                pending_left_hide_timer.start()

    return win_user32.CallNextHookEx(None, nCode, wParam, lParam)

_c_mouse_proc = HOOKPROC(low_level_mouse_handler)
_hook_thread_id = None
_h_hook = None
_hook_thread = None

def _mouse_message_loop():
    global _hook_thread_id, _h_hook
    _hook_thread_id = win_kernel32.GetCurrentThreadId()
    _h_hook = win_user32.SetWindowsHookExW(WH_MOUSE_LL, ctypes.cast(_c_mouse_proc, ctypes.c_void_p), None, 0)
    msg = wintypes.MSG()
    while win_user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        pass
    if _h_hook:
        try:
            win_user32.UnhookWindowsHookEx(_h_hook)
        except Exception:
            pass
        _h_hook = None

def start_mouse_listener():
    global _hook_thread
    _hook_thread = threading.Thread(target=_mouse_message_loop, daemon=True)
    _hook_thread.start()

def stop_mouse_listener():
    global _hook_thread_id, _h_hook, pending_left_show_timer, pending_left_hide_timer
    if pending_left_show_timer:
        try:
            pending_left_show_timer.cancel()
        except Exception:
            pass
        pending_left_show_timer = None
    if pending_left_hide_timer:
        try:
            pending_left_hide_timer.cancel()
        except Exception:
            pass
        pending_left_hide_timer = None
    if _hook_thread_id:
        try:
            win_user32.PostThreadMessageW(_hook_thread_id, WM_QUIT, 0, 0)
        except Exception:
            pass
    if _h_hook:
        try:
            win_user32.UnhookWindowsHookEx(_h_hook)
        except Exception:
            pass
        _h_hook = None


# ==============================================================================
# HÀM SETUP & KHỞI ĐỘNG CHÍNH
# ==============================================================================

def main():
    load_config()
    show_banner()

    model_name = CONFIG.get("model_name", "Gemini 3.5 Flash-Lite")
    dbl_interval = float(CONFIG.get("double_click_interval", 0.35))

    print_box(
        "HỆ THỐNG ĐANG LẮNG NGHE CHUỘT",
        [
            "1. Nhấp 2 lần CHUỘT PHẢI liên tiếp : Chụp màn hình & gửi Gemini giải bài",
            "2. Nhấp 4 lần CHUỘT TRÁI liên tiếp  : Tự động gõ đáp án tự luận (Unicode)",
            "3. Nhấp 2 lần CHUỘT TRÁI liên tiếp  : Hiện kết quả (Chấm đỏ, số câu & chữ tự luận)",
            "4. Nhấp 1 lần CHUỘT TRÁI ngoài chữ  : Ẩn ngay lập tức toàn bộ kết quả",
            f"Khoảng cách nhấp: <= {dbl_interval}s",
            f"Cấu hình lưu tại: C:\\duc\\configs\\seb_mouse_v31.json",
            "Bấm phím ESC để thoát tool.",
        ],
        color=GREEN,
        width=76,
    )
    print()

    start_mouse_listener()

    try:
        keyboard.wait("esc")
    except KeyboardInterrupt:
        pass
    finally:
        stop_mouse_listener()
        dot_overlay.hide_all()
        print(YELLOW + f"\nĐã tắt {TOOL_TITLE}. Tạm biệt!")


if __name__ == "__main__":
    main()
