# dung thu vien TTS va pydub
import os
from TTS.api import TTS
from pydub import AudioSegment
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import tempfile
import time
import numpy as np
from pydub.playback import play
from TTS.utils.manage import ModelManager
from functools import lru_cache
import uuid

# Tự động lấy danh sách model tiếng Anh mới nhất
all_models = ModelManager().list_models()
en_models = [m for m in all_models if m.startswith("tts_models/en/")]

# Danh sách model theo ngôn ngữ
LANG_MODELS = {
    "English": en_models,
    "Vietnamese": [
        "tts_models/vi/viet_tts"
    ],
    "Multilingual": [
        "tts_models/multilingual/multi-dataset/your_tts"
    ]
}

# Tạo cache cho các instance TTS
tts_cache = {}
def get_tts(model_name):
    if model_name not in tts_cache:
        tts = TTS(model_name)
        try:
            tts.to("cuda")  # Nếu có GPU sẽ dùng GPU, không thì sẽ báo lỗi và dùng CPU
        except Exception:
            tts.to("cpu")
        tts_cache[model_name] = tts
    return tts_cache[model_name]

def chunk_text(text, max_chars=500):
    """
    Tách văn bản thành các đoạn nhỏ, cố gắng tách theo dấu chấm để không cắt câu giữa chừng.
    """
    chunks = []
    while len(text) > max_chars:
        pos = text.rfind(".", 0, max_chars)
        if pos == -1:
            pos = max_chars
        chunk = text[:pos+1].strip()    # Lấy đến dấu chấm
        chunks.append(chunk)
        text = text[pos+1:].strip()
    if text:
        chunks.append(text)
    return chunks

# Hàm chọn file txt
def select_txt_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        txt_file_entry.delete(0, tk.END)
        txt_file_entry.insert(0, file_path)

def get_speakers(model_name):
    try:
        tts = get_tts(model_name)
        if hasattr(tts, "speakers") and tts.speakers:
            return tts.speakers
        return []
    except Exception:
        return []

def on_language_change(*args):
    lang = language_var.get()
    models = LANG_MODELS[lang]
    model_var.set(models[0])
    model_menu['menu'].delete(0, 'end')
    for m in models:
        model_menu['menu'].add_command(label=m, command=tk._setit(model_var, m))
    update_speaker_list()

def on_model_change(*args):
    update_speaker_list()

def update_speaker_list():
    model_name = model_var.get()
    speakers = get_speakers(model_name)
    speaker_menu['menu'].delete(0, 'end')
    if speakers:
        for s in speakers:
            speaker_menu['menu'].add_command(label=s, command=tk._setit(speaker_var, s))
        speaker_var.set(speakers[0])
        speaker_label.pack(pady=10)
        speaker_menu.pack(pady=5)
    else:
        speaker_var.set("")
        speaker_label.pack_forget()
        speaker_menu.pack_forget()
    # Luôn luôn hiển thị ô nhập văn bản test và nút Test Voice
    test_text_label.pack(pady=10)
    test_text_entry.pack(pady=5)
    test_button.pack(pady=5)

# Thêm biến speed_var để chọn tốc độ đọc
speed_var = None

# Thêm biến progress_var, progress_bar, progress_label
progress_var = None
progress_bar = None
progress_label = None

def test_voice():
    try:
        model_name = model_var.get()
        speaker = speaker_var.get() if speaker_var.get() else None
        tts = get_tts(model_name)
        text = test_text_var.get()
        speed = float(speed_var.get()) if speed_var else 0.9
        # Truyền speed nếu model hỗ trợ
        try:
            result = tts.tts(text=text, speaker=speaker if speaker else None, speed=speed)
        except TypeError:
            result = tts.tts(text=text, speaker=speaker if speaker else None)
        if isinstance(result, (tuple, list)):
            wav = result[0]
        else:
            wav = result
        if isinstance(wav, list):
            wav = np.array(wav)
        audio = AudioSegment(
            (wav * 32767).astype(np.int16).tobytes(),
            frame_rate=44100,  # tăng sample rate
            sample_width=2,
            channels=1
        )
        temp_wav = os.path.join(tempfile.gettempdir(), f"tts_test_{uuid.uuid4().hex}.wav")
        audio.export(temp_wav, format="wav")
        play(audio)
        os.startfile(temp_wav)
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không test được giọng: {e}")

