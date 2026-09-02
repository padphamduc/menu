# ============================================================
# MỞ SEB_VIP
# - Nếu đã có: mở trực tiếp.
# - Nếu chưa có: chọn MEGA / Google Drive / GitHub -> tải -> giải nén -> mở.
# - Giải nén bằng 7zr.exe chính thức của 7-Zip được bundle trong DucTool.exe.
#   Cách này hỗ trợ archive 7z dùng BCJ2 mà py7zr không hỗ trợ.
# ============================================================

import base64
import html
import http.cookiejar
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from Cryptodome.Cipher import AES
from Cryptodome.Util import Counter


BASE_DIR = Path(r"C:\duc")
INSTALL_DIR = BASE_DIR / "SEB_VIP"
TARGET_EXE = INSTALL_DIR / "Application" / "SafeExamBrowser.exe"
ARCHIVE_PATH = BASE_DIR / "SEB_VIP.7z"
STAGING_DIR = BASE_DIR / "SEB_VIP.__installing__"

MEGA_URL = "https://mega.nz/file/jOogRQ4Z#pzTlDDD6Zqe6uSsrbVa7WMlUKxYczAwuCU0OoHy34FA"
DRIVE_URL = "https://drive.google.com/file/d/1TbSZX4KyPyKIWRSoJbLVJRFRBNimvi1P/view?usp=sharing"
GITHUB_URL = "https://github.com/padphamduc/menu/releases/download/v9.9.9/SEB_VIP.7z"

CHUNK_SIZE = 1024 * 1024
TIMEOUT = 160
DOWNLOAD_THREADS = 16
PROGRESS_REFRESH = 0.40


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
    print(DUC_TOOL_BANNER, flush=True)


def log(message=""):
    print(message, flush=True)


def human_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024


def launch_seb(exe_path):
    exe_path = Path(exe_path)
    if not exe_path.exists():
        raise FileNotFoundError(f"Không tìm thấy: {exe_path}")

    log(f"\nĐang mở: {exe_path}")
    subprocess.Popen(
        [str(exe_path)],
        cwd=str(exe_path.parent),
        close_fds=True,
    )


# ============================================================
# PROGRESS 1 DÒNG
# ============================================================

_progress_last_len = 0


def _render_download_progress(percent=None, downloaded=0, total=0, spinner_index=0,
                              speed_bps=0.0, source_name="SEB_VIP"):
    global _progress_last_len

    frames = "|/-\\"
    frame = frames[spinner_index % len(frames)]
    min_speed = 10 * 1024

    if percent is not None and total > 0:
        percent = max(0.0, min(100.0, float(percent)))
        bar_width = 20
        filled = int(bar_width * percent / 100.0)
        bar = "█" * filled + "░" * (bar_width - filled)

        if speed_bps >= min_speed:
            status = f"{human_size(speed_bps)}/s"
        elif percent >= 100.0:
            status = "Hoàn tất"
        else:
            status = f"{frame} Đang chờ..."

        text = f"{source_name} {percent:5.1f}% [{bar}] {status}"
    else:
        status = f"{human_size(speed_bps)}/s" if speed_bps >= min_speed else f"{frame} Đang kết nối..."
        text = f"{source_name} {status}"

    try:
        columns = shutil.get_terminal_size(fallback=(100, 25)).columns
    except Exception:
        columns = 100
    max_width = max(30, columns - 2)
    if len(text) > max_width:
        text = text[:max_width]

    clear_len = max(_progress_last_len, len(text))
    sys.stdout.write("\r" + (" " * clear_len) + "\r" + text)
    sys.stdout.flush()
    _progress_last_len = len(text)


def _finish_progress_line():
    global _progress_last_len
    if _progress_last_len:
        sys.stdout.write("\n")
        sys.stdout.flush()
    _progress_last_len = 0


def _request_headers(extra=None):
    headers = {
        "User-Agent": "Mozilla/5.0 DucTool-SEB-VIP/2.0",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Connection": "close",
    }
    if extra:
        headers.update(extra)
    return headers


# ============================================================
# CHỌN NGUỒN TẢI
# ============================================================

def choose_download_source():
    log()
    log("Chọn nguồn tải SEB_VIP:")
    log("[1] Download via Mega")
    log("[2] Download via Driver")
    log("[3] Download via Github")

    while True:
        try:
            choice = input("Lựa chọn [1/2/3] (mặc định 1): ").strip() or "1"
        except EOFError:
            choice = "1"

        if choice == "1":
            return "mega"
        if choice == "2":
            return "drive"
        if choice == "3":
            return "github"

        log("Chỉ chọn 1, 2 hoặc 3.")


