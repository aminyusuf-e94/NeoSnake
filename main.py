"""
NEON SNAKE: CYBERRUN
Game cyberpunk Snake berbasis pygame-ce dengan audio prosedural mandiri.

Instalasi:
    pip install pygame-ce

Jalankan:
    python main.py

Catatan:
- Folder assets/ akan dibuat otomatis.
- Semua file audio .wav dibuat secara otomatis saat pertama kali game dijalankan.
- Tidak membutuhkan file audio eksternal.
"""

from __future__ import annotations

import math
import random
import struct
import threading
import wave
from pathlib import Path
from typing import Callable, Optional

import pygame


# ============================================================
# KONFIGURASI GLOBAL
# ============================================================

WIDTH = 1280
HEIGHT = 720
FPS = 60

CELL_SIZE = 28
HUD_HEIGHT = 84
TARGET_LENGTH = 20

BLACK = (0, 0, 0)
DARK_GRID = (29, 19, 66)
CYAN = (0, 245, 255)
NEON_GREEN = (125, 255, 80)
NEON_PURPLE = (190, 80, 255)
NEON_RED = (255, 45, 100)
WHITE = (230, 250, 255)
HUD_BACKGROUND = (5, 4, 16)

STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_WIN = "WIN"
STATE_GAME_OVER = "GAME_OVER"

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


# ============================================================
# PROCEDURAL AUDIO ENGINE
# ============================================================

