# dung thu vien TTS va pydub
import os
from TTS.api import TTS  # type: ignore
from pydub import AudioSegment
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import tempfile
import time
import numpy as np  # type: ignore
from pydub.playback import play
from TTS.utils.manage import ModelManager  # type: ignore
from functools import lru_cache
import uuid
import sounddevice as sd  # Thêm thư viện sounddevice
import queue  # Thêm queue để xử lý buffer âm thanh
from speaker_gender import SPEAKER_GENDER
import concurrent.futures

# Tự động lấy danh sách models mới nhất
all_models = ModelManager().list_models()
en_models = [m for m in all_models if m.startswith("tts_models/en/")]

# Danh sách model theo ngôn ngữ
LANG_MODELS = {
    "English": en_models,
}

# Tạo cache cho các instance TTS
tts_cache = {}

# Số luồng tối đa cho xử lý song song
MAX_WORKERS = min(4, os.cpu_count() or 4)

# Thêm biến global để lưu trạng thái GPU
USE_CUDA = False

def initialize_cuda():
    """Kiểm tra và khởi tạo CUDA một lần duy nhất khi chương trình bắt đầu"""
    global USE_CUDA
    try:
        import torch
        print("[DEBUG] Đã import torch thành công trong initialize_cuda")
        if torch.cuda.is_available():
            print("[DEBUG] torch.cuda.is_available() == True")
        else:
            print("[DEBUG] torch.cuda.is_available() == False")
        if torch.backends.cudnn.is_available():
            print("[DEBUG] torch.backends.cudnn.is_available() == True")
        else:
            print("[DEBUG] torch.backends.cudnn.is_available() == False")
        if torch.cuda.is_available() and torch.backends.cudnn.is_available():
            # Khởi tạo CUDA
            try:
                torch.cuda.init()
                print("[DEBUG] torch.cuda.init() thành công")
            except Exception as e:
                print(f"[DEBUG] Lỗi khi torch.cuda.init(): {e}")
            device_count = torch.cuda.device_count()
            current_device = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(current_device)
            print(f"Sử dụng GPU: {device_name} (Device {current_device}/{device_count})")
            USE_CUDA = True
        else:
            print("Không tìm thấy GPU hỗ trợ CUDA, sử dụng CPU")
            USE_CUDA = False
    except Exception as e:
        print(f"Lỗi khi khởi tạo CUDA: {str(e)}")
        USE_CUDA = False
    print(f"[DEBUG] USE_CUDA trong initialize_cuda: {USE_CUDA}")
    return USE_CUDA

def parallel_process(function, items, max_workers=MAX_WORKERS):
    """Xử lý các item trong danh sách song song bằng ThreadPoolExecutor"""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(function, item): item for item in items}
        for future in concurrent.futures.as_completed(future_to_item):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"Lỗi khi xử lý item: {str(e)}")
    return results

def get_tts(model_name):
    if model_name not in tts_cache:
        tts = TTS(model_name)
        if USE_CUDA:
            try:
                tts.to("cuda")
                print(f"[INFO] Model '{model_name}' is running on GPU (CUDA)")
            except Exception as e:
                tts.to("cpu")
                print(f"[INFO] Model '{model_name}' fallback to CPU. Lý do không dùng được GPU CUDA: {str(e)}")
        else:
            tts.to("cpu")
            # Log rõ lý do không dùng được CUDA
            try:
                import torch
                if not torch.cuda.is_available():
                    print(f"[INFO] Model '{model_name}' is running on CPU. Lý do: torch.cuda.is_available() == False (không phát hiện GPU hoặc driver CUDA)")
                elif not torch.backends.cudnn.is_available():
                    print(f"[INFO] Model '{model_name}' is running on CPU. Lý do: torch.backends.cudnn.is_available() == False (không phát hiện cuDNN)")
                else:
                    print(f"[INFO] Model '{model_name}' is running on CPU. Lý do: Không rõ (USE_CUDA==False)")
            except ImportError:
                print(f"[INFO] Model '{model_name}' is running on CPU. Lý do: Không import được torch (chưa cài torch hoặc môi trường lỗi)")
        tts_cache[model_name] = tts
    return tts_cache[model_name]

@lru_cache(maxsize=32)
def get_speakers(model_name):
    try:
        tts = get_tts(model_name)
        if hasattr(tts, "speakers") and tts.speakers:
            return tts.speakers
        return []
    except Exception:
        return []