# ============================================================
# DOWNLOAD HTTP THƯỜNG / GITHUB 16 LUỒNG
# ============================================================

def _probe_range_support(url):
    request = urllib.request.Request(
        url,
        headers=_request_headers({"Range": "bytes=0-0"}),
    )

    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        status = getattr(response, "status", response.getcode())
        content_range = response.headers.get("Content-Range", "")
        content_length = response.headers.get("Content-Length", "0")
        response.read()

        if status == 206 and "/" in content_range:
            try:
                total = int(content_range.rsplit("/", 1)[1])
                if total > 0:
                    return True, total
            except Exception:
                pass

        try:
            total = int(content_length or 0)
        except Exception:
            total = 0

        return False, total


def _stream_response_to_archive(response, total_hint=0, source_name="SEB_VIP"):
    downloaded = 0
    start_time = time.monotonic()
    last_render = 0.0
    spinner_index = 0
    total = int(response.headers.get("Content-Length", "0") or 0) or total_hint

    with open(ARCHIVE_PATH, "wb") as output:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break

            output.write(chunk)
            downloaded += len(chunk)

            now = time.monotonic()
            if now - last_render >= PROGRESS_REFRESH:
                elapsed = max(now - start_time, 0.001)
                speed = downloaded / elapsed
                spinner_index += 1
                _render_download_progress(
                    (downloaded * 100.0 / total) if total > 0 else None,
                    downloaded=downloaded,
                    total=total,
                    spinner_index=spinner_index,
                    speed_bps=speed,
                    source_name=source_name,
                )
                last_render = now

    elapsed = max(time.monotonic() - start_time, 0.001)
    speed = downloaded / elapsed
    _render_download_progress(
        100.0 if total > 0 else None,
        downloaded=downloaded,
        total=total,
        spinner_index=spinner_index + 1,
        speed_bps=speed,
        source_name=source_name,
    )
    _finish_progress_line()


def _download_single_stream(url, total_hint=0, source_name="SEB_VIP"):
    request = urllib.request.Request(url, headers=_request_headers())
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        _stream_response_to_archive(response, total_hint=total_hint, source_name=source_name)


def _download_multi_range(url, total_size, source_name="SEB_VIP"):
    part_dir = BASE_DIR / "SEB_VIP.__parts__"
    if part_dir.exists():
        shutil.rmtree(part_dir, ignore_errors=True)
    part_dir.mkdir(parents=True, exist_ok=True)

    thread_count = min(DOWNLOAD_THREADS, max(1, total_size))
    part_size = (total_size + thread_count - 1) // thread_count

    ranges = []
    for index in range(thread_count):
        start = index * part_size
        if start >= total_size:
            break
        end = min(total_size - 1, start + part_size - 1)
        ranges.append((index, start, end, part_dir / f"part_{index:02d}.bin"))

    thread_count = len(ranges)
    progress_lock = threading.Lock()
    downloaded = 0
    stop_progress = threading.Event()
    start_time = time.monotonic()

    def add_progress(amount):
        nonlocal downloaded
        with progress_lock:
            downloaded += amount

    def worker(index, start, end, part_path):
        expected = end - start + 1
        request = urllib.request.Request(
            url,
            headers=_request_headers({"Range": f"bytes={start}-{end}"}),
        )

        written = 0
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            status = getattr(response, "status", response.getcode())
            if status != 206:
                raise RuntimeError(
                    f"Server không trả HTTP 206 cho phần {index + 1}/{thread_count} (HTTP {status})"
                )

            with open(part_path, "wb") as output:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    output.write(chunk)
                    written += len(chunk)
                    add_progress(len(chunk))

        if written != expected:
            raise RuntimeError(
                f"Phần {index + 1}/{thread_count} thiếu dữ liệu: {written}/{expected} bytes"
            )
        return index

    def progress_loop():
        spinner_index = 0
        samples = [(start_time, 0)]

        while not stop_progress.wait(PROGRESS_REFRESH):
            with progress_lock:
                current_downloaded = downloaded

            now = time.monotonic()
            samples.append((now, current_downloaded))
            cutoff = now - 2.0
            while len(samples) > 2 and samples[1][0] < cutoff:
                samples.pop(0)

            first_time, first_bytes = samples[0]
            dt = max(now - first_time, 0.001)
            speed = max(0, current_downloaded - first_bytes) / dt

            spinner_index += 1
            _render_download_progress(
                current_downloaded * 100.0 / total_size,
                downloaded=current_downloaded,
                total=total_size,
                spinner_index=spinner_index,
                speed_bps=speed,
                source_name=source_name,
            )

    progress_thread = threading.Thread(target=progress_loop, daemon=True)
    progress_thread.start()

    try:
        with ThreadPoolExecutor(max_workers=thread_count, thread_name_prefix="SEBVIP") as pool:
            futures = [pool.submit(worker, *item) for item in ranges]
            for future in as_completed(futures):
                future.result()

        with open(ARCHIVE_PATH, "wb") as output:
            for _index, _start, _end, part_path in ranges:
                with open(part_path, "rb") as source:
                    shutil.copyfileobj(source, output, length=4 * 1024 * 1024)

        actual_size = ARCHIVE_PATH.stat().st_size
        if actual_size != total_size:
            raise RuntimeError(
                f"File sau khi ghép sai dung lượng: {actual_size}/{total_size} bytes"
            )

    finally:
        stop_progress.set()
        progress_thread.join(timeout=1.0)
        shutil.rmtree(part_dir, ignore_errors=True)

    elapsed = max(time.monotonic() - start_time, 0.001)
    speed = total_size / elapsed
    _render_download_progress(
        100.0,
        downloaded=total_size,
        total=total_size,
        spinner_index=0,
        speed_bps=speed,
        source_name=source_name,
    )
    _finish_progress_line()


