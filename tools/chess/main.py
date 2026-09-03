import pygame
import chess
import chess.engine
import sys
import ctypes
import threading
import os
import json

try:
    import win32gui
    import win32con
    PYWIN32_OK = True
except Exception:
    PYWIN32_OK = False

# Giúp CMD/PowerShell hiển thị tiếng Việt đúng nếu terminal hỗ trợ UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import os
import re
import time
from PIL import Image, ImageTk
import tkinter as tk
import pyautogui
from google import genai

# ============================================================
# CONFIG
# ============================================================
BOARD_SIZE = 720
MIN_BOARD_SIZE = 400
MAX_BOARD_SIZE = 1040
RESIZE_STEP = 80
MINI_MODE_THRESHOLD = 560


def is_mini_mode():
    """True khi bàn cờ đang ở chế độ mini."""
    return BOARD_SIZE < MINI_MODE_THRESHOLD

SQ = BOARD_SIZE // 8
SIDE_W = 260
WIDTH = BOARD_SIZE + SIDE_W
HEIGHT = max(BOARD_SIZE + 40, 760)

STOCKFISH_PATH = r"C:\stockfish\stockfish-windows-x86-64-avx2.exe"
COORD_DIR = r"C:\duc"
COORD_FILE = os.path.join(COORD_DIR, "chess_board_region.json")

# Gemini API key is read from environment variable GEMINI_API_KEY.
GEMINI_MODEL = "gemini-3.7-flash"

PLAYER_COLOR = chess.WHITE
BOARD_FLIPPED = True
WINDOW_PINNED = False
OVERLAY_BOARD_REGION = None
OVERLAY_WINDOW = None
OVERLAY_CANVAS = None
OVERLAY_ROOT = None
AUTO_CLICK_STOCKFISH = True

# ============================================================
# STOCKFISH EXTERNAL DRAG CONFIG
# ============================================================
# Thời gian kéo từ tâm ô đi tới tâm ô đến.
STOCKFISH_DRAG_DURATION = 0.70

# Số bước nội suy trong lúc kéo.
STOCKFISH_DRAG_STEPS = 28

# Giữ nút trái tại ô bắt đầu trước khi bắt đầu kéo.
STOCKFISH_DRAG_START_HOLD = 0.10

# Giữ tại ô đích trước khi nhả chuột.
STOCKFISH_DRAG_END_HOLD = 0.08

# F10 đổi lần lượt các mức thời gian kéo.
DRAG_DELAY_PRESETS = [0.20, 0.35, 0.50, 0.70, 1.00, 1.25, 1.50, 2.00]
DRAG_DELAY_INDEX = 3

EXTERNAL_BOARD_HWND = None
LAST_PIN_REFRESH = 0
PIN_THREAD_STARTED = False
PIN_THREAD_STOP = False

# ============================================================
# COLORS
# ============================================================
LIGHT = (238, 238, 210)
DARK = (118, 150, 86)
SELECT = (246, 246, 105)
LAST = (186, 202, 68)
MOVE_DOT = (70, 70, 70)
BG = (28, 28, 28)
PANEL = (40, 40, 40)
PANEL2 = (55, 55, 55)
TEXT = (240, 240, 240)
WARN = (255, 210, 90)
BORDER = (90, 90, 90)

PLAYER_ARROW = (40, 140, 255)
STOCKFISH_ARROW = (255, 170, 30)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("DUCTOOL - Hỗ Trợ Cờ Vua")

def load_ui_font(size, bold=False):
    # Ưu tiên các font Windows hỗ trợ tiếng Việt đầy đủ.
    candidates = [
        "Segoe UI",
        "Tahoma",
        "Arial",
        "Verdana",
        "DejaVu Sans"
    ]

    available = {name.lower(): name for name in pygame.font.get_fonts()}

    for name in candidates:
        key = name.replace(" ", "").lower()

        # pygame.font.get_fonts() thường trả tên không có khoảng trắng
        if key in available:
            return pygame.font.SysFont(available[key], size, bold=bold)

        try:
            font = pygame.font.SysFont(name, size, bold=bold)
            if font:
                return font
        except Exception:
            pass

    return pygame.font.Font(None, size)


# Font quân cờ Unicode.
piece_font = pygame.font.SysFont("Segoe UI Symbol", 58)
mini_font = pygame.font.SysFont("Segoe UI Symbol", 42)

# Font giao diện tiếng Việt.
status_font = load_ui_font(20)
small_font = load_ui_font(17)
title_font = load_ui_font(22, bold=True)


def refresh_fonts():
    global piece_font, mini_font, status_font, small_font, title_font

    piece_size = max(30, int(SQ * 0.64))
    mini_size = max(28, int(SQ * 0.47))
    status_size = max(16, int(SQ * 0.22))
    small_size = max(14, int(SQ * 0.18))
    title_size = max(18, int(SQ * 0.24))

    piece_font = pygame.font.SysFont("Segoe UI Symbol", piece_size)
    mini_font = pygame.font.SysFont("Segoe UI Symbol", mini_size)
    status_font = load_ui_font(status_size)
    small_font = load_ui_font(small_size)
    title_font = load_ui_font(title_size, bold=True)


