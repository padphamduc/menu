import os
import sys
import json
import shutil
import hashlib
import zipfile
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

import tkinter as tk
from tkinter import messagebox

LAUNCHER_VERSION = "1.0.0"

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(r"C:\duc")
TOOLS_DIR = BASE_DIR / "tools"
SETTINGS_FILE = BASE_DIR / "launcher_settings.json"
GITHUB_TOKEN_FILE = BASE_DIR / "github_token.txt"
GEMINI_KEY_FILE = BASE_DIR / "key.txt"

BASE_DIR.mkdir(parents=True, exist_ok=True)
TOOLS_DIR.mkdir(parents=True, exist_ok=True)

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

DEFAULT_SETTINGS = {
    "repo": "",
    "branch": "main",
    "auto_update": True
}


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
    remote_folder = Path(remote_folder)
    local_folder = Path(local_folder)

    tmp = local_folder.with_name(local_folder.name + ".__new__")
    old = local_folder.with_name(local_folder.name + ".__old__")

    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    if old.exists():
        shutil.rmtree(old, ignore_errors=True)

    shutil.copytree(remote_folder, tmp)
    (tmp / ".managed_by_duc_launcher").write_text("1", encoding="utf-8")
    save_json(tmp / ".sync.json", {"hash": remote_hash})

    if local_folder.exists():
        local_folder.rename(old)

    tmp.rename(local_folder)
    shutil.rmtree(old, ignore_errors=True)


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()

        self.settings = dict(DEFAULT_SETTINGS)
        loaded = safe_json_read(SETTINGS_FILE, {})
        if isinstance(loaded, dict):
            self.settings.update(loaded)

        self.update_running = False
        self.tool_buttons = []

        self.title("Đức Tool Launcher")
        self.geometry("940x650")
        self.minsize(840, 560)
        self.configure(bg=BG)

        self._center()
        self._build_ui()
        self._seed_local_tools()
        self.refresh_tools()

        if not self.settings.get("repo"):
            self.after(450, self.open_settings)
        elif self.settings.get("auto_update", True):
            self.after(500, self.check_updates_async)

    def _center(self):
        self.update_idletasks()
        w, h = 940, 650
        x = max(0, (self.winfo_screenwidth() - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _seed_local_tools(self):
        if any(TOOLS_DIR.iterdir()):
            return

        candidates = [
            APP_DIR / "tools_seed",
            APP_DIR.parent / "tools",
            APP_DIR / "tools",
        ]

        for candidate in candidates:
            if not candidate.is_dir():
                continue
            for td in candidate.iterdir():
                if not td.is_dir() or not (td / "tool.json").exists():
                    continue
                meta = read_tool_meta(td)
                if not meta:
                    continue
                dest = TOOLS_DIR / str(meta["id"])
                try:
                    h = directory_hash(td)
                    copy_tool(td, dest, h)
                except Exception:
                    pass
            if any(TOOLS_DIR.iterdir()):
                break

    def _build_ui(self):
        header = tk.Frame(self, bg=PANEL, height=88)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=PANEL)
        brand.pack(side="left", padx=30, pady=15)

        tk.Label(
            brand, text="ĐỨC TOOL",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI Black", 22)
        ).pack(anchor="w")

        tk.Label(
            brand, text="Dynamic GitHub Launcher",
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
            text="⚙  Cài đặt",
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
            text="Sẵn sàng",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9)
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

    def set_status(self, text, color=None):
        self.status_label.config(
            text=text,
            fg=color or MUTED
        )

    def clear_cards(self):
        for child in self.cards_frame.winfo_children():
            child.destroy()

    def refresh_tools(self):
        tools = []

        for folder in TOOLS_DIR.iterdir():
            if not folder.is_dir():
                continue
            meta = read_tool_meta(folder)
            if meta:
                tools.append(meta)

        tools.sort(key=lambda m: (
            int(m.get("order", 9999)),
            str(m.get("name", "")).lower()
        ))

        self.clear_cards()
        self.count_label.config(
            text=f"{len(tools)} tool" + ("" if len(tools) == 1 else "s")
        )

        if not tools:
            empty = tk.Frame(self.cards_frame, bg=CARD, padx=25, pady=30)
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

        accents = [PURPLE, BLUE, GREEN, "#e46db3", "#e58b45"]

        for i, meta in enumerate(tools):
            self.add_tool_card(meta, accents[i % len(accents)])

    def add_tool_card(self, meta, accent):
        outer = tk.Frame(self.cards_frame, bg=BORDER)
        outer.pack(fill="x", pady=7)

        card = tk.Frame(outer, bg=CARD, padx=20, pady=15)
        card.pack(fill="both", padx=1, pady=1)

        left = tk.Frame(card, bg=CARD)
        left.pack(side="left", fill="both", expand=True)

        name = str(meta.get("name", meta.get("id", "Tool")))
        version = str(meta.get("version", "")).strip()
        title = name if not version else f"{name}   v{version}"

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

        btn = tk.Button(
            card,
            text="MỞ TOOL",
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
        btn.pack(side="right", padx=(20, 0))

        def enter(_):
            for w in (card, left, title_label, desc_label):
                w.configure(bg=CARD_HOVER)

        def leave(_):
            for w in (card, left, title_label, desc_label):
                w.configure(bg=CARD)

        for w in (outer, card, left, title_label, desc_label):
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
            py = self.python_executable()
            if os.name == "nt":
                creationflags = getattr(
                    subprocess,
                    "CREATE_NEW_CONSOLE",
                    0
                )
                subprocess.Popen(
                    [py, str(entry)],
                    cwd=str(folder),
                    creationflags=creationflags
                )
            else:
                subprocess.Popen(
                    [py, str(entry)],
                    cwd=str(folder)
                )

            self.set_status(
                f"Đã mở {meta.get('name', meta.get('id'))}",
                GREEN
            )
        except Exception as e:
            messagebox.showerror("Không thể mở tool", str(e))
            self.set_status("Lỗi mở tool", RED)

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
        win = tk.Toplevel(self)
        win.title("Cài đặt GitHub")
        win.geometry("650x390")
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()

        tk.Label(
            win,
            text="GitHub Repository",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI Semibold", 16)
        ).pack(anchor="w", padx=26, pady=(22, 2))

        tk.Label(
            win,
            text="Dùng repo public không cần token. Repo private có thể nhập token.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=26, pady=(0, 15))

        form = tk.Frame(win, bg=BG)
        form.pack(fill="x", padx=26)

        tk.Label(
            form, text="Repo URL hoặc owner/repo",
            bg=BG, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w")

        repo_var = tk.StringVar(value=self.settings.get("repo", ""))
        repo_entry = tk.Entry(
            form,
            textvariable=repo_var,
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10)
        )
        repo_entry.pack(fill="x", pady=(4, 12), ipady=8)

        row = tk.Frame(form, bg=BG)
        row.pack(fill="x")

        left = tk.Frame(row, bg=BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))

        right = tk.Frame(row, bg=BG)
        right.pack(side="left", fill="x", expand=True, padx=(8, 0))

        tk.Label(
            left, text="Branch",
            bg=BG, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w")

        branch_var = tk.StringVar(
            value=self.settings.get("branch", "main")
        )
        tk.Entry(
            left,
            textvariable=branch_var,
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10)
        ).pack(fill="x", pady=(4, 12), ipady=8)

        tk.Label(
            right, text="GitHub Token (không bắt buộc)",
            bg=BG, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w")

        old_token = ""
        if GITHUB_TOKEN_FILE.exists():
            old_token = GITHUB_TOKEN_FILE.read_text(
                encoding="utf-8",
                errors="ignore"
            ).strip()

        token_var = tk.StringVar(value=old_token)
        tk.Entry(
            right,
            textvariable=token_var,
            show="•",
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10)
        ).pack(fill="x", pady=(4, 12), ipady=8)

        auto_var = tk.BooleanVar(
            value=bool(self.settings.get("auto_update", True))
        )
        tk.Checkbutton(
            form,
            text="Tự kiểm tra và cập nhật khi mở app",
            variable=auto_var,
            bg=BG,
            fg=TEXT,
            selectcolor=CARD,
            activebackground=BG,
            activeforeground=TEXT,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=6)

        btns = tk.Frame(win, bg=BG)
        btns.pack(fill="x", padx=26, pady=20)

        def save_settings():
            repo = repo_var.get().strip()
            if repo:
                try:
                    owner, repository = parse_repo(repo)
                    normalized = f"{owner}/{repository}"
                except Exception as e:
                    messagebox.showerror("Repo không hợp lệ", str(e))
                    return
            else:
                normalized = ""

            self.settings = {
                "repo": normalized,
                "branch": branch_var.get().strip() or "main",
                "auto_update": bool(auto_var.get())
            }
            save_json(SETTINGS_FILE, self.settings)

            token = token_var.get().strip()
            if token:
                GITHUB_TOKEN_FILE.write_text(
                    token,
                    encoding="utf-8"
                )
            elif GITHUB_TOKEN_FILE.exists():
                GITHUB_TOKEN_FILE.unlink()

            self._refresh_footer()
            win.destroy()

            if normalized:
                self.check_updates_async()

        tk.Button(
            btns,
            text="LƯU & ĐỒNG BỘ",
            command=save_settings,
            bg=PURPLE,
            fg="white",
            activebackground=PURPLE,
            activeforeground="white",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            font=("Segoe UI Semibold", 9)
        ).pack(side="right")

        repo_entry.focus_set()

    def github_token(self):
        if not GITHUB_TOKEN_FILE.exists():
            return ""
        return GITHUB_TOKEN_FILE.read_text(
            encoding="utf-8",
            errors="ignore"
        ).strip()

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

        direct = extracted / "tools"
        if direct.exists():
            return extracted

        dirs = [p for p in extracted.iterdir() if p.is_dir()]
        for d in dirs:
            if (d / "tools").exists():
                return d

        raise RuntimeError(
            "Repository không có thư mục tools/."
        )

    def sync_from_repo(self):
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
                    copy_tool(
                        remote_folder,
                        local_folder,
                        remote_hash
                    )
                    updated += 1

            # Remove only tools previously managed by launcher and deleted on GitHub.
            for local_folder in list(TOOLS_DIR.iterdir()):
                if not local_folder.is_dir():
                    continue

                marker = local_folder / ".managed_by_duc_launcher"
                meta = read_tool_meta(local_folder)
                if not marker.exists() or not meta:
                    continue

                tool_id = str(meta["id"])
                if tool_id not in remote_ids:
                    shutil.rmtree(
                        local_folder,
                        ignore_errors=True
                    )
                    updated += 1

            launcher_update_available = False
            remote_version_file = root / "launcher" / "version.json"
            remote_launcher = root / "launcher" / "launcher.py"
            remote_bat = root / "launcher" / "START_APP.bat"

            if remote_version_file.exists() and remote_launcher.exists():
                remote_ver_data = safe_json_read(
                    remote_version_file,
                    {}
                )
                remote_ver = str(
                    (remote_ver_data or {}).get(
                        "version",
                        "0.0.0"
                    )
                )

                if version_tuple(remote_ver) > version_tuple(LAUNCHER_VERSION):
                    try:
                        shutil.copy2(
                            remote_launcher,
                            APP_DIR / "launcher.py"
                        )
                        if remote_bat.exists():
                            shutil.copy2(
                                remote_bat,
                                APP_DIR / "START_APP.bat"
                            )
                        launcher_update_available = True
                    except Exception:
                        pass

            return {
                "discovered": discovered,
                "updated": updated,
                "launcher_updated": launcher_update_available
            }

    def check_updates_async(self):
        if self.update_running:
            return

        if not self.settings.get("repo"):
            self.open_settings()
            return

        self.update_running = True
        self.update_btn.config(state="disabled")
        self.set_status(
            "Đang kiểm tra GitHub...",
            YELLOW
        )

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
            self.set_status(
                "Không thể đồng bộ GitHub",
                RED
            )
            messagebox.showerror(
                "Cập nhật thất bại",
                error
            )
            return

        self.refresh_tools()
        self._refresh_footer()

        updated = int(result.get("updated", 0))
        discovered = int(result.get("discovered", 0))

        if updated:
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
    Launcher().mainloop()