def convert_to_speech_thread():
    try:
        txt_file = txt_file_entry.get()
        model_name = model_var.get()
        speaker = speaker_var.get() if speaker_var.get() else None
        speed = float(speed_var.get()) if speed_var else 0.9
        if not txt_file:
            messagebox.showerror("Lỗi", "Vui lòng chọn file txt.")
            return
        if not os.path.exists(txt_file):
            messagebox.showerror("Lỗi", "File không tồn tại.")
            return
        with open(txt_file, 'r', encoding='utf-8') as file:
            text = file.read()
        def chunk_text(text, max_chars=500):
            chunks = []
            while len(text) > max_chars:
                pos = text.rfind(".", 0, max_chars)
                if pos == -1:
                    pos = max_chars
                chunk = text[:pos+1].strip()
                chunks.append(chunk)
                text = text[pos+1:].strip()
            if text:
                chunks.append(text)
            return chunks
        chunks = chunk_text(text, max_chars=500)
        tts = get_tts(model_name)
        audio_segments = []
        total_chunks = len(chunks)
        if progress_bar and progress_var and progress_label:
            progress_var.set(0)
            progress_bar['maximum'] = total_chunks
            progress_label.config(text=f"Đang xử lý: 0/{total_chunks}")
        for i, chunk in enumerate(chunks):
            temp_file = f"temp_audio_{i}.wav"
            # Truyền speed nếu model hỗ trợ
            try:
                tts.tts_to_file(text=chunk, file_path=temp_file, speaker=speaker if speaker else None, speed=speed)
            except TypeError:
                tts.tts_to_file(text=chunk, file_path=temp_file, speaker=speaker if speaker else None)
            segment = AudioSegment.from_wav(temp_file)
            segment = segment.set_frame_rate(44100)  # tăng sample rate
            audio_segments.append(segment)
            os.remove(temp_file)
            # Cập nhật progress
            if progress_bar and progress_var and progress_label:
                progress_var.set(i+1)
                progress_label.config(text=f"Đang xử lý: {i+1}/{total_chunks}")
                progress_bar.update_idletasks()
        combined = audio_segments[0]
        for seg in audio_segments[1:]:
            combined += seg
        base_filename = os.path.splitext(os.path.basename(txt_file))[0]
        folder = os.path.dirname(txt_file)
        safe_model = model_name.replace('/', '_')
        name_parts = [base_filename, safe_model]
        if speaker:
            name_parts.append(speaker.replace(' ', '_'))
        output_base = '_'.join(name_parts)
        output_filename = os.path.join(folder, output_base + '.mp3')
        count = 1
        while os.path.exists(output_filename):
            output_filename = os.path.join(folder, f"{output_base}_{count}.mp3")
            count += 1
        combined.export(output_filename, format="mp3")
        messagebox.showinfo("Thành công", f"Đã tạo file MP3: {output_filename}")
        # Reset progress khi xong
        if progress_bar and progress_var and progress_label:
            progress_var.set(0)
            progress_label.config(text="Hoàn thành!")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Đã xảy ra lỗi: {str(e)}")
    finally:
        ok_button.config(state=tk.NORMAL, text="OK")

def on_ok_click():
    ok_button.config(state=tk.DISABLED, text="Loading...")
    threading.Thread(target=convert_to_speech_thread).start()

# Giao diện chính
def main():
    global txt_file_entry, language_var, model_var, model_menu, speaker_var, speaker_menu, speaker_label, test_button, ok_button, test_text_var, test_text_label, test_text_entry, speed_var, progress_var, progress_bar, progress_label
    root = tk.Tk()
    root.title("DIOUS tool TTS - Chuyển Văn Bản Thành Giọng Nói")
    root.geometry("500x700")

    txt_file_label = tk.Label(root, text="Chọn file .txt:")
    txt_file_label.pack(pady=10)

    txt_file_entry = tk.Entry(root, width=50)
    txt_file_entry.pack(pady=5)

    txt_file_button = tk.Button(root, text="Chọn File", command=select_txt_file)
    txt_file_button.pack(pady=5)

    language_label = tk.Label(root, text="Chọn Ngôn Ngữ:")
    language_label.pack(pady=10)

    language_var = tk.StringVar(value="English")
    language_menu = tk.OptionMenu(root, language_var, *LANG_MODELS.keys())
    language_menu.pack(pady=5)

    model_label = tk.Label(root, text="Chọn Model:")
    model_label.pack(pady=10)
    model_var = tk.StringVar(value=LANG_MODELS["English"][0])
    model_menu = tk.OptionMenu(root, model_var, *LANG_MODELS["English"])
    model_menu.pack(pady=5)

    speaker_label = tk.Label(root, text="Chọn Giọng (Speaker):")
    speaker_var = tk.StringVar()
    speaker_menu = tk.OptionMenu(root, speaker_var, "")

    # Thêm label và entry cho tốc độ đọc
    speed_label = tk.Label(root, text="Chọn tốc độ đọc (0.5 = chậm, 1.0 = chuẩn, 2.0 = nhanh):")
    speed_label.pack(pady=10)
    speed_var = tk.StringVar(value="0.8")
    speed_entry = tk.Entry(root, textvariable=speed_var, width=10)
    speed_entry.pack(pady=5)

    # Thêm progress bar và label
    progress_var = tk.IntVar(value=0)
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=1, length=400)
    progress_bar.pack(pady=10)
    progress_label = tk.Label(root, text="Đang xử lý: 0/0")
    progress_label.pack(pady=5)

    # Thêm label cho ô nhập văn bản test
    test_text_label = tk.Label(root, text="Nhập văn bản để test giọng:")
    test_text_var = tk.StringVar(value="Hello, this is a sample voice!")
    test_text_entry = tk.Entry(root, textvariable=test_text_var, width=40)
    test_button = tk.Button(root, text="Test Voice", command=lambda: threading.Thread(target=test_voice).start())

    # Mặc định cập nhật speaker khi chọn model/ngôn ngữ
    language_var.trace_add('write', on_language_change)
    model_var.trace_add('write', on_model_change)
    update_speaker_list()

    ok_button = tk.Button(root, text="OK", command=on_ok_click)
    ok_button.pack(side="bottom", pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()