def apply_board_size(new_size):
    global BOARD_SIZE, SQ, WIDTH, HEIGHT, screen

    new_size = max(MIN_BOARD_SIZE, min(MAX_BOARD_SIZE, int(new_size)))
    new_size = (new_size // 8) * 8

    BOARD_SIZE = new_size
    SQ = BOARD_SIZE // 8

    if is_mini_mode():
        # Mini mode: chỉ còn bàn cờ, không panel, không status.
        WIDTH = BOARD_SIZE
        HEIGHT = BOARD_SIZE
    else:
        WIDTH = BOARD_SIZE + SIDE_W
        HEIGHT = max(BOARD_SIZE + 40, 760)

    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    refresh_pin_hwnd()

    if is_mini_mode():
        pygame.display.set_caption(
            f"DUCTOOL Hỗ Trợ Cờ Vua - Mini {BOARD_SIZE}x{BOARD_SIZE}"
        )
    else:
        pygame.display.set_caption(
            f"DUCTOOL Hỗ Trợ Cờ Vua - Bàn cờ {BOARD_SIZE}x{BOARD_SIZE}"
        )

    refresh_fonts()
    restore_pin_after_resize()
    print(f"Kích thước bàn cờ: {BOARD_SIZE} x {BOARD_SIZE}")


refresh_fonts()

board = chess.Board()
selected_square = None
last_move = None
last_player_move = None
last_stockfish_move = None
setup_mode = False

dragging = False
drag_piece = None
drag_from_square = None
drag_from_palette = False
drag_mouse = (0, 0)

try:
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
except Exception as e:
    print("Không mở được Stockfish.")
    print("Kiểm tra file:", STOCKFISH_PATH)
    print(e)
    sys.exit()

try:
    engine.configure({
        "Skill Level": 20,
        "Threads": 4,
        "Hash": 256
    })
except Exception:
    engine.configure({"Skill Level": 20})

PIECES = {
    (chess.PAWN, chess.WHITE): "♙",
    (chess.KNIGHT, chess.WHITE): "♘",
    (chess.BISHOP, chess.WHITE): "♗",
    (chess.ROOK, chess.WHITE): "♖",
    (chess.QUEEN, chess.WHITE): "♕",
    (chess.KING, chess.WHITE): "♔",
    (chess.PAWN, chess.BLACK): "♟",
    (chess.KNIGHT, chess.BLACK): "♞",
    (chess.BISHOP, chess.BLACK): "♝",
    (chess.ROOK, chess.BLACK): "♜",
    (chess.QUEEN, chess.BLACK): "♛",
    (chess.KING, chess.BLACK): "♚",
}

PALETTE_ITEMS = [
    chess.Piece(chess.KING, chess.WHITE),
    chess.Piece(chess.QUEEN, chess.WHITE),
    chess.Piece(chess.ROOK, chess.WHITE),
    chess.Piece(chess.BISHOP, chess.WHITE),
    chess.Piece(chess.KNIGHT, chess.WHITE),
    chess.Piece(chess.PAWN, chess.WHITE),
    chess.Piece(chess.KING, chess.BLACK),
    chess.Piece(chess.QUEEN, chess.BLACK),
    chess.Piece(chess.ROOK, chess.BLACK),
    chess.Piece(chess.BISHOP, chess.BLACK),
    chess.Piece(chess.KNIGHT, chess.BLACK),
    chess.Piece(chess.PAWN, chess.BLACK),
]

palette_rects = []


# ============================================================
# GHIM CỬA SỔ / ALWAYS ON TOP - NATIVE WIN32 V6
# ============================================================
PIN_HWND = None


def refresh_pin_hwnd():
    global PIN_HWND

    try:
        hwnd = pygame.display.get_wm_info().get("window")
        if hwnd:
            PIN_HWND = hwnd
            return hwnd
    except Exception:
        pass

    return PIN_HWND


def native_make_topmost():
    hwnd = PIN_HWND or refresh_pin_hwnd()
    if not hwnd:
        return False

    try:
        if PYWIN32_OK:
            # TOOLWINDOW giúp cửa sổ hoạt động giống overlay/tool palette hơn.
            exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            exstyle |= win32con.WS_EX_TOPMOST
            exstyle |= win32con.WS_EX_TOOLWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)

            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_SHOWWINDOW
                | win32con.SWP_FRAMECHANGED
            )
            return True

        # Fallback nếu chưa cài pywin32
        user32 = ctypes.windll.user32

        HWND_TOPMOST = -1
        GWL_EXSTYLE = -20
        WS_EX_TOPMOST = 0x00000008
        WS_EX_TOOLWINDOW = 0x00000080

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        SWP_FRAMECHANGED = 0x0020

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            get_long = user32.GetWindowLongPtrW
            set_long = user32.SetWindowLongPtrW
        else:
            get_long = user32.GetWindowLongW
            set_long = user32.SetWindowLongW

        style = get_long(hwnd, GWL_EXSTYLE)
        style |= WS_EX_TOPMOST | WS_EX_TOOLWINDOW
        set_long(hwnd, GWL_EXSTYLE, style)

        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            | SWP_SHOWWINDOW | SWP_FRAMECHANGED
        )
        return True

    except Exception as e:
        print("Lỗi native topmost:", e)
        return False


def native_remove_topmost():
    hwnd = PIN_HWND or refresh_pin_hwnd()
    if not hwnd:
        return False

    try:
        if PYWIN32_OK:
            exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            exstyle &= ~win32con.WS_EX_TOPMOST
            exstyle &= ~win32con.WS_EX_TOOLWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)

            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_SHOWWINDOW
                | win32con.SWP_FRAMECHANGED
            )
            return True

        user32 = ctypes.windll.user32
        user32.SetWindowPos(
            hwnd, -2, 0, 0, 0, 0,
            0x0002 | 0x0001 | 0x0010 | 0x0040
        )
        return True

    except Exception:
        return False


def pin_worker():
    # Không ép ghim liên tục nữa để tránh tốn CPU / giật app.
    # Giữ hàm để tương thích với code cũ.
    return


def ensure_pin_thread():
    # Không cần thread nền cho chế độ ghim mới.
    return


def set_window_pinned(pinned):
    global WINDOW_PINNED

    refresh_pin_hwnd()
    WINDOW_PINNED = bool(pinned)

    if WINDOW_PINNED:
        native_make_topmost()
        print("Đã bật GHIM NATIVE WIN32.")
        if not PYWIN32_OK:
            print("Khuyến nghị cài pywin32: pip install pywin32")
    else:
        native_remove_topmost()
        print("Đã bỏ ghim bàn cờ.")


def toggle_window_pin():
    set_window_pinned(not WINDOW_PINNED)


def keep_window_on_top():
    # Không gọi Win32 mỗi frame nữa.
    return


def restore_pin_after_resize():
    refresh_pin_hwnd()

    if WINDOW_PINNED:
        pygame.time.delay(50)
        native_make_topmost()


def restore_pin_on_window_event():
    if WINDOW_PINNED:
        refresh_pin_hwnd()
        native_make_topmost()




