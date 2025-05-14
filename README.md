# Hướng dẫn cài đặt và chạy ứng dụng Coqui TTS (app4.py) hiện chỉ support trên windows.

## 1. Yêu cầu hệ thống

- cài đặt Python 3.10
- pip (trình quản lý gói Python)
- Yarn (trình quản lý gói NodeJS, dùng để cài các gói frontend nếu cần)
- Máy tính có thể chạy được GUI (Windows, macOS, Linux)
- (Tùy chọn) GPU NVIDIA để tăng tốc độ xử lý TTS

## 2. Cài đặt Python và pip

Nếu chưa có Python, tải và cài đặt tại: https://www.python.org/downloads/

Kiểm tra phiên bản:
```bash
python --version
pip --version
```

## 3. Cài đặt Yarn

Nếu chưa có Yarn, cài đặt theo hướng dẫn tại: https://classic.yarnpkg.com/lang/en/docs/install/

Kiểm tra phiên bản:
```bash
yarn --version
```

## 4. Tạo và kích hoạt virtual environment (khuyến nghị)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

## 5. Cài đặt các thư viện Python cần thiết

Tạo file `requirements.txt` với nội dung:
```txt
TTS
pydub
numpy
tk
```

Cài đặt bằng pip:
```bash
pip install -r requirements.txt
```

**Lưu ý:**
- Nếu gặp lỗi thiếu `ffmpeg`, hãy cài đặt ffmpeg (bắt buộc cho pydub):
  - Windows: tải tại https://ffmpeg.org/download.html, giải nén và thêm vào PATH.

## 6. (Tùy chọn) Cài đặt thêm cho GPU

Nếu bạn có GPU NVIDIA và muốn tăng tốc, cài đặt thêm torch phù hợp:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
(Thay `cu121` bằng phiên bản CUDA phù hợp máy bạn)

## 7. Chạy ứng dụng

```bash
python app4.py
```

Giao diện sẽ hiện ra, làm theo các bước:
1. Chọn file .txt chứa văn bản cần chuyển thành giọng nói.
2. Chọn ngôn ngữ, model, giọng (nếu có).
3. Chỉnh tốc độ đọc nếu muốn.
4. Nhấn "Test Voice" để nghe thử.
5. Nhấn "OK" để chuyển toàn bộ file thành file mp3.

## 8. Một số lỗi thường gặp

- **Lỗi thiếu ffmpeg:**
  - Đảm bảo đã cài ffmpeg và thêm vào PATH.
- **Lỗi không có model:**
  - Đảm bảo có kết nối internet để tải model lần đầu.
- **Lỗi CUDA:**
  - Nếu không có GPU hoặc GPU ko đc setup để hỗ trợ thì phần mềm sẽ tự động chuyển sang CPU.
- **Lỗi Test voice:**
  - một số model chưa hỗ trợ test trực tiếp trên tool, muốn test thì tạo 1 file mp3 rồi mở ra nghe
## 9. Liên hệ hỗ trợ

Nếu gặp lỗi không giải quyết được, hãy gửi ảnh chụp màn hình lỗi và mô tả hệ điều hành, phiên bản Python, các bước đã làm tới người phát triển. 