def chunk_text(text, max_chars=500):
    """
    Tách văn bản thành các đoạn nhỏ, cố gắng tách theo dấu chấm để không cắt câu giữa chừng.
    """
    chunks = []
    while len(text) > max_chars:
        pos = text.rfind(".", 0, max_chars)
        if pos == -1:
            pos = max_chars
        chunk = text[: pos + 1].strip()  # Lấy đến dấu chấm
        chunks.append(chunk)
        text = text[pos + 1 :].strip()
    if text:
        chunks.append(text)
    return chunks

@lru_cache(maxsize=100)
def get_speaker_gender(speaker_name):
    """Hàm helper để lấy giới tính/độ tuổi chi tiết của speaker nếu có, ưu tiên tra cứu nhiều biến thể tên speaker."""
    # Chuẩn hóa tên
    name_raw = speaker_name
    name_strip = speaker_name.strip()
    name_lower = name_strip.lower()
    name_noprefix = name_strip.replace("VCTK_", "").replace("vctk_", "")
    name_noprefix_lower = name_noprefix.lower()
    # Danh sách các biến thể để thử tra dict
    variants = [
        name_raw,
        name_strip,
        name_lower,
        name_noprefix,
        name_noprefix_lower
    ]
    for v in variants:
        if v in SPEAKER_GENDER:
            return SPEAKER_GENDER[v]
    # Nếu không tìm thấy, log ra để debug
    print(f"[DEBUG] Không tìm thấy giới tính cho speaker: '{speaker_name}'. Các biến thể đã thử: {variants}")
    # Xử lý các trường hợp đặc biệt chi tiết
    # Ưu tiên các label chi tiết
    keyword_map = [
        (['young boy', 'boy child', 'child boy'], 'Young Boy'),
        (['young girl', 'girl child', 'child girl'], 'Young Girl'),
        (['boy'], 'Boy'),
        (['girl'], 'Girl'),
        (['child'], 'Child'),
        (['young'], 'Young'),
        (['male', 'man', 'm_'], 'Male'),
        (['female', 'woman', 'f_'], 'Female'),
    ]
    for keywords, label in keyword_map:
        for kw in keywords:
            if kw in name_lower:
                return label
    # Kiểm tra các model đơn giọng phổ biến
    for model_prefix in ["ljspeech", "libritts", "yourtts", "coqui_studio"]:
        if model_prefix in name_lower:
            try:
                speaker_num = int(''.join(filter(str.isdigit, speaker_name)))
                return "Female" if speaker_num % 2 == 0 else "Male"
            except:
                pass
    return "Unknown"

def update_speaker_list():
    model_name = model_var.get()
    speakers = get_speakers(model_name)
    speaker_menu["menu"].delete(0, "end")
    if speakers:
        for s in speakers:
            # Sử dụng hàm helper để lấy giới tính
            gender = get_speaker_gender(s)
            label = f"{s} ({gender})"
            speaker_menu["menu"].add_command(label=label, command=tk._setit(speaker_var, s))
        speaker_var.set(speakers[0])
        speaker_label.pack(pady=10)
        speaker_menu.pack(pady=5)
    else:
        speaker_var.set("")
        speaker_label.pack_forget()
        speaker_menu.pack_forget()

def on_language_change(*args):
    lang = language_var.get()
    models = LANG_MODELS[lang]
    model_var.set(models[0])
    model_menu["menu"].delete(0, "end")
    for m in models:
        model_menu["menu"].add_command(label=m, command=tk._setit(model_var, m))
    update_speaker_list()

def on_model_change(*args):
    update_speaker_list()

# Thêm biến speed_var để chọn tốc độ đọc
speed_var = None

# Thêm biến progress_var, progress_bar, progress_label
progress_var = None
progress_bar = None
progress_label = None

