import time
import pygame

pygame.mixer.init()

print("--- MENGETES EFEK SUARA (SFX) ---")
try:
    eat_sfx = pygame.mixer.Sound("assets/eat.wav")
    eat_sfx.play()
    print("[OK] Suara makan berbunyi!")
    time.sleep(1)
except Exception as e:
    print(f"[ERROR] Gagal memuat eat.wav: {e}")

print("--- MENGETES MUSIK LATAR (BGM) ---")
try:
    pygame.mixer.music.load("assets/bgm.wav")
    pygame.mixer.music.play()
    print("[OK] Musik BGM berputar selama 4 detik...")
    time.sleep(4)
except Exception as e:
    print(f"[ERROR] Gagal memuat bgm.wav: {e}")

pygame.quit()