def download_github():
    _render_download_progress(None, spinner_index=0, source_name="GitHub")
    supports_range, total_size = _probe_range_support(GITHUB_URL)

    global _progress_last_len
    sys.stdout.write("\r" + (" " * _progress_last_len) + "\r")
    sys.stdout.flush()
    _progress_last_len = 0

    if supports_range and total_size > 0:
        _download_multi_range(GITHUB_URL, total_size, source_name="GitHub")
    else:
        _download_single_stream(GITHUB_URL, total_hint=total_size, source_name="GitHub")


# ============================================================
# DOWNLOAD GOOGLE DRIVE
# ============================================================

def _extract_drive_file_id(url):
    match = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)

    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    values = query.get("id")
    if values:
        return values[0]

    raise ValueError("Không lấy được Google Drive file ID.")


def _drive_confirmation_request(opener, file_id):
    direct_url = (
        "https://drive.usercontent.google.com/download"
        f"?id={urllib.parse.quote(file_id)}&export=download&confirm=t"
    )
    request = urllib.request.Request(direct_url, headers=_request_headers())
    response = opener.open(request, timeout=TIMEOUT)

    content_type = (response.headers.get("Content-Type") or "").lower()
    disposition = response.headers.get("Content-Disposition") or ""

    # Bình thường Google trả file trực tiếp.
    if "text/html" not in content_type or disposition:
        return response

    # Nếu Google hiện trang xác nhận file lớn, lấy form + hidden input rồi gọi lại.
    html_bytes = response.read(2 * 1024 * 1024)
    response.close()
    page = html_bytes.decode("utf-8", errors="ignore")

    action_match = re.search(r'<form[^>]+action="([^"]+)"', page, flags=re.I)
    if not action_match:
        raise RuntimeError("Google Drive trả trang HTML nhưng không tìm thấy link tải xác nhận.")

    action = html.unescape(action_match.group(1))
    params = {}
    for name, value in re.findall(
        r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"',
        page,
        flags=re.I,
    ):
        params[html.unescape(name)] = html.unescape(value)

    if "id" not in params:
        params["id"] = file_id
    if "export" not in params:
        params["export"] = "download"

    confirm_url = action + "?" + urllib.parse.urlencode(params)
    confirm_request = urllib.request.Request(confirm_url, headers=_request_headers())
    return opener.open(confirm_request, timeout=TIMEOUT)


def download_drive():
    file_id = _extract_drive_file_id(DRIVE_URL)
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    _render_download_progress(None, spinner_index=0, source_name="Drive")
    with _drive_confirmation_request(opener, file_id) as response:
        _stream_response_to_archive(response, source_name="Drive")


# ============================================================
# DOWNLOAD MEGA PUBLIC FILE + AES-CTR DECRYPT
# ============================================================

def _b64url_decode(value):
    value = value.strip()
    value += "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _parse_mega_public_file(url):
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]

    if len(parts) >= 2 and parts[0].lower() == "file":
        handle = parts[1]
        key = parsed.fragment
    else:
        # Hỗ trợ link MEGA kiểu cũ /#!HANDLE!KEY
        fragment = parsed.fragment
        if fragment.startswith("!"):
            values = fragment[1:].split("!", 1)
            if len(values) != 2:
                raise ValueError("Link MEGA không hợp lệ.")
            handle, key = values
        else:
            raise ValueError("Link MEGA không hợp lệ.")

    if not handle or not key:
        raise ValueError("Link MEGA thiếu handle hoặc key.")

    return handle, key


