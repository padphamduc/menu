ĐỨC TOOL LAUNCHER - padphamduc/menu

Repo đã tích hợp sẵn:
  padphamduc/menu
Branch:
  main

Cách dùng:
1. Double-click START_APP.bat.
2. App tự đồng bộ GitHub.
3. Nếu repo PUBLIC: không cần GitHub token.
4. Nếu repo PRIVATE: vào “GitHub Access” -> “NHẬP / ĐỔI TOKEN”.
   Token được Windows DPAPI mã hóa và lưu tại:
   C:\duc\github_token.bin
5. Sau này thêm/sửa/xóa tool trong GitHub /tools, app tự nhận.

QUAN TRỌNG:
- Không nhúng GitHub token vào launcher.py.
- Token đã từng gửi trong chat nên cần revoke và tạo token mới.
- Gemini API vẫn lưu local tại C:\duc\key.txt.
