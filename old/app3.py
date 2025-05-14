import tkinter as tk
from tkinter import filedialog, messagebox
import pyttsx3
import os
import threading

# Lấy danh sách voice tiếng Anh
engine = pyttsx3.init()
voices = engine.getProperty('voices')
english_voices = [(voice.name, voice.id) for voice in voices if (
    (hasattr(voice, "languages") and len(voice.languages) > 0 and (
        (isinstance(voice.languages[0], bytes) and 'en' in voice.languages[0].decode('utf-8')) or
        (isinstance(voice.languages[0], str) and 'en' in voice.languages[0])
    )) or 'en' in voice.id
)]

# Hàm để chọn file txt
def select_txt_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        txt_file_entry.delete(0, tk.END)
        txt_file_entry.insert(0, file_path)

# Hàm để chuyển văn bản thành giọng nói
def convert_to_speech_thread():
    try:
        txt_file = txt_file_entry.get()
        speed = float(speed_scale.get())
        language = language_var.get()
        selected_voice_id = None
        if language == 'en' and voice_var.get():
            selected_voice_id = voice_dict.get(voice_var.get())

        if not txt_file:
            messagebox.showerror("Lỗi", "Vui lòng chọn file txt.")
            return

        if not os.path.exists(txt_file):
            messagebox.showerror("Lỗi", "File không tồn tại.")
            return

        with open(txt_file, 'r', encoding='utf-8') as file:
            text = file.read()

        engine = pyttsx3.init()
        engine.setProperty('rate', int(200 * speed))
        if selected_voice_id:
            engine.setProperty('voice', selected_voice_id)
        else:
            voices = engine.getProperty('voices')
            selected_voice = None
            for voice in voices:
                lang_match = False
                if hasattr(voice, "languages") and len(voice.languages) > 0:
                    lang_str = voice.languages[0]
                    if isinstance(lang_str, bytes):
                        lang_str = lang_str.decode('utf-8')
                    if language in lang_str:
                        lang_match = True
                if lang_match or language in voice.id:
                    selected_voice = voice.id
                    break
            if selected_voice:
                engine.setProperty('voice', selected_voice)
            else:
                engine.setProperty('voice', voices[0].id)

        base_filename = os.path.splitext(os.path.basename(txt_file))[0]
        output_filename = base_filename + '.mp3'
        count = 1
        while os.path.exists(output_filename):
            output_filename = f"{base_filename}_{count}.mp3"
            count += 1
        engine.save_to_file(text, output_filename)
        engine.runAndWait()

        messagebox.showinfo("Thành công", f"Giọng nói đã được tạo và lưu tại {output_filename}")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Đã xảy ra lỗi: {str(e)}")
    finally:
        ok_button.config(state=tk.NORMAL, text="OK")

def on_ok_click():
    ok_button.config(state=tk.DISABLED, text="Loading...")
    threading.Thread(target=convert_to_speech_thread).start()

def speak_greeting():
    try:
        language = language_var.get()
        selected_voice_id = None
        if language == 'en' and voice_var.get():
            selected_voice_id = voice_dict.get(voice_var.get())
        greeting = "Hello everyone, Have a nice day"
        engine = pyttsx3.init()
        engine.setProperty('rate', 200)
        if selected_voice_id:
            engine.setProperty('voice', selected_voice_id)
        else:
            voices = engine.getProperty('voices')
            selected_voice = None
            for voice in voices:
                lang_match = False
                if hasattr(voice, "languages") and len(voice.languages) > 0:
                    lang_str = voice.languages[0]
                    if isinstance(lang_str, bytes):
                        lang_str = lang_str.decode('utf-8')
                    if language in lang_str:
                        lang_match = True
                if lang_match or language in voice.id:
                    selected_voice = voice.id
                    break
            if selected_voice:
                engine.setProperty('voice', selected_voice)
            else:
                engine.setProperty('voice', voices[0].id)
        engine.say(greeting)
        engine.runAndWait()
    except Exception as e:
        pass

# Tạo cửa sổ ứng dụng
def main():
    global txt_file_entry, speed_scale, language_var, voice_var, voice_menu, voice_dict, ok_button
    root = tk.Tk()
    root.title("Chuyển Văn Bản Thành Giọng Nói (pyttsx3)")
    root.geometry("400x500")

    txt_file_label = tk.Label(root, text="Chọn file .txt:")
    txt_file_label.pack(pady=10)

    txt_file_entry = tk.Entry(root, width=40)
    txt_file_entry.pack(pady=5)

    txt_file_button = tk.Button(root, text="Chọn File", command=select_txt_file)
    txt_file_button.pack(pady=5)

    language_label = tk.Label(root, text="Chọn Ngôn Ngữ:")
    language_label.pack(pady=10)

    language_var = tk.StringVar(value="vi")
    language_menu = tk.OptionMenu(root, language_var, "vi", "en", "es", "fr", "de")
    language_menu.pack(pady=5)

    # Thêm OptionMenu chọn voice cho tiếng Anh
    voice_label = tk.Label(root, text="Chọn Giọng (English voices):")
    voice_label.pack(pady=10)
    voice_var = tk.StringVar()
    voice_dict = {name: vid for name, vid in english_voices}
    voice_names = list(voice_dict.keys())
    if voice_names:
        voice_var.set(voice_names[0])
    voice_menu = tk.OptionMenu(root, voice_var, *voice_names)
    voice_menu.pack(pady=5)
    # Thêm nút Test Voice ngay dưới chọn giọng
    test_button = tk.Button(root, text="Test Voice", command=lambda: threading.Thread(target=speak_greeting).start())
    test_button.pack(pady=5)
    # Mặc định ẩn nếu không phải tiếng Anh
    if language_var.get() != 'en':
        voice_label.pack_forget()
        voice_menu.pack_forget()
        test_button.pack_forget()

    def on_language_change(*args):
        if language_var.get() == 'en':
            voice_label.pack(pady=10)
            voice_menu.pack(pady=5)
            test_button.pack(pady=5)
        else:
            voice_label.pack_forget()
            voice_menu.pack_forget()
            test_button.pack_forget()
    language_var.trace_add('write', on_language_change)

    speed_label = tk.Label(root, text="Chọn Tốc Độ Nói:")
    speed_label.pack(pady=10)

    speed_scale = tk.Scale(root, from_=0.5, to=2.0, orient="horizontal", resolution=0.1)
    speed_scale.set(1.0)
    speed_scale.pack(pady=10)

    ok_button = tk.Button(root, text="OK", command=on_ok_click)
    ok_button.pack(side="bottom", pady=20)

    root.mainloop()

if __name__ == "__main__":
    main() 