def save_overlay_region():
    r"""Lưu tọa độ vùng bàn cờ F2 vào C:\duc\chess_board_region.json."""
    if OVERLAY_BOARD_REGION is None:
        return

    try:
        os.makedirs(COORD_DIR, exist_ok=True)

        left, top, width, height = OVERLAY_BOARD_REGION
        data = {
            "left": int(left),
            "top": int(top),
            "width": int(width),
            "height": int(height)
        }

        with open(COORD_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("[F2] Đã lưu tọa độ:", COORD_FILE)

    except Exception as e:
        print("[F2] Không lưu được tọa độ:", e)


def load_overlay_region():
    """Tự đọc lại tọa độ vùng bàn cờ đã lưu khi mở tool."""
    global OVERLAY_BOARD_REGION

    try:
        if not os.path.exists(COORD_FILE):
            return False

        with open(COORD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        left = int(data["left"])
        top = int(data["top"])
        width = int(data["width"])
        height = int(data["height"])

        if width < 80 or height < 80:
            return False

        OVERLAY_BOARD_REGION = (left, top, width, height)

        print("")
        print("==============================================")
        print("[AUTO] ĐÃ TẢI TỌA ĐỘ BÀN CỜ")
        print("File :", COORD_FILE)
        print(f"X    : {left}")
        print(f"Y    : {top}")
        print(f"SIZE : {width} x {height}")
        print("==============================================")

        return True

    except Exception as e:
        print("[AUTO] Không đọc được file tọa độ:", e)
        return False


# ============================================================
# F2 EXTERNAL BOARD ARROW OVERLAY
# ============================================================
def select_overlay_board_region():
    global OVERLAY_BOARD_REGION, WINDOW_PINNED, EXTERNAL_BOARD_HWND

    was_pinned = WINDOW_PINNED
    restored = False

    try:
        # QUAN TRỌNG:
        # Tạm tắt trạng thái ghim thật sự, nếu không WINDOWFOCUSLOST
        # sẽ ghim DUCTOOL trở lại và che màn hình khoanh vùng.
        WINDOW_PINNED = False

        if was_pinned:
            native_remove_topmost()

        # Ẩn DUCTOOL hoàn toàn trước khi chụp.
        pygame.display.iconify()
        pygame.event.pump()
        time.sleep(0.45)

        shot = pyautogui.screenshot()

        # Hiện giao diện toàn màn hình để kéo chọn vùng.
        box = select_screen_region(shot)

        # Khôi phục DUCTOOL ngay sau khi chọn/hủy.
        restore_ductool_window(was_pinned)
        restored = True
        WINDOW_PINNED = was_pinned

        if box is None:
            print("[F2] Đã hủy khoanh vùng.")
            return

        left, top, right, bottom = box

        # Giữ nguyên đúng vùng người dùng kéo, không tự ép từ góc trái.
        width = right - left
        height = bottom - top

        if width < 80 or height < 80:
            print("[F2] Vùng chọn quá nhỏ.")
            return

        # Bàn cờ thường vuông. Lấy vùng vuông nằm giữa phần đã khoanh
        # để tránh lệch nếu tay kéo hơi dư.
        side = min(width, height)
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        board_left = int(cx - side / 2)
        board_top = int(cy - side / 2)

        OVERLAY_BOARD_REGION = (board_left, board_top, side, side)
        save_overlay_region()

        # Ghi nhớ cửa sổ thật nằm dưới tâm bàn cờ để click nền sau này.
        try:
            user32 = ctypes.windll.user32

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT(
                int(board_left + side / 2),
                int(board_top + side / 2)
            )

            hwnd = user32.WindowFromPoint(pt)

            # Lấy cửa sổ gốc/top-level.
            GA_ROOT = 2
            root_hwnd = user32.GetAncestor(hwnd, GA_ROOT)

            EXTERNAL_BOARD_HWND = root_hwnd or hwnd

            print(f"[F2] Target HWND: {EXTERNAL_BOARD_HWND}")

        except Exception as e:
            EXTERNAL_BOARD_HWND = None
            print("[F2] Không lấy được HWND bàn cờ ngoài:", e)

        print("")
        print("==============================================")
        print("[F2] ĐÃ CHỌN VÙNG BÀN CỜ")
        print(f"X      : {board_left}")
        print(f"Y      : {board_top}")
        print(f"SIZE   : {side} x {side}")
        print("==============================================")

        update_external_overlay()

    except Exception as e:
        print("[F2] Lỗi khoanh vùng:", e)

    finally:
        WINDOW_PINNED = was_pinned

        if not restored:
            restore_ductool_window(was_pinned)

        if was_pinned:
            refresh_pin_hwnd()
            native_make_topmost()


def external_square_center(square):
    if OVERLAY_BOARD_REGION is None:
        return None

    left, top, size, _ = OVERLAY_BOARD_REGION
    sq = size / 8.0
    file_idx = chess.square_file(square)
    rank_idx = chess.square_rank(square)

    if BOARD_FLIPPED:
        col = 7 - file_idx
        row = rank_idx
    else:
        col = file_idx
        row = 7 - rank_idx

    return (
        left + (col + 0.5) * sq,
        top + (row + 0.5) * sq
    )


def destroy_external_overlay():
    global OVERLAY_ROOT, OVERLAY_CANVAS
    try:
        if OVERLAY_ROOT is not None:
            OVERLAY_ROOT.destroy()
    except Exception:
        pass
    OVERLAY_ROOT = None
    OVERLAY_CANVAS = None



def click_stockfish_move_on_external_board(move):
    """
    Kéo-thả chậm nước Stockfish trên bàn cờ ngoài bằng Win32 background messages.
    Không di chuyển con trỏ chuột thật.
    """
    if not AUTO_CLICK_STOCKFISH:
        return

    if OVERLAY_BOARD_REGION is None:
        print("[Auto Drag] Chưa chọn vùng bàn cờ bằng F2.")
        return

    if move is None:
        return

    try:
        user32 = ctypes.windll.user32
        hwnd = EXTERNAL_BOARD_HWND

        if not hwnd:
            left, top, size, _ = OVERLAY_BOARD_REGION

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT(int(left + size / 2), int(top + size / 2))
            child = user32.WindowFromPoint(pt)
            GA_ROOT = 2
            hwnd = user32.GetAncestor(child, GA_ROOT) or child

        if not hwnd:
            print("[Auto Drag] Không xác định được cửa sổ bàn cờ ngoài.")
            return

        p_from = external_square_center(move.from_square)
        p_to = external_square_center(move.to_square)
        if not p_from or not p_to:
            return

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        WM_MOUSEMOVE = 0x0200
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202
        MK_LBUTTON = 0x0001

        def make_lparam(x, y):
            return (int(y) << 16) | (int(x) & 0xFFFF)

        def screen_to_client(screen_x, screen_y):
            pt = POINT(int(screen_x), int(screen_y))
            if not user32.ScreenToClient(hwnd, ctypes.byref(pt)):
                raise RuntimeError("ScreenToClient thất bại")
            return pt.x, pt.y

        sx, sy = screen_to_client(*p_from)
        ex, ey = screen_to_client(*p_to)

        user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, make_lparam(sx, sy))
        time.sleep(0.03)

        user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, make_lparam(sx, sy))
        time.sleep(STOCKFISH_DRAG_START_HOLD)

        steps = max(2, int(STOCKFISH_DRAG_STEPS))
        duration = max(0.05, float(STOCKFISH_DRAG_DURATION))
        step_delay = duration / steps

        for i in range(1, steps + 1):
            t = i / steps
            smooth = t * t * (3.0 - 2.0 * t)
            cx = int(sx + (ex - sx) * smooth)
            cy = int(sy + (ey - sy) * smooth)

            user32.PostMessageW(
                hwnd, WM_MOUSEMOVE, MK_LBUTTON, make_lparam(cx, cy)
            )
            time.sleep(step_delay)

        user32.PostMessageW(hwnd, WM_MOUSEMOVE, MK_LBUTTON, make_lparam(ex, ey))
        time.sleep(STOCKFISH_DRAG_END_HOLD)
        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, make_lparam(ex, ey))

        print(
            f"[Background Drag] Stockfish: "
            f"{chess.square_name(move.from_square)} -> "
            f"{chess.square_name(move.to_square)} | "
            f"{STOCKFISH_DRAG_DURATION:.2f}s / {steps} bước"
        )

    except Exception as e:
        print("[Background Drag] Lỗi:", e)



