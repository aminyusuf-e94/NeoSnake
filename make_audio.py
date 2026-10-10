import math
import os
import struct
import wave

os.makedirs("assets", exist_ok=True)


def generate_sound(filename, freq, duration, sound_type="sine"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)

    filepath = os.path.join("assets", filename)
    with wave.open(filepath, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        for i in range(n_samples):
            t = i / sample_rate

            if sound_type == "eat":
                current_freq = freq + (i / n_samples) * 500
                value = int(32767 * 0.3 * math.sin(2 * math.pi * current_freq * t))
            elif sound_type == "crash":
                current_freq = max(40, freq - (i / n_samples) * 300)
                value = int(32767 * 0.4 * math.sin(2 * math.pi * current_freq * t))
            elif sound_type == "win":
                step = int(t * 12) % 4
                current_freq = freq * (1 + step * 0.25)
                value = int(32767 * 0.3 * math.sin(2 * math.pi * current_freq * t))
            elif sound_type == "bgm":
                # Synthwave Arpeggio Loop (A-C-E-G)
                notes = [110.0, 130.81, 164.81, 196.0]
                step = int(t * 8) % len(notes)
                current_freq = notes[step]
                envelope = 0.3 * (1.0 - (t * 8 - int(t * 8)))
                value = int(32767 * envelope * math.sin(2 * math.pi * current_freq * t))
            else:
                value = int(32767 * 0.3 * math.sin(2 * math.pi * freq * t))

            data = struct.pack("<h", value)
            wav_file.writeframesraw(data)

    print(f"[SUCCESS] Berhasil membuat: {filepath}")


generate_sound("start.wav", 440, 0.3, "start")
generate_sound("eat.wav", 520, 0.12, "eat")
generate_sound("win.wav", 440, 0.8, "win")
generate_sound("crash.wav", 180, 0.5, "crash")
generate_sound("bgm.wav", 110, 4.0, "bgm")  # Musik Latar Loop 4 Detik