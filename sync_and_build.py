# -*- coding: utf-8 -*-
r"""
Synchronization and Build Pipeline for DucTool
Mã hóa tự động từ src_clean/ sang môi trường triển khai (D:\TOOLSEB, C:\duc) và biên dịch DucTool.exe
"""

import os
import sys
import shutil
import base64
import zlib
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

_K = b'DucTool_Protected_Key_#2026@'

HEADER = """# -*- coding: utf-8 -*-
# ============================================================
# PROTECTED BY DUCTOOL SECURITY SYSTEM
# BẢN QUYỀN THUỘC VỀ ĐỨC DẠY BẠN HỌC NHÉ <3
# ============================================================
import base64, zlib
_K = b'DucTool_Protected_Key_#2026@'
_D = base64.b64decode('{b64}')
_C = bytes([b ^ _K[i % len(_K)] for i, b in enumerate(_D)])
exec(compile(zlib.decompress(_C).decode('utf-8'), globals().get('__file__', '<protected>'), 'exec'))
"""

def encrypt_code(code_str: str) -> str:
    comp = zlib.compress(code_str.encode('utf-8'))
    xored = bytes([b ^ _K[i % len(_K)] for i, b in enumerate(comp)])
    b64 = base64.b64encode(xored).decode('ascii')
    return HEADER.format(b64=b64)

def process_file(src_path: Path, dst_paths: list[Path]):
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()
    encrypted = encrypt_code(content)
    for dst in dst_paths:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(encrypted)
        print(f"  -> Encrypted to {dst}")

def main():
    base_clean = Path(r"D:\TOOLSEB\src_clean")
    base_toolseb = Path(r"D:\TOOLSEB")
    base_duc = Path(r"C:\duc")

    print("==========================================")
    print(" [1/3] ĐỒNG BỘ VÀ MÃ HÓA SOURCE CODE")
    print("==========================================")

    # 1. launcher_exe.py
    src_launcher = base_clean / "launcher_exe.py"
    if src_launcher.exists():
        process_file(src_launcher, [
            base_toolseb / "launcher_exe.py",
            base_duc / "launcher_online.py",
        ])

    # 2. core/
    src_core = base_clean / "core"
    for py_file in src_core.glob("*.py"):
        print(f"Processing core/{py_file.name}...")
        rel = py_file.name
        process_file(py_file, [
            base_toolseb / "core" / rel,
            base_duc / "core" / rel,
        ])

    # 3. tools/
    src_tools = base_clean / "tools"
    for tool_dir in src_tools.iterdir():
        if tool_dir.is_dir():
            for py_file in tool_dir.glob("*.py"):
                print(f"Processing tools/{tool_dir.name}/{py_file.name}...")
                process_file(py_file, [
                    base_toolseb / "tools" / tool_dir.name / py_file.name,
                    base_toolseb / "tools_seed" / tool_dir.name / py_file.name,
                    base_duc / "tools" / tool_dir.name / py_file.name,
                ])
            for json_file in tool_dir.glob("*.json"):
                print(f"Copying tools/{tool_dir.name}/{json_file.name}...")
                for d in [base_toolseb / "tools" / tool_dir.name, base_toolseb / "tools_seed" / tool_dir.name, base_duc / "tools" / tool_dir.name]:
                    d.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(json_file, d / json_file.name)

    print("\n==========================================")
    print(" [2/3] BIÊN DỊCH DUCTOOL.EXE BẰNG PYINSTALLER")
    print("==========================================")

    # Chạy PyInstaller với DucTool.spec trong môi trường python hiện tại
    py_exe = sys.executable

    cmd = [py_exe, "-m", "PyInstaller", "--noconfirm", "--clean", "DucTool.spec"]
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(base_toolseb))
    if res.returncode != 0:
        print("\n❌ LỖI TRONG QUÁ TRÌNH BIÊN DỊCH PYINSTALLER!")
        sys.exit(res.returncode)

    print("\n==========================================")
    print(" [3/3] TRIỂN KHAI DUCTOOL.EXE")
    print("==========================================")
    built_exe = base_toolseb / "dist" / "DucTool.exe"
    if built_exe.exists():
        target_duc_exe = base_duc / "DucTool.exe"
        try:
            shutil.copy2(built_exe, target_duc_exe)
            print(f"✔ Đã copy {built_exe} -> {target_duc_exe}")
        except Exception:
            old_exe = base_duc / "DucTool.exe.old"
            try:
                if old_exe.exists():
                    try:
                        old_exe.unlink()
                    except Exception:
                        pass
                target_duc_exe.rename(old_exe)
                shutil.copy2(built_exe, target_duc_exe)
                print(f"✔ Đã thay thế thành công (qua rename): {built_exe} -> {target_duc_exe}")
            except Exception as e2:
                print(f"⚠️ Không thể copy tới {target_duc_exe}: {e2}")
        print("\n🎉 HOÀN TẤT ĐỒNG BỘ VÀ BUILD THÀNH CÔNG!")
    else:
        print("\n❌ Không tìm thấy dist\\DucTool.exe sau khi build!")

if __name__ == "__main__":
    main()