def update_external_overlay():
    """
    Không vẽ mũi tên trên bàn cờ ngoài nữa.
    F2 chỉ còn dùng để chọn/lưu vùng cho chức năng click nền.
    """
    destroy_external_overlay()
    return


def pump_external_overlay():
    return


def screen_to_square(x, y):
    file = x // SQ
    rank = y // SQ

    if not BOARD_FLIPPED:
        board_file = file
        board_rank = 7 - rank
    else:
        board_file = 7 - file
        board_rank = rank

    return chess.square(board_file, board_rank)


def inside_board(pos):
    x, y = pos
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


# ============================================================
# DRAW
# ============================================================

def square_center(square):
    x, y = square_to_screen(square)
    return x + SQ // 2, y + SQ // 2


def draw_move_arrow(move, color):
    """
    Vẽ mũi tên từ ô đi -> ô đến.
    Tự co giãn theo kích thước bàn cờ và tự đúng khi lật bàn.
    """
    if move is None:
        return

    start = square_center(move.from_square)
    end = square_center(move.to_square)

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = (dx * dx + dy * dy) ** 0.5

    if length <= 1:
        return

    # Rút ngắn hai đầu để mũi tên không đè kín quân.
    ux = dx / length
    uy = dy / length

    pad = max(10, int(SQ * 0.18))
    sx = start[0] + ux * pad
    sy = start[1] + uy * pad
    ex = end[0] - ux * pad
    ey = end[1] - uy * pad

    line_width = max(3, int(SQ * 0.07))
    head_len = max(10, int(SQ * 0.20))
    head_w = max(7, int(SQ * 0.12))

    pygame.draw.line(
        screen,
        color,
        (int(sx), int(sy)),
        (int(ex), int(ey)),
        line_width
    )

    # Vector vuông góc để dựng đầu mũi tên.
    px = -uy
    py = ux

    bx = ex - ux * head_len
    by = ey - uy * head_len

    p1 = (int(ex), int(ey))
    p2 = (int(bx + px * head_w), int(by + py * head_w))
    p3 = (int(bx - px * head_w), int(by - py * head_w))

    pygame.draw.polygon(screen, color, [p1, p2, p3])


def draw_last_move_arrows():
    # Vẽ sau ô bàn nhưng trước quân cờ.
    if last_player_move is not None:
        draw_move_arrow(last_player_move, PLAYER_ARROW)

    if last_stockfish_move is not None:
        draw_move_arrow(last_stockfish_move, STOCKFISH_ARROW)


def draw_board():
    for y in range(8):
        for x in range(8):
            color = LIGHT if (x + y) % 2 == 0 else DARK
            pygame.draw.rect(screen, color, (x * SQ, y * SQ, SQ, SQ))