def test_voice():
    try:
        print("Bắt đầu test voice...")
        
        # Kiểm tra xem user đã chọn file txt chưa
        txt_file = txt_file_entry.get()
        if not txt_file:
            messagebox.showerror("Lỗi", "Vui lòng chọn file txt trước khi test giọng.")
            return
        
        if not os.path.exists(txt_file):
            messagebox.showerror("Lỗi", "File txt không tồn tại.")
            return
            
        # Lấy danh sách các speaker của model hiện tại
        model_name = model_var.get()
        speakers = get_speakers(model_name)
        
        if not speakers:
            # Nếu model không có nhiều speaker, sử dụng None
            test_for_model(model_name, None, txt_file, [])
        else:
            # Hiển thị thông báo
            messagebox.showinfo("Test Voice", f"Đang tạo file âm thanh cho {len(speakers)} giọng của model {model_name}.\nQuá trình này có thể mất một chút thời gian.")
            
            # Tạo thread cho mỗi speaker
            for speaker in speakers:
                threading.Thread(
                    target=test_for_model,
                    args=(model_name, speaker, txt_file, speakers)
                ).start()
                
    except Exception as e:
        print(f"Lỗi tổng thể trong test_voice: {str(e)}")
        messagebox.showerror("Lỗi", f"Không test được giọng: {str(e)}")

def test_for_model(model_name, speaker, txt_file, all_speakers):
    """Tạo file âm thanh test cho một speaker cụ thể"""
    try:
        start_time = time.time()  # Bắt đầu đếm thời gian
        # Thiết lập các tham số cần thiết
        speed = 0.8
        if speed_var and speed_var.get():
            try:
                speed = float(speed_var.get())
            except Exception:
                speed = 0.8
        
        # Đọc nội dung file txt
        with open(txt_file, "r", encoding="utf-8") as file:
            text = file.read()
        
        # Rút gọn văn bản nếu quá dài để test nhanh hơn
        if len(text) > 500:
            text = text[:500] + "..."
        
        # Tạo tên file
        base_filename = os.path.splitext(os.path.basename(txt_file))[0]
        folder = os.path.dirname(txt_file)
        safe_model = model_name.replace("/", "_")
        
        if speaker:
            # Sử dụng hàm helper để lấy giới tính
            gender = get_speaker_gender(speaker)
            output_filename = os.path.join(folder, f"test_{safe_model}_{speaker.replace(' ', '_')}_{gender}.mp3")
        else:
            output_filename = os.path.join(folder, f"test_{safe_model}.mp3")
        
        # Kiểm tra nếu file đã tồn tại
        count = 1
        original_output = output_filename
        while os.path.exists(output_filename):
            output_filename = original_output.replace(".mp3", f"_{count}.mp3")
            count += 1
        
        # Sử dụng lại logic từ hàm convert_to_speech_thread để tạo file âm thanh
        tts = get_tts(model_name)
        
        # Chia văn bản thành các đoạn nhỏ hơn nếu cần
        chunks = chunk_text(text, max_chars=500)
        
        # Tạo thư mục tạm thời để lưu các file tạm
        temp_dir = tempfile.mkdtemp(prefix="tts_test_")
        
        try:
            # Hàm để xử lý từng chunk riêng biệt
            def process_chunk(chunk_data):
                index, chunk_text = chunk_data
                temp_file = os.path.join(temp_dir, f"temp_test_{index}.wav")
                
                try:
                    # Tạo âm thanh và lưu vào file tạm
                    try:
                        tts.tts_to_file(
                            text=chunk_text,
                            file_path=temp_file,
                            speaker=speaker,
                            speed=speed,
                        )
                    except TypeError as e:
                        # Nếu model không hỗ trợ speed, thông báo cho user và chờ OK
                        root = None
                        try:
                            root = tk._get_default_root()
                        except:
                            pass
                        messagebox.showwarning(
                            "Speed not supported",
                            f"Model '{model_name}' không hỗ trợ điều chỉnh tốc độ đọc (speed).\nSẽ sử dụng tốc độ mặc định của model.\n\nNhấn OK để tiếp tục.",
                            parent=root
                        )
                        tts.tts_to_file(
                            text=chunk_text,
                            file_path=temp_file,
                            speaker=speaker,
                        )
                    
                    # Đọc file âm thanh tạm thời
                    segment = AudioSegment.from_wav(temp_file)
                    segment = segment.set_frame_rate(44100)  # tăng sample rate
                    return segment
                except Exception as e:
                    print(f"Lỗi khi xử lý chunk {index}: {str(e)}")
                    return None
                finally:
                    # Xóa file tạm
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
            
            # Xử lý song song các chunks
            chunk_data = [(i, chunk) for i, chunk in enumerate(chunks)]
            audio_segments = parallel_process(process_chunk, chunk_data)
            
            # Loại bỏ các kết quả None
            audio_segments = [seg for seg in audio_segments if seg is not None]
            
            # Ghép các đoạn âm thanh
            if audio_segments:
                try:
                    combined = audio_segments[0]
                    for seg in audio_segments[1:]:
                        combined += seg
                        
                    # Xuất file âm thanh
                    combined.export(output_filename, format="mp3")
                    print(f"Đã tạo file test: {output_filename}")
                    total_time = time.time() - start_time
                    # Chỉ hiển thị thông báo hoàn thành nếu đây là speaker cuối cùng
                    if not all_speakers or speaker == all_speakers[-1]:
                        messagebox.showinfo("Hoàn thành", f"Đã tạo file test cho model {model_name}" + \
                                                        (f" với giọng {speaker}" if speaker else "") + \
                                                        f"\nTổng thời gian xử lý: {total_time:.2f} giây")
                except Exception as e:
                    print(f"Lỗi khi xuất file âm thanh cuối cùng: {str(e)}")
                    if not all_speakers or speaker == all_speakers[-1]:
                        messagebox.showerror("Lỗi", f"Không thể tạo file âm thanh cuối cùng: {str(e)}")
        finally:
            # Dọn dẹp thư mục tạm
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
    
    except Exception as e:
        # Chỉ hiển thị thông báo lỗi cho người dùng nếu đây là lỗi nghiêm trọng
        error_msg = str(e)
        if "CUDA" in error_msg or "GPU" in error_msg or "memory" in error_msg.lower():
            if not all_speakers or speaker == all_speakers[-1]:
                messagebox.showerror("Lỗi", f"Lỗi hệ thống: {error_msg}")
        else:
            print(f"Lỗi khi xử lý {model_name} ({speaker}): {error_msg}")