def _mega_api_download_info(handle):
    request_id = int(time.time() * 1000) & 0x7FFFFFFF
    api_url = f"https://g.api.mega.co.nz/cs?id={request_id}"
    payload = json.dumps([{"a": "g", "g": 1, "p": handle}]).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=payload,
        headers=_request_headers({"Content-Type": "application/json"}),
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        raw = json.loads(response.read().decode("utf-8"))

    if not isinstance(raw, list) or not raw:
        raise RuntimeError("MEGA API trả dữ liệu không hợp lệ.")

    info = raw[0]
    if isinstance(info, int):
        raise RuntimeError(f"MEGA API error: {info}")
    if not isinstance(info, dict) or "g" not in info:
        raise RuntimeError("MEGA không trả URL download.")

    return info


def download_mega():
    handle, encoded_key = _parse_mega_public_file(MEGA_URL)
    key_bytes = _b64url_decode(encoded_key)
    if len(key_bytes) != 32:
        raise RuntimeError(f"MEGA key không đúng 32 bytes (nhận {len(key_bytes)} bytes).")

    file_key = struct.unpack(">8I", key_bytes)
    aes_key_words = (
        file_key[0] ^ file_key[4],
        file_key[1] ^ file_key[5],
        file_key[2] ^ file_key[6],
        file_key[3] ^ file_key[7],
    )
    aes_key = struct.pack(">4I", *aes_key_words)
    iv0, iv1 = file_key[4], file_key[5]

    info = _mega_api_download_info(handle)
    download_url = info["g"]
    total = int(info.get("s", 0) or 0)

    counter = Counter.new(
        128,
        initial_value=((iv0 << 32) + iv1) << 64,
    )
    decryptor = AES.new(aes_key, AES.MODE_CTR, counter=counter)

    request = urllib.request.Request(download_url, headers=_request_headers())
    downloaded = 0
    start_time = time.monotonic()
    last_render = 0.0
    spinner_index = 0

    _render_download_progress(None, spinner_index=0, source_name="MEGA")

    with urllib.request.urlopen(request, timeout=TIMEOUT) as response, open(ARCHIVE_PATH, "wb") as output:
        if total <= 0:
            total = int(response.headers.get("Content-Length", "0") or 0)

        while True:
            encrypted = response.read(CHUNK_SIZE)
            if not encrypted:
                break

            decrypted = decryptor.decrypt(encrypted)
            output.write(decrypted)
            downloaded += len(decrypted)

            now = time.monotonic()
            if now - last_render >= PROGRESS_REFRESH:
                elapsed = max(now - start_time, 0.001)
                speed = downloaded / elapsed
                spinner_index += 1
                _render_download_progress(
                    (downloaded * 100.0 / total) if total > 0 else None,
                    downloaded=downloaded,
                    total=total,
                    spinner_index=spinner_index,
                    speed_bps=speed,
                    source_name="MEGA",
                )
                last_render = now

    if total > 0 and downloaded != total:
        raise RuntimeError(f"MEGA tải thiếu dữ liệu: {downloaded}/{total} bytes")

    elapsed = max(time.monotonic() - start_time, 0.001)
    speed = downloaded / elapsed
    _render_download_progress(
        100.0 if total > 0 else None,
        downloaded=downloaded,
        total=total,
        spinner_index=spinner_index + 1,
        speed_bps=speed,
        source_name="MEGA",
    )
    _finish_progress_line()


# ============================================================
# DOWNLOAD DISPATCH
# ============================================================

def download_archive(source):
    global _progress_last_len

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PATH.unlink(missing_ok=True)
    _progress_last_len = 0

    try:
        if source == "mega":
            download_mega()
        elif source == "drive":
            download_drive()
        elif source == "github":
            download_github()
        else:
            raise ValueError(f"Nguồn tải không hợp lệ: {source}")
    except Exception as exc:
        _finish_progress_line()
        ARCHIVE_PATH.unlink(missing_ok=True)
        raise RuntimeError(f"Không tải được SEB_VIP: {exc}") from exc

    if not ARCHIVE_PATH.exists() or ARCHIVE_PATH.stat().st_size == 0:
        ARCHIVE_PATH.unlink(missing_ok=True)
        raise RuntimeError("SEB_VIP tải về rỗng hoặc không tồn tại.")

    log(f"Tải xong SEB_VIP: {human_size(ARCHIVE_PATH.stat().st_size)}")


# ============================================================
# GIẢI NÉN BẰNG 7ZR.EXE - HỖ TRỢ BCJ2
# ============================================================