def draw_highlights():
    if setup_mode:
        return

    if last_move:
        for square in [last_move.from_square, last_move.to_square]:
            x, y = square_to_screen(square)
            s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            s.fill((*LAST, 120))
            screen.blit(s, (x, y))

    if selected_square is not None:
        x, y = square_to_screen(selected_square)

        s = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
        s.fill((*SELECT, 130))
        screen.blit(s, (x, y))

        for move in board.legal_moves:
            if move.from_square == selected_square:
                mx, my = square_to_screen(move.to_square)
                pygame.draw.circle(
                    screen,
                    MOVE_DOT,
                    (mx + SQ // 2, my + SQ // 2),
                    9
                )


def render_piece(symbol, font, is_white, center, size_shift=2):
    # Quan trang: mau sang + vien toi
    # Quan den: mau toi + vien sang
    fill = (255, 255, 255) if is_white else (35, 35, 35)
    outline = (15, 15, 15) if is_white else (225, 225, 225)

    # Ve vien bang cach blit lech xung quanh
    outline_img = font.render(symbol, True, outline)
    for dx, dy in [
        (-size_shift, 0), (size_shift, 0),
        (0, -size_shift), (0, size_shift),
        (-size_shift, -size_shift), (size_shift, -size_shift),
        (-size_shift, size_shift), (size_shift, size_shift)
    ]:
        r = outline_img.get_rect(center=(center[0] + dx, center[1] + dy))
        screen.blit(outline_img, r)

    img = font.render(symbol, True, fill)
    rect = img.get_rect(center=center)
    screen.blit(img, rect)



def square_to_screen(square):
    """Đổi chess square -> tọa độ pixel góc trên-trái trên bàn cờ mini."""
    file_idx = chess.square_file(square)
    rank_idx = chess.square_rank(square)

    if BOARD_FLIPPED:
        col = 7 - file_idx
        row = rank_idx
    else:
        col = file_idx
        row = 7 - rank_idx

    return col * SQ, row * SQ


def draw_pieces():
    for square in chess.SQUARES:
        piece = board.piece_at(square)

        if not piece:
            continue

        # while dragging an existing board piece, hide original
        if setup_mode and dragging and drag_from_square == square:
            continue

        symbol = PIECES[(piece.piece_type, piece.color)]
        x, y = square_to_screen(square)

        render_piece(
            symbol,
            piece_font,
            piece.color == chess.WHITE,
            (x + SQ // 2, y + SQ // 2),
            2
        )

def draw_panel():
    global palette_rects

    if is_mini_mode():
        palette_rects = []
        return

    pygame.draw.rect(screen, PANEL, (BOARD_SIZE, 0, SIDE_W, HEIGHT))
    pygame.draw.line(screen, BORDER, (BOARD_SIZE, 0), (BOARD_SIZE, HEIGHT), 2)

    title = title_font.render("QUÂN CỜ THIẾT LẬP", True, TEXT)
    screen.blit(title, (BOARD_SIZE + 20, 18))

    help1 = small_font.render("Kéo quân vào bàn cờ", True, TEXT)
    help2 = small_font.render("Kéo quân ra ngoài để xóa", True, TEXT)
    screen.blit(help1, (BOARD_SIZE + 20, 48))
    screen.blit(help2, (BOARD_SIZE + 20, 70))

    palette_rects = []

    start_x = BOARD_SIZE + 25
    start_y = max(100, int(SQ * 1.15))
    cell_w = max(72, min(95, SIDE_W // 2 - 35))
    cell_h = max(58, int(SQ * 0.82))

    for i, piece in enumerate(PALETTE_ITEMS):
        col = i % 2
        row = i // 2

        rect = pygame.Rect(
            start_x + col * (cell_w + 15),
            start_y + row * cell_h,
            cell_w,
            max(50, int(cell_h * 0.82))
        )

        pygame.draw.rect(screen, PANEL2, rect, border_radius=8)
        pygame.draw.rect(screen, BORDER, rect, width=1, border_radius=8)

        symbol = PIECES[(piece.piece_type, piece.color)]

        render_piece(
            symbol,
            mini_font,
            piece.color == chess.WHITE,
            rect.center,
            1
        )

        palette_rects.append((rect, piece))

    y = min(BOARD_SIZE - 120, start_y + 6 * cell_h + 20)

    turn_text = "LƯỢT TRẮNG" if board.turn == chess.WHITE else "LƯỢT ĐEN"
    screen.blit(
        status_font.render(turn_text, True, WARN if setup_mode else TEXT),
        (BOARD_SIZE + 20, y)
    )

    info = [
        "F1: Bật/Tắt thiết lập",
        "F2: Chọn vùng cho kéo thả",
        "F3: Đổi bên đi trước",
        "F4: Xóa bàn cờ",
        "F5: Khoanh vùng -> Gemini",
        "F6: Ghim/Bỏ ghim cửa sổ",
        "F7: Kéo thả Stockfish",
        "F10: Đổi delay kéo",
        "Đường xanh: nước của bạn",
        "Đường cam: Stockfish",
        "R : Ván mới",
"E : Hoàn tác",
        "1 : Chơi quân Trắng",
        "2 : Chơi quân Đen",
        "ESC: Thoát",
    ]

    y += 35
    for line in info:
        screen.blit(
            small_font.render(line, True, TEXT),
            (BOARD_SIZE + 20, y)
        )
        y += 22


def draw_drag_piece():
    if not dragging or drag_piece is None:
        return

    symbol = PIECES[(drag_piece.piece_type, drag_piece.color)]

    render_piece(
        symbol,
        piece_font,
        drag_piece.color == chess.WHITE,
        drag_mouse,
        2
    )


def get_status():
    if setup_mode:
        if board.is_valid():
            return "CHẾ ĐỘ THIẾT LẬP - vị trí hợp lệ"
        return "CHẾ ĐỘ THIẾT LẬP - vị trí chưa hợp lệ"

    if not board.is_valid():
        return "Vị trí không hợp lệ - nhấn F1 để chỉnh"

    if board.is_checkmate():
        return "Chiếu hết - Stockfish thắng" if board.turn == PLAYER_COLOR else "Chiếu hết - Bạn thắng"

    if board.is_stalemate():
        return "Hòa - Bí"

    if board.is_insufficient_material():
        return "Hòa - Không đủ quân"

    if board.is_check():
        return "Chiếu!"

    return "Lượt của bạn" if board.turn == PLAYER_COLOR else "Lượt Stockfish"


def draw_status():
    if is_mini_mode():
        return
    pygame.draw.rect(screen, BG, (0, BOARD_SIZE, BOARD_SIZE, HEIGHT - BOARD_SIZE))
    color = WARN if setup_mode or not board.is_valid() else TEXT
    screen.blit(status_font.render(get_status(), True, color), (12, BOARD_SIZE + 8))


def redraw():
    screen.fill(BG)
    draw_board()
    draw_highlights()
    draw_last_move_arrows()
    draw_pieces()
    draw_panel()
    draw_status()
    draw_drag_piece()
    pygame.display.flip()


# ============================================================
# STOCKFISH
# ============================================================
def stockfish_move():
    global last_move, last_stockfish_move

    if setup_mode or not board.is_valid() or board.is_game_over():
        return

    if board.turn == PLAYER_COLOR:
        return

    try:
        result = engine.play(board, chess.engine.Limit(time=0.18))
        last_move = result.move
        last_stockfish_move = result.move

        # Click trực tiếp nước Stockfish lên bàn cờ ngoài đã chọn bằng F2.
        click_stockfish_move_on_external_board(result.move)

        board.push(result.move)
        update_external_overlay()
        print("Stockfish:", result.move)
    except Exception as e:
        print("Lỗi Stockfish:", e)


# ============================================================
# NORMAL PLAY
# ============================================================
def player_click(pos):
    global selected_square, last_move, last_player_move

    if setup_mode or not board.is_valid() or board.is_game_over():
        return

    if board.turn != PLAYER_COLOR:
        return

    if not inside_board(pos):
        return

    square = screen_to_square(*pos)
    piece = board.piece_at(square)

    if selected_square is None:
        if piece and piece.color == PLAYER_COLOR:
            selected_square = square
        return

    if piece and piece.color == PLAYER_COLOR:
        selected_square = square
        return

    move = chess.Move(selected_square, square)
    selected_piece = board.piece_at(selected_square)

    if (
        selected_piece
        and selected_piece.piece_type == chess.PAWN
        and chess.square_rank(square) in [0, 7]
    ):
        move = chess.Move(selected_square, square, promotion=chess.QUEEN)

    if move in board.legal_moves:
        last_move = move
        last_player_move = move
        board.push(move)
        update_external_overlay()
        selected_square = None
        redraw()
        stockfish_move()
    else:
        selected_square = None


# ============================================================
# DRAG & DROP SETUP
# ============================================================
def start_drag(pos):
    global dragging, drag_piece, drag_from_square, drag_from_palette, drag_mouse

    if not setup_mode:
        return False

    drag_mouse = pos

    # From board
    if inside_board(pos):
        sq = screen_to_square(*pos)
        piece = board.piece_at(sq)

        if piece:
            dragging = True
            drag_piece = piece
            drag_from_square = sq
            drag_from_palette = False
            return True

    # From palette
    for rect, piece in palette_rects:
        if rect.collidepoint(pos):
            dragging = True
            drag_piece = piece
            drag_from_square = None
            drag_from_palette = True
            return True

    return False


def update_drag(pos):
    global drag_mouse
    if dragging:
        drag_mouse = pos


def finish_drag(pos):
    global dragging, drag_piece, drag_from_square, drag_from_palette
    global selected_square, last_move, last_player_move, last_stockfish_move

    if not dragging:
        return

    # Dragging an existing board piece:
    # remove it from origin first, then either place at destination
    # or leave removed if dropped outside board.
    if drag_from_square is not None:
        board.remove_piece_at(drag_from_square)

    if inside_board(pos):
        target = screen_to_square(*pos)
        board.set_piece_at(target, drag_piece)

    # If dropped outside board, an existing board piece stays removed.
    # Palette pieces simply disappear if dropped outside.

    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = max(1, board.fullmove_number)

    selected_square = None
    last_move = None
    last_player_move = None
    last_stockfish_move = None

    dragging = False
    drag_piece = None
    drag_from_square = None
    drag_from_palette = False



# ============================================================
# GEMINI SCREENSHOT IMPORT
# ============================================================
def extract_board_fen(text):
    """
    Extract only the piece-placement field of a FEN.
    Example:
    rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
    """
    if not text:
        return None

    text = text.strip()

    # Remove common markdown/code fences.
    text = text.replace("```fen", "").replace("```", "").strip()

    pattern = r'([prnbqkPRNBQK1-8]+(?:/[prnbqkPRNBQK1-8]+){7})'
    match = re.search(pattern, text)

    return match.group(1) if match else None



def select_screen_region(screenshot):
    """
    Hiển thị ảnh chụp toàn màn hình và cho người dùng kéo chuột
    khoanh vùng bàn cờ. ESC hoặc chuột phải = hủy.
    Trả về (left, top, right, bottom) hoặc None.
    """
    result = {"box": None}
    start = {"x": 0, "y": 0}
    rect = {"id": None}

    root = tk.Tk()
    root.title("DUCTOOL - Khoanh vùng bàn cờ")
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    sw, sh = screenshot.size
    root.geometry(f"{sw}x{sh}+0+0")

    canvas = tk.Canvas(
        root,
        width=sw,
        height=sh,
        highlightthickness=0,
        cursor="cross"
    )
    canvas.pack(fill="both", expand=True)

    photo = ImageTk.PhotoImage(screenshot)
    canvas._photo = photo
    canvas.create_image(0, 0, image=photo, anchor="nw")

    # Lớp tối mờ + hướng dẫn. Ảnh gốc vẫn đủ rõ để khoanh bàn cờ.
    canvas.create_rectangle(
        0, 0, sw, 42,
        fill="black",
        outline=""
    )
    canvas.create_text(
        sw // 2,
        21,
        text="KÉO CHUỘT KHOANH VÙNG BÀN CỜ  •  ESC / CHUỘT PHẢI: HỦY",
        fill="white",
        font=("Segoe UI", 13, "bold")
    )

    def on_down(event):
        start["x"], start["y"] = event.x, event.y
        if rect["id"] is not None:
            canvas.delete(rect["id"])

        rect["id"] = canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="red",
            width=3
        )

    def on_move(event):
        if rect["id"] is not None:
            canvas.coords(
                rect["id"],
                start["x"], start["y"],
                event.x, event.y
            )

    def on_up(event):
        x1, y1 = start["x"], start["y"]
        x2, y2 = event.x, event.y

        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))

        # Chống click nhầm / vùng quá nhỏ.
        if right - left < 80 or bottom - top < 80:
            return

        result["box"] = (left, top, right, bottom)
        root.destroy()

    def cancel(event=None):
        result["box"] = None
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_down)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_up)
    canvas.bind("<ButtonPress-3>", cancel)
    root.bind("<Escape>", cancel)

    root.focus_force()
    root.mainloop()

    return result["box"]


