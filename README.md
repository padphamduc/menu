# DucTool — 1 EXE, không cần cài Python

## Mục tiêu

`DucTool.exe` chứa sẵn Python runtime và các thư viện mà ba tool hiện tại dùng:
- keyboard
- pyautogui / Pillow
- colorama
- google-genai
- pydantic

Launcher vẫn đọc động `tools/` từ GitHub `padphamduc/menu`.
Khi bấm tool, chính `DucTool.exe` chạy `main.py` bằng Python nhúng bên trong.
Máy người nhận KHÔNG cần cài Python.

## Build bằng GitHub Actions

Đưa 4 phần này vào root repository `padphamduc/menu`:
- launcher_exe.py
- DucTool.spec
- requirements-build.txt
- .github/workflows/build-exe.yml

Sau đó GitHub -> Actions -> `Build DucTool EXE` -> Run workflow.
Tải artifact `DucTool-Windows`, bên trong có đúng `DucTool.exe`.

## Gửi cho bạn bè

Chỉ gửi:

    DucTool.exe

Lần đầu chạy, app tạo dữ liệu local dưới:

    C:\duc\

Tool được đồng bộ về:

    C:\duc\tools\

Gemini API key vẫn được nhập/lưu local tại:

    C:\duc\key.txt

## Repo Public vs Private

Nếu `padphamduc/menu` là PUBLIC, bạn bè không cần GitHub token.

Nếu repo PRIVATE, mỗi máy cần quyền đọc riêng. Không nhúng một Personal Access Token chung vào EXE vì người nhận có thể trích xuất nó. Cách đơn giản nhất để phân phối 1 EXE là giữ code/tool không bí mật trong repo PUBLIC và giữ API key chỉ ở máy người dùng.

## Thêm tool sau này

Chỉ thêm thư mục mới dưới `tools/` với `tool.json` + `main.py` rồi push GitHub.
Không cần build lại EXE nếu tool mới chỉ dùng các thư viện đã được nhúng ở trên.

Nếu tool mới import một thư viện Python hoàn toàn mới mà EXE chưa chứa, lúc đó cần thêm thư viện đó vào build và build một EXE mới.