def convert_to_speech_thread():
    try:
        start_time = time.time()  # Bắt đầu đếm thời gian
        txt_file = txt_file_entry.get()
        model_name = model_var.get()
        speaker = speaker_var.get() if speaker_var.get() else None
        speed = 0.8
        if speed_var and speed_var.get():
            try:
                speed = float(speed_var.get())
            except Exception:
                speed = 0.8
        if not txt_file:
            messagebox.showerror("Lỗi", "Vui lòng chọn file txt.")
            return
        if not os.path.exists(txt_file):
            messagebox.showerror("Lỗi", "File không tồn tại.")
            return
        with open(txt_file, "r", encoding="utf-8") as file:
            text = file.read()

        chunks = chunk_text(text, max_chars=500)
        tts = get_tts(model_name)
        total_chunks = len(chunks)
        if progress_bar and progress_var and progress_label:
            progress_var.set(0)
            progress_bar["maximum"] = total_chunks
            progress_label.config(text=f"Đang xử lý: 0/{total_chunks}")
        
        # Tạo thư mục tạm thời
        temp_dir = tempfile.mkdtemp(prefix="tts_temp_")
        
        try:
            # Hàm để xử lý từng chunk riêng biệt
            def process_chunk(chunk_data):
                index, chunk_text = chunk_data
                temp_file = os.path.join(temp_dir, f"temp_audio_{index}.wav")
                try:
                    try:
                        tts.tts_to_file(
                            text=chunk_text,
                            file_path=temp_file,
                            speaker=speaker if speaker else None,
                            speed=speed,
                        )
                    except TypeError as e:
                        # Nếu model không hỗ trợ speed, thông báo cho user và chờ OK
                        root = None
                        try:
                            root = tk._get_default_root()
                        except:
                            pass
                        messagebox.showwarning(
                            "Speed not supported",
                            f"Model '{model_name}' không hỗ trợ điều chỉnh tốc độ đọc (speed).\nSẽ sử dụng tốc độ mặc định của model.\n\nNhấn OK để tiếp tục.",
                            parent=root
                        )
                        tts.tts_to_file(
                            text=chunk_text,
                            file_path=temp_file,
                            speaker=speaker if speaker else None,
                        )
                    
                    segment = AudioSegment.from_wav(temp_file)
                    segment = segment.set_frame_rate(44100)  # tăng sample rate
                    
                    # Cập nhật progress
                    if progress_bar and progress_var and progress_label:
                        # Sử dụng after vì giao diện không an toàn cho đa luồng
                        root = progress_bar.winfo_toplevel()
                        root.after(0, lambda: progress_var.set(progress_var.get() + 1))
                        root.after(0, lambda: progress_label.config(text=f"Đang xử lý: {progress_var.get()}/{total_chunks}"))
                        root.after(0, lambda: progress_bar.update_idletasks())
                    
                    return segment
                except Exception as e:
                    print(f"Lỗi khi xử lý chunk {index}: {str(e)}")
                    return None
                finally:
                    # Xóa file tạm
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
            
            # Xử lý song song các chunks
            chunk_data = [(i, chunk) for i, chunk in enumerate(chunks)]
            audio_segments = parallel_process(process_chunk, chunk_data)
            
            # Loại bỏ các kết quả None
            audio_segments = [seg for seg in audio_segments if seg is not None]
                    
            if audio_segments:
                combined = audio_segments[0]
                for seg in audio_segments[1:]:
                    combined += seg
                    
                base_filename = os.path.splitext(os.path.basename(txt_file))[0]
                folder = os.path.dirname(txt_file)
                safe_model = model_name.replace("/", "_")
                name_parts = [base_filename, safe_model]
                if speaker:
                    name_parts.append(speaker.replace(" ", "_"))
                output_base = "_".join(name_parts)
                output_filename = os.path.join(folder, output_base + ".mp3")
                count = 1
                while os.path.exists(output_filename):
                    output_filename = os.path.join(folder, f"{output_base}_{count}.mp3")
                    count += 1
                combined.export(output_filename, format="mp3")
                total_time = time.time() - start_time
                messagebox.showinfo("Thành công", f"Đã tạo file MP3: {output_filename}\nTổng thời gian: {total_time:.2f} giây")
                # Reset progress khi xong
                if progress_bar and progress_var and progress_label:
                    progress_var.set(0)
                    progress_label.config(text="Hoàn thành!")
        finally:
            # Dọn dẹp thư mục tạm
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
    except Exception as e:
        messagebox.showerror("Lỗi", f"Đã xảy ra lỗi: {str(e)}")
    finally:
        ok_button.config(state=tk.NORMAL, text="OK")