def restore_ductool_window(was_pinned=False):
    """
    Hiện lại cửa sổ DUCTOOL ngay sau khi khoanh vùng,
    trước khi chờ Gemini xử lý.
    """
    global screen

    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("DUCTOOL Hỗ Trợ Cờ Vua")
        refresh_pin_hwnd()

        hwnd = refresh_pin_hwnd()
        if hwnd:
            try:
                if PYWIN32_OK:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                else:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            except Exception:
                pass

        if was_pinned:
            native_make_topmost()

        redraw()
        pygame.display.flip()
        pygame.event.pump()

    except Exception as e:
        print("[F5] Không khôi phục được cửa sổ:", e)


def import_board_from_gemini():
    global board, selected_square, last_move, last_player_move, last_stockfish_move
    global WINDOW_PINNED

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("")
        print("==============================================")
        print("CHƯA CÓ GEMINI_API_KEY")
        print("CMD:")
        print('setx GEMINI_API_KEY "YOUR_API_KEY"')
        print("Sau đó đóng CMD và mở lại.")
        print("==============================================")
        return

    screenshot_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "_gemini_chess_capture.png"
    )

    was_pinned = WINDOW_PINNED
    restored = False

    try:
        print("")
        print("[F5] Chuẩn bị khoanh vùng bàn cờ...")

        # Tạm tắt ghim để DUCTOOL không bật trở lại đè lên màn hình khoanh vùng.
        WINDOW_PINNED = False
        native_remove_topmost()

        # Ẩn DUCTOOL, chụp màn hình phía sau.
        pygame.display.iconify()
        pygame.event.pump()
        time.sleep(0.45)

        full_shot = pyautogui.screenshot()

        print("[F5] Kéo chuột khoanh đúng vùng bàn cờ.")
        box = select_screen_region(full_shot)

        # QUAN TRỌNG: hiện DUCTOOL lại NGAY sau khi thả chuột,
        # không bắt người dùng chờ Gemini với cửa sổ bị ẩn.
        restore_ductool_window(was_pinned)
        restored = True
        WINDOW_PINNED = was_pinned

        if box is None:
            print("[F5] Đã hủy khoanh vùng.")
            return

        left, top, right, bottom = box
        cropped = full_shot.crop((left, top, right, bottom))
        cropped.save(screenshot_path)

        print(
            f"[F5] Đã chọn vùng: "
            f"{right-left}x{bottom-top} tại ({left}, {top})"
        )
        print("[F5] Đang gửi vùng bàn cờ sang Gemini...")

        client = genai.Client(api_key=api_key)
        image = Image.open(screenshot_path)

        prompt = """
This image is a cropped screenshot containing a chessboard.

Identify every chess piece and its square.

Return ONLY the board-position field of FEN:
exactly 8 ranks separated by /, from rank 8 to rank 1.

Use:
P N B R Q K for White pieces
p n b r q k for Black pieces
digits 1-8 for consecutive empty squares

Do NOT return side to move, castling, en-passant, move counters,
markdown, explanations, labels, or other text.

If coordinate labels are visible, use them to determine orientation.
If the board is flipped, still output standard chess FEN coordinates.

Example:
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image]
        )

        raw = response.text or ""
        print("[Gemini]", raw)

        board_fen = extract_board_fen(raw)

        if not board_fen:
            print("[F5] Gemini không trả về FEN hợp lệ.")
            return

        temp = chess.Board(None)
        temp.set_board_fen(board_fen)

        current_turn = board.turn

        board = chess.Board(None)
        board.set_board_fen(board_fen)
        board.turn = current_turn
        board.castling_rights = chess.BB_EMPTY
        board.ep_square = None
        board.halfmove_clock = 0
        board.fullmove_number = 1

        selected_square = None
        last_move = None
        last_player_move = None
        last_stockfish_move = None

        print("[F5] Đã sắp xếp lại bàn cờ.")
        print("Board FEN:", board.board_fen())

        redraw()
        pygame.display.flip()

    except Exception as e:
        print("[F5] Lỗi Gemini / khoanh vùng:", e)

    finally:
        WINDOW_PINNED = was_pinned

        # Dù lỗi/cancel ở bước nào cũng bắt buộc hiện DUCTOOL trở lại.
        if not restored:
            restore_ductool_window(was_pinned)

        if was_pinned:
            refresh_pin_hwnd()
            native_make_topmost()


# ============================================================
# F10 - CHỈNH DELAY KÉO STOCKFISH
# ============================================================
def cycle_stockfish_drag_delay():
    global STOCKFISH_DRAG_DURATION, DRAG_DELAY_INDEX

    presets = DRAG_DELAY_PRESETS

    # Tự đồng bộ index với duration hiện tại nếu có thay đổi config thủ công.
    try:
        current_index = presets.index(round(float(STOCKFISH_DRAG_DURATION), 2))
    except Exception:
        current_index = int(DRAG_DELAY_INDEX) if 0 <= int(DRAG_DELAY_INDEX) < len(presets) else 0

    DRAG_DELAY_INDEX = (current_index + 1) % len(presets)
    STOCKFISH_DRAG_DURATION = presets[DRAG_DELAY_INDEX]

    print("")
    print("==============================================")
    print("[F10] DELAY KÉO STOCKFISH")
    print(f"Thời gian kéo: {STOCKFISH_DRAG_DURATION:.2f} giây")
    print(f"Mức: {DRAG_DELAY_INDEX + 1}/{len(presets)}")
    print("==============================================")
    redraw()


# ============================================================
# CONTROLS
# ============================================================
def toggle_setup():
    global setup_mode, selected_square, last_move
    setup_mode = not setup_mode
    selected_square = None
    last_move = None

    if not setup_mode:
        if not board.is_valid():
            print("Vị trí chưa hợp lệ.")
            print("Cần có đúng 1 Vua Trắng và 1 Vua Đen.")
            return

        print("Thiết lập hợp lệ")
        print("FEN:", board.fen())

        if board.turn != PLAYER_COLOR:
            stockfish_move()


def clear_board():
    global board, selected_square, last_move, last_player_move, last_stockfish_move
    board = chess.Board(None)
    board.turn = chess.WHITE
    selected_square = None
    last_move = None

    update_external_overlay()


def new_game():
    global board, selected_square, last_move, last_player_move, last_stockfish_move
    board = chess.Board()
    selected_square = None
    last_move = None
    last_player_move = None
    last_stockfish_move = None

    if PLAYER_COLOR == chess.BLACK:
        stockfish_move()

    update_external_overlay()


def undo_move():
    global last_move, selected_square, last_player_move, last_stockfish_move

    if setup_mode:
        return

    selected_square = None

    if board.move_stack:
        board.pop()

    if board.move_stack:
        board.pop()

    last_move = board.peek() if board.move_stack else None

    # Sau hoàn tác, dựng lại 2 mũi tên gần nhất theo màu người chơi.
    last_player_move = None
    last_stockfish_move = None

    temp = chess.Board()
    for mv in board.move_stack:
        mover_color = temp.turn

        if mover_color == PLAYER_COLOR:
            last_player_move = mv
        else:
            last_stockfish_move = mv

        temp.push(mv)

    update_external_overlay()

# ============================================================
# MAIN
# ============================================================
def main():
    global PLAYER_COLOR, BOARD_FLIPPED, PIN_THREAD_STOP, AUTO_CLICK_STOCKFISH

    load_overlay_region()
    print(
        f"[DRAG CONFIG] duration={STOCKFISH_DRAG_DURATION:.2f}s | "
        f"steps={STOCKFISH_DRAG_STEPS} | "
        f"start_hold={STOCKFISH_DRAG_START_HOLD:.2f}s | "
        f"end_hold={STOCKFISH_DRAG_END_HOLD:.2f}s"
    )

    refresh_pin_hwnd()

    print("""
