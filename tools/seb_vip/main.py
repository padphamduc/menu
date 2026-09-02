# ============================================================
# MỞ SEB_VIP
# - Nếu đã có: mở trực tiếp.
# - Nếu chưa có: tải SEB_VIP.7z -> giải nén -> xóa .7z -> mở SEB.
# ============================================================

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

import requests
import py7zr


BASE_DIR = Path(r"C:\duc")
INSTALL_DIR = BASE_DIR / "SEB_VIP"
TARGET_EXE = INSTALL_DIR / "Application" / "SafeExamBrowser.exe"
ARCHIVE_PATH = BASE_DIR / "SEB_VIP.7z"
STAGING_DIR = BASE_DIR / "SEB_VIP.__installing__"

# Repo đã được launcher sử dụng cố định.
REPO = "padphamduc/menu"
ASSET_NAME = "SEB_VIP.7z"

# Ưu tiên GitHub Releases. Nếu bạn đặt SEB_VIP.7z trực tiếp ở root branch
# main (và GitHub cho phép kích thước file đó), tool sẽ thử URL raw ở bước 2.
DOWNLOAD_URLS = [
    f"https://github.com/{REPO}/releases/latest/download/{ASSET_NAME}",
    f"https://raw.githubusercontent.com/{REPO}/main/{ASSET_NAME}",
]

CHUNK_SIZE = 1024 * 1024
TIMEOUT = (15, 120)


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

    # Dùng cwd đúng thư mục Application để SEB tìm các file đi kèm.
    subprocess.Popen(
        [str(exe_path)],
        cwd=str(exe_path.parent),
        close_fds=True,
    )


def download_one(url, destination):
    log(f"\nĐang tải:\n{url}")

    with requests.get(
        url,
        stream=True,
        allow_redirects=True,
        timeout=TIMEOUT,
        headers={"User-Agent": "DucTool-SEB-VIP/1.0"},
    ) as response:
        response.raise_for_status()

        total = int(response.headers.get("content-length", "0") or 0)
        downloaded = 0
        last_print = 0.0

        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)

                now = time.monotonic()
                if now - last_print >= 0.5:
                    if total:
                        pct = downloaded * 100 / total
                        log(
                            f"  {human_size(downloaded)} / {human_size(total)} "
                            f"({pct:.1f}%)"
                        )
                    else:
                        log(f"  Đã tải {human_size(downloaded)}")
                    last_print = now

    if not destination.exists() or destination.stat().st_size == 0:
        raise RuntimeError("File tải về rỗng hoặc không tồn tại.")


def download_archive():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # URL tùy chọn cho trường hợp người dùng muốn đổi nguồn mà không sửa code.
    custom_url = os.environ.get("SEB_VIP_URL", "").strip()
    urls = ([custom_url] if custom_url else []) + DOWNLOAD_URLS

    last_error = None

    for url in urls:
        try:
            ARCHIVE_PATH.unlink(missing_ok=True)
            download_one(url, ARCHIVE_PATH)
            log(f"\nTải xong: {ARCHIVE_PATH}")
            return
        except Exception as exc:
            last_error = exc
            ARCHIVE_PATH.unlink(missing_ok=True)
            log(f"Nguồn này không tải được: {exc}")

    raise RuntimeError(
        "Không tải được SEB_VIP.7z từ các nguồn đã cấu hình. "
        f"Lỗi cuối: {last_error}"
    )


def validate_archive_paths(names):
    """Chặn path traversal trước khi extract."""
    for raw_name in names:
        name = str(raw_name).replace("\\", "/")
        p = PurePosixPath(name)
        if p.is_absolute() or ".." in p.parts:
            raise RuntimeError(f"Đường dẫn không an toàn trong archive: {raw_name}")


def find_seb_root(extracted_root):
    """
    Tìm thư mục chứa Application\SafeExamBrowser.exe.
    Hỗ trợ cả archive có file ở root và archive bọc thêm một thư mục ngoài.
    """
    direct = extracted_root / "Application" / "SafeExamBrowser.exe"
    if direct.exists():
        return extracted_root

    matches = list(extracted_root.rglob("SafeExamBrowser.exe"))
    for exe in matches:
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
        with py7zr.SevenZipFile(ARCHIVE_PATH, mode="r") as archive:
            validate_archive_paths(archive.getnames())
            archive.extractall(path=STAGING_DIR)

        seb_root = find_seb_root(STAGING_DIR)
        if seb_root is None:
            raise RuntimeError(
                "Giải nén xong nhưng không tìm thấy Application\\SafeExamBrowser.exe"
            )

        if INSTALL_DIR.exists():
            shutil.rmtree(INSTALL_DIR, ignore_errors=True)

        # Nếu root thật chính là staging thì đổi tên nhanh; nếu archive có một
        # thư mục bao ngoài thì chỉ chuyển nội dung root thật sang C:\duc\SEB_VIP.
        if seb_root.resolve() == STAGING_DIR.resolve():
            STAGING_DIR.replace(INSTALL_DIR)
        else:
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            move_contents(seb_root, INSTALL_DIR)
            shutil.rmtree(STAGING_DIR, ignore_errors=True)

        if not TARGET_EXE.exists():
            raise RuntimeError(
                f"Cài xong nhưng vẫn thiếu file: {TARGET_EXE}"
            )

        log(f"Giải nén hoàn tất: {INSTALL_DIR}")

    except Exception:
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        raise


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 62)
    log("MỞ SEB_VIP")
    log("=" * 62)

    # Đã có thì không tải/cài lại.
    if TARGET_EXE.exists():
        log("Đã tìm thấy SEB_VIP trên máy -> mở trực tiếp.")
        launch_seb(TARGET_EXE)
        return 0

    log("Chưa có SEB_VIP trên máy.")
    log("Bắt đầu tải SEB_VIP.7z và cài vào C:\\duc\\SEB_VIP ...")

    try:
        download_archive()
        extract_archive()

        # Chỉ xóa gói .7z sau khi đã giải nén và kiểm tra EXE thành công.
        try:
            ARCHIVE_PATH.unlink(missing_ok=True)
            log(f"Đã xóa file cài: {ARCHIVE_PATH}")
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