def find_7zr_executable():
    candidates = []

    # PyInstaller one-file giải nén asset bundle vào sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.extend([
            Path(meipass) / "assets" / "7zr.exe",
            Path(meipass) / "7zr.exe",
        ])

    # Khi chạy source để debug/build.
    try:
        project_root = Path(__file__).resolve().parents[2]
        candidates.append(project_root / "assets" / "7zr.exe")
    except Exception:
        pass

    # Nếu máy đã cài 7-Zip thì cũng sử dụng được.
    for command in ("7zr.exe", "7za.exe", "7z.exe"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))

    candidates.extend([
        Path(r"C:\Program Files\7-Zip\7z.exe"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
    ])

    for candidate in candidates:
        try:
            if candidate and candidate.exists():
                return candidate
        except Exception:
            pass

    raise RuntimeError(
        "DucTool.exe hiện tại chưa chứa 7zr.exe. "
        "Hãy build lại DucTool.exe từ project mới để hỗ trợ giải nén BCJ2."
    )


def extract_with_7zr():
    extractor = find_7zr_executable()
    log("\nĐang giải nén SEB_VIP...")

    command = [
        str(extractor),
        "x",
        str(ARCHIVE_PATH),
        f"-o{STAGING_DIR}",
        "-y",
        "-bd",
    ]

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )

    if result.returncode != 0:
        details = (result.stdout or "").strip()
        if len(details) > 1200:
            details = details[-1200:]
        raise RuntimeError(
            f"7-Zip không giải nén được SEB_VIP (code {result.returncode})."
            + (f"\n{details}" if details else "")
        )


def find_seb_root(extracted_root):
    r"""
    Tìm thư mục chứa Application\SafeExamBrowser.exe.
    Hỗ trợ archive có file ở root hoặc được bọc thêm một thư mục ngoài.
    """
    direct = extracted_root / "Application" / "SafeExamBrowser.exe"
    if direct.exists():
        return extracted_root

    for exe in extracted_root.rglob("SafeExamBrowser.exe"):
        if exe.parent.name.lower() == "application":
            return exe.parent.parent

    return None


def move_contents(source_root, destination_root):
    destination_root.mkdir(parents=True, exist_ok=True)

    for item in source_root.iterdir():
        target = destination_root / item.name

        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        shutil.move(str(item), str(target))


def extract_archive():
    if not ARCHIVE_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file tải về: {ARCHIVE_PATH}")

    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR, ignore_errors=True)

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    log(f"\nĐang giải nén vào thư mục tạm: {STAGING_DIR}")

    try:
        extract_with_7zr()

        seb_root = find_seb_root(STAGING_DIR)
        if seb_root is None:
            raise RuntimeError(
                r"Giải nén xong nhưng không tìm thấy Application\SafeExamBrowser.exe"
            )

        if INSTALL_DIR.exists():
            shutil.rmtree(INSTALL_DIR, ignore_errors=True)

        if seb_root.resolve() == STAGING_DIR.resolve():
            STAGING_DIR.replace(INSTALL_DIR)
        else:
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            move_contents(seb_root, INSTALL_DIR)
            shutil.rmtree(STAGING_DIR, ignore_errors=True)

        if not TARGET_EXE.exists():
            raise RuntimeError(f"Cài xong nhưng vẫn thiếu file: {TARGET_EXE}")

        log(f"Giải nén hoàn tất: {INSTALL_DIR}")

    except Exception:
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        raise


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        try:
            os.system("chcp 65001 > nul")
            os.system("cls")
        except Exception:
            pass

    print_duc_tool_banner()
    log()
    log("=" * 62)
    log("MỞ SEB_VIP")
    log("=" * 62)

    if TARGET_EXE.exists():
        log("Đã tìm thấy SEB_VIP trên máy -> mở trực tiếp.")
        launch_seb(TARGET_EXE)
        return 0

    log("Chưa có SEB_VIP trên máy.")
    log(r"Bắt đầu tải SEB_VIP và cài vào C:\duc\SEB_VIP ...")

    source = choose_download_source()

    try:
        download_archive(source)
        extract_archive()

        try:
            ARCHIVE_PATH.unlink(missing_ok=True)
            log("Đã xóa file cài SEB_VIP.")
        except Exception as exc:
            log(f"Cảnh báo: chưa xóa được file cài: {exc}")

        launch_seb(TARGET_EXE)
        return 0

    except Exception as exc:
        log(f"\nLỖI: {exc}")
        log("SEB chưa được mở.")

        try:
            input("\nNhấn Enter để đóng...")
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