==================================================
      DUCTOOL HỖ TRỢ CỜ VUA - THIẾT LẬP KÉO THẢ
==================================================

F1 = Bật / tắt chế độ thiết lập
F2 = Chọn vùng bàn cờ ngoài -> dùng cho kéo thả
F3 = Đổi bên đi trước
F4 = Xóa toàn bộ bàn cờ
F5 = Khoanh vùng bàn cờ -> Gemini -> sắp xếp bàn cờ
F6 = Ghim / bỏ ghim cửa sổ
F7 = Bật / tắt kéo thả Stockfish
F10 = Đổi delay kéo giữa 2 ô

+  = Phóng to bàn cờ
-  = Thu nhỏ bàn cờ
   (Dưới 560px: tự chuyển sang chế độ MINI chỉ còn bàn cờ)

1  = Chơi quân Trắng
2  = Chơi quân Đen

R  = Ván mới
E  = Hoàn tác
ESC = Thoát

CHẾ ĐỘ THIẾT LẬP:
- Kéo quân từ bảng bên phải vào bàn cờ.
- Kéo quân đang có sang ô khác để di chuyển.
- Kéo quân ra ngoài bàn cờ để xóa.
- Chuột phải vào quân để xóa nhanh.
==================================================
""")

    clock = pygame.time.Clock()
    running = True

    while running:
        redraw()
        pump_external_overlay()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.WINDOWFOCUSLOST:
                restore_pin_on_window_event()

            elif event.type == pygame.WINDOWSHOWN:
                restore_pin_on_window_event()

            elif event.type == pygame.WINDOWEXPOSED:
                restore_pin_on_window_event()

            elif event.type == pygame.WINDOWRESIZED:
                restore_pin_on_window_event()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if setup_mode:
                        start_drag(event.pos)
                    else:
                        player_click(event.pos)

                elif event.button == 3 and setup_mode and inside_board(event.pos):
                    sq = screen_to_square(*event.pos)
                    board.remove_piece_at(sq)

            elif event.type == pygame.MOUSEWHEEL:
                keys = pygame.key.get_mods()
                if keys & pygame.KMOD_CTRL:
                    if event.y > 0:
                        apply_board_size(BOARD_SIZE + RESIZE_STEP)
                    elif event.y < 0:
                        apply_board_size(BOARD_SIZE - RESIZE_STEP)

            elif event.type == pygame.MOUSEMOTION:
                update_drag(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and setup_mode:
                    finish_drag(event.pos)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_F2:
                    select_overlay_board_region()

                elif event.key == pygame.K_F1:
                    toggle_setup()

                elif event.key == pygame.K_F3 and setup_mode:
                    board.turn = not board.turn

                elif event.key == pygame.K_F4 and setup_mode:
                    clear_board()

                elif event.key == pygame.K_F5:
                    import_board_from_gemini()

                elif event.key == pygame.K_F6:
                    toggle_window_pin()

                elif event.key == pygame.K_F7:
                    AUTO_CLICK_STOCKFISH = not AUTO_CLICK_STOCKFISH
                    print(
                        "[F7] Auto drag Stockfish:",
                        "BẬT" if AUTO_CLICK_STOCKFISH else "TẮT"
                    )

                elif event.key == pygame.K_F10:
                    cycle_stockfish_drag_delay()

                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    apply_board_size(BOARD_SIZE + RESIZE_STEP)

                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    apply_board_size(BOARD_SIZE - RESIZE_STEP)

                elif not setup_mode:
                    if event.key == pygame.K_1:
                        PLAYER_COLOR = chess.WHITE
                        BOARD_FLIPPED = True
                        new_game()

                    elif event.key == pygame.K_2:
                        PLAYER_COLOR = chess.BLACK
                        BOARD_FLIPPED = False
                        new_game()

                    elif event.key == pygame.K_r:
                        # R luôn reset về mặc định: người chơi cầm quân Trắng.
                        PLAYER_COLOR = chess.WHITE
                        BOARD_FLIPPED = True
                        new_game()

                    elif event.key == pygame.K_e:
                        undo_move()

        clock.tick(60)

    PIN_THREAD_STOP = True
    destroy_external_overlay()
    engine.quit()
    pygame.quit()


if __name__ == "__main__":
    main()