class ProceduralAudio:
    """
    Audio engine mandiri yang menghasilkan WAV menggunakan
    wave, struct, dan sintesis matematika berbasis math.sin().
    """

    SAMPLE_RATE = 44_100
    MAX_AMPLITUDE = 32_767

    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir

    def ensure_assets(self) -> None:
        """Membuat folder audio dan file WAV yang belum tersedia."""
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        audio_generators: dict[str, Callable[[], None]] = {
            "start.wav": self.generate_start_sound,
            "eat.wav": self.generate_eat_sound,
            "win.wav": self.generate_win_sound,
            "crash.wav": self.generate_crash_sound,
            "bgm.wav": self.generate_bgm_loop,
        }

        for filename, generator in audio_generators.items():
            file_path = self.assets_dir / filename

            if not file_path.exists():
                try:
                    generator()
                    print(f"[AUDIO] Audio prosedural dibuat: {filename}")
                except OSError as error:
                    print(f"[AUDIO] Gagal membuat {filename}: {error}")

    def write_wave(
        self,
        filename: str,
        duration: float,
        sample_function: Callable[[float, int], float],
    ) -> None:
        """
        Menulis satu file mono WAV 16-bit.

        sample_function menerima:
        - waktu saat ini dalam detik
        - index sample
        dan mengembalikan nilai audio antara -1.0 sampai 1.0.
        """
        file_path = self.assets_dir / filename
        total_samples = int(self.SAMPLE_RATE * duration)
        frames = bytearray()

        for index in range(total_samples):
            time_value = index / self.SAMPLE_RATE
            signal = sample_function(time_value, index)

            # Membatasi sinyal agar tidak clipping.
            signal = max(-1.0, min(1.0, signal))
            sample_value = int(signal * self.MAX_AMPLITUDE)

            frames.extend(struct.pack("<h", sample_value))

        with wave.open(str(file_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.SAMPLE_RATE)
            wav_file.writeframes(frames)

    def generate_start_sound(self) -> None:
        """Membuat efek power-up dengan frekuensi yang naik cepat."""
        duration = 0.42

        def sample_function(time_value: float, _: int) -> float:
            progress = time_value / duration
            frequency = 180 + (1_250 * progress)
            envelope = math.sin(math.pi * progress) ** 0.7
            signal = math.sin(2 * math.pi * frequency * time_value)
            harmonic = math.sin(2 * math.pi * frequency * 2 * time_value) * 0.25
            return (signal + harmonic) * envelope * 0.48

        self.write_wave("start.wav", duration, sample_function)

    def generate_eat_sound(self) -> None:
        """Membuat blip/zap digital bernada tinggi saat Data Core dimakan."""
        duration = 0.16

        def sample_function(time_value: float, _: int) -> float:
            progress = time_value / duration
            frequency = 1_400 - (650 * progress)
            envelope = (1.0 - progress) ** 2
            square_wave = 1.0 if math.sin(
                2 * math.pi * frequency * time_value
            ) > 0 else -1.0

            sine_wave = math.sin(2 * math.pi * frequency * 1.5 * time_value)
            return (square_wave * 0.55 + sine_wave * 0.25) * envelope * 0.42

        self.write_wave("eat.wav", duration, sample_function)

    def generate_win_sound(self) -> None:
        """Membuat chord kemenangan synth empat nada."""
        duration = 1.6
        notes = [523.25, 659.25, 783.99, 1046.50]

        def sample_function(time_value: float, _: int) -> float:
            note_index = min(int(time_value / 0.4), len(notes) - 1)
            note_start = note_index * 0.4
            local_time = time_value - note_start
            frequency = notes[note_index]

            attack = min(local_time / 0.03, 1.0)
            release = max(0.0, 1.0 - (local_time / 0.4))
            envelope = attack * (release ** 0.65)

            fundamental = math.sin(2 * math.pi * frequency * local_time)
            fifth = math.sin(2 * math.pi * frequency * 1.5 * local_time) * 0.32
            octave = math.sin(2 * math.pi * frequency * 2 * local_time) * 0.18

            return (fundamental + fifth + octave) * envelope * 0.34

        self.write_wave("win.wav", duration, sample_function)

    def generate_crash_sound(self) -> None:
        """Membuat power-down/glitch dengan noise deterministik."""
        duration = 0.75

        def sample_function(time_value: float, index: int) -> float:
            progress = time_value / duration
            frequency = 180 - (150 * progress)
            envelope = (1.0 - progress) ** 1.3

            # Pseudo-noise dari operasi matematika sederhana.
            noise = math.sin(index * 12.9898) * 43_758.5453
            noise = (noise - math.floor(noise)) * 2.0 - 1.0

            glitch_gate = 1.0 if int(time_value * 42) % 3 != 0 else 0.12
            tone = math.sin(2 * math.pi * frequency * time_value)

            return (tone * 0.45 + noise * 0.55) * envelope * glitch_gate * 0.45

        self.write_wave("crash.wav", duration, sample_function)

    def generate_bgm_loop(self) -> None:
        """
        Membuat loop Synthwave 8 detik.
        Setiap not memiliki envelope agar transisi akhir loop halus.
        """
        duration = 8.0
        step_duration = 0.5

        bass_notes = [
            55.00, 55.00, 65.41, 55.00,
            73.42, 73.42, 65.41, 55.00,
            55.00, 55.00, 82.41, 73.42,
            65.41, 65.41, 55.00, 49.00,
        ]

        lead_notes = [
            220.00, 0.00, 261.63, 0.00,
            293.66, 0.00, 261.63, 0.00,
            220.00, 0.00, 329.63, 0.00,
            293.66, 0.00, 261.63, 0.00,
        ]

        def sample_function(time_value: float, _: int) -> float:
            step_index = min(
                int(time_value / step_duration),
                len(bass_notes) - 1,
            )

            local_time = time_value - (step_index * step_duration)
            phase = local_time / step_duration

            # Envelope menyusut menjelang akhir setiap step.
            bass_envelope = min(phase / 0.02, 1.0) * (1.0 - phase) ** 0.35
            bass_frequency = bass_notes[step_index]

            bass = math.sin(2 * math.pi * bass_frequency * local_time)
            bass += math.sin(
                2 * math.pi * bass_frequency * 2 * local_time
            ) * 0.28
            bass += math.sin(
                2 * math.pi * bass_frequency * 0.5 * local_time
            ) * 0.18

            lead_frequency = lead_notes[step_index]
            lead = 0.0

            if lead_frequency > 0:
                lead_envelope = min(phase / 0.05, 1.0) * (1.0 - phase) ** 1.4
                lead = math.sin(
                    2 * math.pi * lead_frequency * local_time
                ) * lead_envelope
                lead += math.sin(
                    2 * math.pi * lead_frequency * 2 * local_time
                ) * lead_envelope * 0.22

            # Kick sederhana di awal setiap beat.
            beat_position = time_value % 1.0
            kick = 0.0

            if beat_position < 0.12:
                kick_progress = beat_position / 0.12
                kick_frequency = 130 - (85 * kick_progress)
                kick = math.sin(
                    2 * math.pi * kick_frequency * beat_position
                )
                kick *= (1.0 - kick_progress) ** 2

            # Hi-hat sintetis di pertengahan beat.
            half_beat_position = time_value % 0.5
            hat = 0.0

            if half_beat_position < 0.04:
                hat_noise = math.sin(
                    (_ * 71.43) + math.sin(_ * 0.17)
                )
                hat = hat_noise * (1.0 - half_beat_position / 0.04)

            return (
                bass * bass_envelope * 0.30
                + lead * 0.13
                + kick * 0.24
                + hat * 0.04
            )

        self.write_wave("bgm.wav", duration, sample_function)


# ============================================================
# UTILITAS VISUAL NEON
# ============================================================

def draw_glow_rect(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    radius: int = 8,
) -> None:
    """Menggambar rounded rectangle dengan glow neon berlapis."""
    glow_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    for padding, alpha in ((16, 16), (10, 32), (5, 70)):
        expanded_rect = rect.inflate(padding, padding)

        pygame.draw.rect(
            glow_surface,
            (*color, alpha),
            expanded_rect,
            border_radius=radius + padding // 2,
        )

    surface.blit(glow_surface, (0, 0))
    pygame.draw.rect(surface, color, rect, border_radius=radius)

    pygame.draw.line(
        surface,
        WHITE,
        (rect.left + 4, rect.top + 3),
        (rect.right - 4, rect.top + 3),
        width=1,
    )


def draw_glow_circle(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
) -> None:
    """Menggambar Data Core berupa lingkaran bercahaya."""
    glow_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    for multiplier, alpha in ((3.2, 18), (2.2, 38), (1.5, 85)):
        glow_radius = int(radius * multiplier)

        pygame.draw.circle(
            glow_surface,
            (*color, alpha),
            center,
            glow_radius,
        )

    surface.blit(glow_surface, (0, 0))
    pygame.draw.circle(surface, color, center, radius)
    pygame.draw.circle(surface, WHITE, center, max(2, radius // 3))


# ============================================================
# CLASS DATA CORE
# ============================================================

class DataCore:
    """Mewakili item Data Core yang harus dikumpulkan pemain."""

    def __init__(self) -> None:
        self.position: tuple[int, int] = (0, 0)

    def spawn(self, snake_body: list[tuple[int, int]]) -> None:
        """Spawn di posisi grid yang tidak ditempati tubuh ular."""
        min_row = (HUD_HEIGHT // CELL_SIZE) + 1
        max_col = (WIDTH // CELL_SIZE) - 1
        max_row = (HEIGHT // CELL_SIZE) - 1

        valid_positions = [
            (column, row)
            for column in range(1, max_col)
            for row in range(min_row, max_row)
            if (column, row) not in snake_body
        ]

        if valid_positions:
            self.position = random.choice(valid_positions)

    def draw(self, surface: pygame.Surface) -> None:
        """Menggambar Data Core dengan efek denyut halus."""
        grid_x, grid_y = self.position
        pulse = math.sin(pygame.time.get_ticks() * 0.008) * 2

        center = (
            grid_x * CELL_SIZE + CELL_SIZE // 2,
            grid_y * CELL_SIZE + CELL_SIZE // 2,
        )

        draw_glow_circle(
            surface,
            center,
            int(CELL_SIZE // 4 + pulse),
            NEON_GREEN,
        )


# ============================================================
# CLASS SNAKE / CYBER-CRAWLER
# ============================================================

class Snake:
    """Mengatur posisi, arah, pertumbuhan, dan collision ular."""

    def __init__(self) -> None:
        self.body: list[tuple[int, int]] = []
        self.direction: tuple[int, int] = (1, 0)
        self.next_direction: tuple[int, int] = (1, 0)
        self.grow_pending = 0
        self.reset()

    def reset(self) -> None:
        """Mengembalikan ular ke posisi awal."""
        center_x = (WIDTH // CELL_SIZE) // 2
        center_y = (HEIGHT // CELL_SIZE) // 2

        self.body = [
            (center_x, center_y),
            (center_x - 1, center_y),
            (center_x - 2, center_y),
        ]

        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.grow_pending = 0

    def set_direction(self, new_direction: tuple[int, int]) -> None:
        """Mencegah ular berbalik arah 180 derajat."""
        current_x, current_y = self.direction
        new_x, new_y = new_direction

        if (new_x, new_y) != (-current_x, -current_y):
            self.next_direction = new_direction

    def move(self) -> None:
        """Menggerakkan kepala dan menghapus ekor bila tidak tumbuh."""
        self.direction = self.next_direction

        head_x, head_y = self.body[0]
        direction_x, direction_y = self.direction

        new_head = (
            head_x + direction_x,
            head_y + direction_y,
        )

        self.body.insert(0, new_head)

        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

    def grow(self) -> None:
        """Menjadwalkan pertumbuhan satu segmen."""
        self.grow_pending += 1

    def hits_wall(self) -> bool:
        """Memeriksa collision dengan area di luar arena."""
        head_x, head_y = self.body[0]

        min_row = (HUD_HEIGHT // CELL_SIZE) + 1
        max_col = (WIDTH // CELL_SIZE) - 1
        max_row = (HEIGHT // CELL_SIZE) - 1

        return (
            head_x <= 0
            or head_x >= max_col
            or head_y < min_row
            or head_y >= max_row
        )

    def hits_self(self) -> bool:
        """Memeriksa collision kepala dengan badan sendiri."""
        return self.body[0] in self.body[1:]

    def draw(self, surface: pygame.Surface) -> None:
        """Menggambar Cyber-Crawler dengan rounded glow cyan."""
        for index, (grid_x, grid_y) in enumerate(self.body):
            margin = 4 if index == 0 else 6

            segment_rect = pygame.Rect(
                grid_x * CELL_SIZE + margin,
                grid_y * CELL_SIZE + margin,
                CELL_SIZE - margin * 2,
                CELL_SIZE - margin * 2,
            )

            segment_color = WHITE if index == 0 else CYAN
            draw_glow_rect(surface, segment_rect, segment_color)


# ============================================================
# CLASS GAME UTAMA
# ============================================================

class Game:
    """State machine utama untuk NEON SNAKE: CYBERRUN."""

    def __init__(self) -> None:
        # Audio dibuat pada worker thread sebelum mixer diinisialisasi.
        audio_engine = ProceduralAudio(ASSETS_DIR)
        asset_thread = threading.Thread(
            target=audio_engine.ensure_assets,
            daemon=False,
        )
        asset_thread.start()
        asset_thread.join()

        pygame.init()

        self.audio_available = self.initialize_audio()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("NEON SNAKE: CYBERRUN")

        self.clock = pygame.time.Clock()
        self.running = True
        self.state = STATE_MENU

        self.font_small = pygame.font.SysFont(
            "consolas",
            22,
            bold=True,
        )
        self.font_medium = pygame.font.SysFont(
            "consolas",
            36,
            bold=True,
        )
        self.font_large = pygame.font.SysFont(
            "consolas",
            62,
            bold=True,
        )

        self.snake = Snake()
        self.data_core = DataCore()
        self.data_core.spawn(self.snake.body)

        self.score = 0
        self.move_timer = 0.0

        self.sfx_start: Optional[pygame.mixer.Sound] = None
        self.sfx_eat: Optional[pygame.mixer.Sound] = None
        self.sfx_win: Optional[pygame.mixer.Sound] = None
        self.sfx_crash: Optional[pygame.mixer.Sound] = None

        if self.audio_available:
            self.load_audio_files()
            self.start_bgm()

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    def initialize_audio(self) -> bool:
        """Menginisialisasi mixer tanpa membuat game crash bila gagal."""
        try:
            pygame.mixer.init(
                frequency=ProceduralAudio.SAMPLE_RATE,
                size=-16,
                channels=1,
                buffer=512,
            )
            return True
        except pygame.error as error:
            print(f"[AUDIO] Mixer tidak dapat diaktifkan: {error}")
            return False

    def load_audio_files(self) -> None:
        """Memuat SFX dan BGM yang dihasilkan oleh ProceduralAudio."""
        try:
            self.sfx_start = pygame.mixer.Sound(
                str(ASSETS_DIR / "start.wav")
            )
            self.sfx_eat = pygame.mixer.Sound(
                str(ASSETS_DIR / "eat.wav")
            )
            self.sfx_win = pygame.mixer.Sound(
                str(ASSETS_DIR / "win.wav")
            )
            self.sfx_crash = pygame.mixer.Sound(
                str(ASSETS_DIR / "crash.wav")
            )

            pygame.mixer.music.load(str(ASSETS_DIR / "bgm.wav"))
        except (pygame.error, OSError) as error:
            print(f"[AUDIO] Gagal memuat audio: {error}")
            self.audio_available = False

    def play_sound(self, sound: Optional[pygame.mixer.Sound]) -> None:
        """Memainkan SFX bila mixer dan file audio tersedia."""
        if self.audio_available and sound is not None:
            try:
                sound.play()
            except pygame.error as error:
                print(f"[AUDIO] Gagal memainkan SFX: {error}")

    def start_bgm(self) -> None:
        """Memutar BGM sejak state MENU dan melakukan looping tanpa henti."""
        if self.audio_available:
            try:
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.32)
            except pygame.error as error:
                print(f"[AUDIO] Gagal memutar BGM: {error}")

    # --------------------------------------------------------
    # GAMEPLAY
    # --------------------------------------------------------

    def start_new_game(self) -> None:
        """Menginisialisasi ulang seluruh data sesi permainan."""
        self.snake.reset()
        self.data_core.spawn(self.snake.body)

        self.score = 0
        self.move_timer = 0.0
        self.state = STATE_PLAYING

        self.play_sound(self.sfx_start)

    def get_move_interval(self) -> float:
        """Mengurangi interval gerak ketika ular bertambah panjang."""
        speed_bonus = max(0, len(self.snake.body) - 3) * 0.0065
        return max(0.060, 0.155 - speed_bonus)

    def update_playing(self, delta_time: float) -> None:
        """Menjalankan pergerakan, collision, dan pengumpulan Data Core."""
        self.move_timer += delta_time

        if self.move_timer < self.get_move_interval():
            return

        self.move_timer = 0.0
        self.snake.move()

        if self.snake.hits_wall() or self.snake.hits_self():
            self.state = STATE_GAME_OVER
            self.play_sound(self.sfx_crash)
            return

        if self.snake.body[0] == self.data_core.position:
            self.snake.grow()
            self.score += 100
            self.play_sound(self.sfx_eat)

            future_length = len(self.snake.body) + self.snake.grow_pending

            if future_length >= TARGET_LENGTH:
                self.state = STATE_WIN
                self.play_sound(self.sfx_win)
            else:
                self.data_core.spawn(self.snake.body)

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    def handle_events(self) -> None:
        """Menangani keyboard dan event penutupan aplikasi."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_ESCAPE:
                self.running = False

            if event.key == pygame.K_SPACE and self.state != STATE_PLAYING:
                self.start_new_game()

            if self.state != STATE_PLAYING:
                continue

            if event.key in (pygame.K_UP, pygame.K_w):
                self.snake.set_direction((0, -1))

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.snake.set_direction((0, 1))

            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.snake.set_direction((-1, 0))

            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.snake.set_direction((1, 0))

    # --------------------------------------------------------
    # RENDERING
    # --------------------------------------------------------

    def draw_grid(self) -> None:
        """Menggambar Matrix Grid biru gelap di atas background hitam."""
        for x_position in range(0, WIDTH + 1, CELL_SIZE):
            pygame.draw.line(
                self.screen,
                DARK_GRID,
                (x_position, 0),
                (x_position, HEIGHT),
                1,
            )

        for y_position in range(0, HEIGHT + 1, CELL_SIZE):
            pygame.draw.line(
                self.screen,
                DARK_GRID,
                (0, y_position),
                (WIDTH, y_position),
                1,
            )

    def draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        center: tuple[int, int],
        alpha: int = 255,
    ) -> None:
        """Menggambar teks monospace dengan glow dan alpha blending."""
        text_surface = font.render(text, True, color)
        text_surface.set_alpha(alpha)
        text_rect = text_surface.get_rect(center=center)

        glow_surface = font.render(text, True, color)
        glow_surface.set_alpha(max(0, alpha // 4))

        for offset_x, offset_y in (
            (-4, 0),
            (4, 0),
            (0, -4),
            (0, 4),
        ):
            glow_rect = glow_surface.get_rect(
                center=(center[0] + offset_x, center[1] + offset_y)
            )
            self.screen.blit(glow_surface, glow_rect)

        self.screen.blit(text_surface, text_rect)

    def draw_hud(self) -> None:
        """Menggambar panel informasi SCORE, LENGTH, dan TARGET."""
        hud_rect = pygame.Rect(0, 0, WIDTH, HUD_HEIGHT)

        pygame.draw.rect(self.screen, HUD_BACKGROUND, hud_rect)
        pygame.draw.line(
            self.screen,
            CYAN,
            (0, HUD_HEIGHT),
            (WIDTH, HUD_HEIGHT),
            2,
        )

        score_text = f"SCORE: {self.score:05d}"
        length_text = f"LENGTH: {len(self.snake.body):02d}"
        target_text = f"TARGET: {TARGET_LENGTH:02d}"

        self.draw_text(
            score_text,
            self.font_small,
            CYAN,
            (160, 42),
        )
        self.draw_text(
            length_text,
            self.font_small,
            NEON_GREEN,
            (WIDTH // 2, 42),
        )
        self.draw_text(
            target_text,
            self.font_small,
            NEON_PURPLE,
            (WIDTH - 160, 42),
        )

    def pulse_alpha(self, speed: float = 0.005) -> int:
        """Menghasilkan nilai alpha berkedip lembut menggunakan sinus."""
        wave_value = (math.sin(pygame.time.get_ticks() * speed) + 1.0) / 2.0
        return int(90 + wave_value * 165)

    def draw_menu(self) -> None:
        """Merender Main Menu."""
        self.draw_text(
            "NEON SNAKE: CYBERRUN",
            self.font_large,
            CYAN,
            (WIDTH // 2, HEIGHT // 2 - 85),
        )
        self.draw_text(
            "CYBERNETIC INFILTRATION PROTOCOL",
            self.font_small,
            NEON_PURPLE,
            (WIDTH // 2, HEIGHT // 2),
        )
        self.draw_text(
            "PRESS [SPACE] TO INITIATE HACK",
            self.font_medium,
            NEON_GREEN,
            (WIDTH // 2, HEIGHT // 2 + 115),
            self.pulse_alpha(),
        )

    def draw_end_screen(
        self,
        title: str,
        color: tuple[int, int, int],
        subtitle: str,
    ) -> None:
        """Merender layar WIN atau GAME OVER."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        self.draw_text(
            title,
            self.font_large,
            color,
            (WIDTH // 2, HEIGHT // 2 - 55),
        )
        self.draw_text(
            subtitle,
            self.font_small,
            WHITE,
            (WIDTH // 2, HEIGHT // 2 + 20),
        )
        self.draw_text(
            "PRESS [SPACE] TO REINITIATE",
            self.font_medium,
            NEON_GREEN,
            (WIDTH // 2, HEIGHT // 2 + 110),
            self.pulse_alpha(),
        )

    def draw(self) -> None:
        """Merender frame berdasarkan state machine aktif."""
        self.screen.fill(BLACK)
        self.draw_grid()

        if self.state == STATE_MENU:
            self.draw_menu()
        else:
            self.draw_hud()
            self.data_core.draw(self.screen)
            self.snake.draw(self.screen)

            if self.state == STATE_WIN:
                self.draw_end_screen(
                    "SYSTEM OVERRIDDEN",
                    NEON_GREEN,
                    "LEVEL CLEARED // NETWORK ACCESS GRANTED",
                )

            elif self.state == STATE_GAME_OVER:
                self.draw_end_screen(
                    "SYSTEM CRASH",
                    NEON_RED,
                    "INTRUSION DETECTED // CONNECTION TERMINATED",
                )

        pygame.display.flip()

    # --------------------------------------------------------
    # GAME LOOP
    # --------------------------------------------------------

    def run(self) -> None:
        """Loop utama game."""
        while self.running:
            delta_time = self.clock.tick(FPS) / 1000.0

            self.handle_events()

            if self.state == STATE_PLAYING:
                self.update_playing(delta_time)

            self.draw()

        if self.audio_available:
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass

        pygame.quit()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    Game().run()