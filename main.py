import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk
import threading
import time
import datetime
import os
import math

# ==== CONFIG ====
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024
LOG_FOLDER = "logs"
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

# ==== GLOBAL STATE ====
running = False
volume = 0.5
osc_speed = 1.0
osc_type = "volume"
mode = "White Noise"
log_enabled = False
current_log = ""
fade_duration = 2.0  # seconds

# ==== AUDIO GENERATOR ====
def white_noise_generator():
    global running
    t = 0
    while running:
        noise = np.random.normal(0, 1, BLOCK_SIZE).astype(np.float32)
        lfo = math.sin(2 * math.pi * osc_speed * t / SAMPLE_RATE)

        # Apply modulation
        if osc_type == "volume":
            modulated = noise * (volume * (0.5 + 0.5 * lfo))
        else:
            modulated = noise * volume

        t += BLOCK_SIZE
        yield np.stack((modulated, modulated), axis=-1)  # stereo

# ==== AUDIO CALLBACK ====
def audio_callback(outdata, frames, time_info, status):
    try:
        data = next(generator)
        outdata[:] = data
    except StopIteration:
        outdata[:] = np.zeros((frames, 2))

# ==== SESSION LOG ====
def log_session_start():
    global current_log
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    current_log = os.path.join(LOG_FOLDER, f"session_{now}.txt")
    with open(current_log, "w") as f:
        f.write(f"[Session Started] {now}\n")
        f.write(f"Mode: {mode}\n")
        f.write(f"Volume: {volume:.2f}\n")
        f.write(f"Oscillation Speed: {osc_speed:.2f} Hz\n")
        f.write(f"Oscillation Type: {osc_type}\n")

def log_session_end():
    if current_log:
        with open(current_log, "a") as f:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[Session Ended] {now}\n")

# ==== AUDIO THREAD ====
def start_audio():
    global running, generator
    running = True
    generator = white_noise_generator()

    if log_enabled:
        log_session_start()

    with sd.OutputStream(channels=2, callback=audio_callback,
                         samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
        while running:
            time.sleep(0.1)

def stop_audio():
    global running
    # Fade out
    start_volume = volume
    fade_steps = int(fade_duration * 20)
    for step in range(fade_steps):
        time.sleep(fade_duration / fade_steps)
        fade_factor = 1 - (step + 1) / fade_steps
        globals()['volume'] = start_volume * fade_factor
    running = False
    globals()['volume'] = start_volume  # reset
    if log_enabled:
        log_session_end()

# ==== GUI ====
def create_gui():
    def on_start():
        if not running:
            threading.Thread(target=start_audio, daemon=True).start()

    def on_stop():
        if running:
            threading.Thread(target=stop_audio, daemon=True).start()

    def on_volume(val):
        globals()['volume'] = float(val)

    def on_speed(val):
        globals()['osc_speed'] = float(val)

    def on_type(event):
        globals()['osc_type'] = osc_type_var.get()

    def on_mode(event):
        globals()['mode'] = mode_var.get()
        mode_label.config(text=f"Mode: {mode}")

    def on_log_toggle():
        globals()['log_enabled'] = bool(log_var.get())

    root = tk.Tk()
    root.title("Spirit Box Simulator v1")

    # === MODE SELECT ===
    ttk.Label(root, text="Select Mode:").pack(pady=5)
    mode_var = tk.StringVar(value=mode)
    mode_menu = ttk.Combobox(root, textvariable=mode_var, values=["White Noise", "Spirit Box"])
    mode_menu.bind("<<ComboboxSelected>>", on_mode)
    mode_menu.pack()

    mode_label = ttk.Label(root, text=f"Mode: {mode}")
    mode_label.pack(pady=2)

    # === VOLUME ===
    ttk.Label(root, text="Volume").pack()
    ttk.Scale(root, from_=0, to=1, value=volume, orient="horizontal", command=on_volume).pack(fill="x")

    # === SPEED ===
    ttk.Label(root, text="Oscillation Speed (Hz)").pack()
    ttk.Scale(root, from_=0.1, to=5, value=osc_speed, orient="horizontal", command=on_speed).pack(fill="x")

    # === TYPE ===
    ttk.Label(root, text="Oscillation Type").pack()
    osc_type_var = tk.StringVar(value=osc_type)
    osc_type_menu = ttk.Combobox(root, textvariable=osc_type_var, values=["volume"])
    osc_type_menu.bind("<<ComboboxSelected>>", on_type)
    osc_type_menu.pack()

    # === LOG TOGGLE ===
    log_var = tk.IntVar(value=0)
    ttk.Checkbutton(root, text="Enable Logging", variable=log_var, command=on_log_toggle).pack()

    # === START / STOP ===
    ttk.Button(root, text="Start", command=on_start).pack(pady=5)
    ttk.Button(root, text="Stop", command=on_stop).pack()

    root.mainloop()

# === MAIN ===
if __name__ == "__main__":
    create_gui()