def on_ok_click():
    ok_button.config(state=tk.DISABLED, text="Loading...")
    threading.Thread(target=convert_to_speech_thread).start()

# Giao diện chính
def main():
    # Khởi tạo CUDA khi chương trình bắt đầu
    initialize_cuda()
    print(f"[DEBUG] USE_CUDA sau khi gọi initialize_cuda trong main: {USE_CUDA}")
    
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
    speed_label = tk.Label(
        root, text="Chọn tốc độ đọc (0.5 = chậm, 1.0 = chuẩn, 2.0 = nhanh):"
    )
    speed_label.pack(pady=10)
    speed_var = tk.StringVar(value="0.8")
    speed_spinbox = tk.Spinbox(
        root,
        from_=0.5,
        to=2.0,
        increment=0.1,
        textvariable=speed_var,
        width=10,
        format="%.1f"
    )
    speed_spinbox.pack(pady=5)

    # Thêm progress bar và label
    progress_var = tk.IntVar(value=0)
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=1, length=400)
    progress_bar.pack(pady=10)
    progress_label = tk.Label(root, text="Đang xử lý: 0/0")
    progress_label.pack(pady=5)

    # Thay thế ô nhập văn bản test bằng nút test cho tất cả giọng
    test_button = tk.Button(
        root,
        text="Test Tất Cả Giọng",
        command=lambda: threading.Thread(target=test_voice).start(),
    )
    test_button.pack(pady=15)

    # Xóa các biến không cần thiết nữa
    test_text_var = None
    test_text_label = None
    test_text_entry = None

    # Mặc định cập nhật speaker khi chọn model/ngôn ngữ
    language_var.trace_add("write", on_language_change)
    model_var.trace_add("write", on_model_change)
    update_speaker_list()

    ok_button = tk.Button(root, text="OK", command=on_ok_click)
    ok_button.pack(side="bottom", pady=20)

    root.mainloop()

# Hàm chọn file txt (đặt lại vào app4.py vì liên quan trực tiếp giao diện)
def select_txt_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        txt_file_entry.delete(0, tk.END)
        txt_file_entry.insert(0, file_path)

if __name__ == "__main__":
    main()
