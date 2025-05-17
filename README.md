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

## 3.1. Cài đặt GitHub CLI (gh)

Nếu chưa có GitHub CLI, bạn nên cài để dễ thao tác với GitHub từ dòng lệnh:

- Tải và cài đặt theo hướng dẫn tại: https://cli.github.com/manual/installation
- Hoặc trên Windows, có thể dùng lệnh sau (nếu đã cài winget):
  ```bash
  winget install --id GitHub.cli
  ```
- Kiểm tra phiên bản:
  ```bash
  gh --version
  ```

## 3.2. Clone repository về máy

Sau khi đã cài GitHub CLI hoặc Git, bạn có thể clone repo về máy bằng lệnh:

```bash
git clone https://github.com/haki203/dious-coqui-tts.git
```
Sau đó, di chuyển vào thư mục dự án:

```bash
cd dious-coqui-tts
```

## 4. Tạo và kích hoạt virtual environment (bắt buộc nếu có nhiều ver python. còn nếu chỉ có python 3.10 thì ko cần)

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
- Nếu bạn muốn cài torch (dùng cho GPU hoặc một số model TTS), hãy cài riêng bằng lệnh sau:
  ```bash
  pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
  ```
- Nếu máy bạn **không có GPU NVIDIA hoặc không hỗ trợ CUDA**, bạn vẫn có thể cài bản trên (torch sẽ tự động chạy trên CPU). Tuy nhiên, để tiết kiệm dung lượng, bạn có thể cài bản chỉ hỗ trợ CPU bằng lệnh:
  ```bash
  pip install torch==2.5.1+cpu --index-url https://download.pytorch.org/whl/cpu
  ```
- ffmpeg là phần mềm ngoài, bắt buộc phải cài để pydub hoạt động. Đã hướng dẫn chi tiết ở trên.
- Các model TTS sẽ được tự động tải về khi bạn chọn lần đầu trong giao diện, không cần cài đặt thủ công.

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