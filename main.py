"""
NEON SNAKE: CYBERRUN
Kerangka game Snake bertema cyberpunk menggunakan pygame-ce.

Instalasi:
    pip install pygame-ce

Struktur folder audio opsional:
    assets/
        start.wav
        eat.wav
        win.wav
        crash.wav
        bgm.ogg
"""

import random
from pathlib import Path

import pygame


# ============================================================
# KONFIGURASI UTAMA
# ============================================================
WIDTH, HEIGHT = 1280, 720
FPS = 60
CELL_SIZE = 28
HUD_HEIGHT = 82
TARGET_LENGTH = 20

BLACK = (0, 0, 0)
DARK_GRID = (29, 19, 66)
CYAN = (0, 245, 255)
NEON_GREEN = (120, 255, 80)
NEON_PURPLE = (196, 80, 255)
WHITE = (235, 250, 255)
RED_NEON = (255, 55, 100)

STATE_MENU = "MENU"
STATE_PLAYING = "PLAYING"
STATE_WIN = "WIN"
STATE_GAME_OVER = "GAME_OVER"


# ============================================================
# UTILITAS VISUAL
# ============================================================
def draw_glow_circle(surface, position, radius, color):
    """Menggambar lingkaran inti dengan beberapa lapisan glow."""
    glow_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    for multiplier, alpha in [(3.0, 18), (2.2, 35), (1.5, 70)]:
        glow_radius = int(radius * multiplier)
        pygame.draw.circle(glow_surface, (*color, alpha), position, glow_radius)

    surface.blit(glow_surface, (0, 0))
    pygame.draw.circle(surface, color, position, radius)
    pygame.draw.circle(surface, WHITE, position, max(2, radius // 3))


def draw_glow_rect(surface, rect, color, border_radius=8):
    """Menggambar rounded rectangle neon dengan efek glow."""
    glow_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    for padding, alpha in [(14, 18), (9, 35), (5, 65)]:
        glow_rect = rect.inflate(padding, padding)
        pygame.draw.rect(
            glow_surface,
            (*color, alpha),
            glow_rect,
            border_radius=border_radius + padding // 2,
        )

    surface.blit(glow_surface, (0, 0))
    pygame.draw.rect(surface, color, rect, border_radius=border_radius)

    # Highlight tipis agar segmen terasa seperti material cybernetic.
    pygame.draw.line(
        surface,
        WHITE,
        (rect.left + 5, rect.top + 4),
        (rect.right - 5, rect.top + 4),
        width=1,
    )


# ============================================================
# CLASS DATA CORE (MAKANAN)
# ============================================================
class DataCore:
    """Representasi data core yang harus dikumpulkan Cyber-Crawler."""

    def __init__(self):
        self.position = (0, 0)

    def spawn(self, snake_body):
        """Memilih posisi acak yang tidak bertabrakan dengan tubuh ular."""
        max_col = WIDTH // CELL_SIZE - 1
        min_row = HUD_HEIGHT // CELL_SIZE + 1
        max_row = HEIGHT // CELL_SIZE - 1

        available_positions = [
            (col, row)
            for col in range(1, max_col)
            for row in range(min_row, max_row)
            if (col, row) not in snake_body
        ]

        if available_positions:
            self.position = random.choice(available_positions)

    def draw(self, surface):
        """Menggambar data core bercahaya."""
        x, y = self.position
        center = (
            x * CELL_SIZE + CELL_SIZE // 2,
            y * CELL_SIZE + CELL_SIZE // 2,
        )
        draw_glow_circle(surface, center, CELL_SIZE // 4, NEON_GREEN)


# ============================================================
# CLASS SNAKE / CYBER-CRAWLER
# ============================================================
class Snake:
    """Mengatur tubuh, gerakan, pertumbuhan, dan collision ular."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Mengembalikan Cyber-Crawler ke kondisi awal."""
        start_x = (WIDTH // CELL_SIZE) // 2
        start_y = (HEIGHT // CELL_SIZE) // 2

        self.body = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y),
        ]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.grow_pending = 0

    def set_direction(self, direction):
        """Mengubah arah, sambil mencegah ular berbalik 180 derajat."""
        dx, dy = direction
        current_dx, current_dy = self.direction

        # Tidak boleh berbalik langsung ke tubuh sendiri.
        if (dx, dy) != (-current_dx, -current_dy):
            self.next_direction = direction

    def move(self):
        """Menggerakkan ular satu sel pada grid."""
        self.direction = self.next_direction

        head_x, head_y = self.body[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        self.body.insert(0, new_head)

        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

    def grow(self):
        """Menambahkan satu panjang tubuh pada langkah berikutnya."""
        self.grow_pending += 1

    def hits_wall(self):
        """Memeriksa collision dengan batas layar atau area HUD."""
        head_x, head_y = self.body[0]

        min_play_row = HUD_HEIGHT // CELL_SIZE + 1
        max_col = WIDTH // CELL_SIZE - 1
        max_row = HEIGHT // CELL_SIZE - 1

        return (
            head_x <= 0
            or head_x >= max_col
            or head_y < min_play_row
            or head_y >= max_row
        )

    def hits_self(self):
        """Memeriksa apakah kepala menabrak tubuh sendiri."""
        return self.body[0] in self.body[1:]

    def draw(self, surface):
        """Menggambar seluruh tubuh ular dengan rounded neon segments."""
        for index, (x, y) in enumerate(self.body):
            margin = 4 if index == 0 else 6
            rect = pygame.Rect(
                x * CELL_SIZE + margin,
                y * CELL_SIZE + margin,
                CELL_SIZE - margin * 2,
                CELL_SIZE - margin * 2,
            )

            # Kepala dibuat sedikit lebih terang.
            color = WHITE if index == 0 else CYAN
            draw_glow_rect(surface, rect, color)


# ============================================================
# CLASS GAME UTAMA
# ============================================================
class Game:
    """Mengatur state machine, input, audio, render, dan game loop."""

    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("NEON SNAKE: CYBERRUN")
        self.clock = pygame.time.Clock()

        # Font monospace memberi nuansa terminal/digital.
        self.font_small = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_medium = pygame.font.SysFont("consolas", 38, bold=True)
        self.font_large = pygame.font.SysFont("consolas", 64, bold=True)

        self.state = STATE_MENU
        self.running = True
        self.score = 0
        self.move_timer = 0.0
        self.bgm_playing = False

        self.snake = Snake()
        self.data_core = DataCore()
        self.data_core.spawn(self.snake.body)

        # Audio akan aman meskipun file belum tersedia.
        self.load_audio()

    # --------------------------------------------------------
    # SISTEM AUDIO
    # --------------------------------------------------------
    def safe_load_sound(self, filename):
        """Memuat sound effect secara aman tanpa menghentikan game."""
        try:
            return pygame.mixer.Sound(str(Path("assets") / filename))
        except (pygame.error, FileNotFoundError):
            print(f"[AUDIO] File tidak ditemukan atau gagal dimuat: {filename}")
            return None

    def load_audio(self):
        """Menyiapkan seluruh aset audio yang dibutuhkan game."""
        self.sfx_start = self.safe_load_sound("start.wav")
        self.sfx_eat = self.safe_load_sound("eat.wav")
        self.sfx_win = self.safe_load_sound("win.wav")
        self.sfx_crash = self.safe_load_sound("crash.wav")

        self.bgm_path = Path("assets") / "bgm.wav"
        try:
            pygame.mixer.music.load(str(self.bgm_path))
            self.bgm_available = True
        except (pygame.error, FileNotFoundError):
            print("[AUDIO] BGM tidak tersedia, game tetap berjalan tanpa musik.")
            self.bgm_available = False

    def play_sound(self, sound):
        """Memainkan SFX bila berhasil dimuat."""
        if sound:
            sound.play()

    def start_bgm(self):
        """Memulai musik latar looping ketika state PLAYING."""
        if self.bgm_available and not self.bgm_playing:
            pygame.mixer.music.play(-1)
            self.bgm_playing = True

    def stop_bgm(self):
        """Menghentikan musik latar ketika permainan selesai."""
        if self.bgm_playing:
            pygame.mixer.music.stop()
            self.bgm_playing = False

    # --------------------------------------------------------
    # GAMEPLAY DAN STATE MACHINE
    # --------------------------------------------------------
    def start_new_game(self):
        """Memulai sesi infiltrasi baru."""
        self.snake.reset()
        self.data_core.spawn(self.snake.body)
        self.score = 0
        self.move_timer = 0.0
        self.state = STATE_PLAYING

        self.play_sound(self.sfx_start)
        self.start_bgm()

    def get_move_interval(self):
        """
        Kecepatan meningkat ketika panjang bertambah.
        Nilai minimum mencegah game menjadi terlalu cepat.
        """
        speed_bonus = (len(self.snake.body) - 3) * 0.007
        return max(0.065, 0.16 - speed_bonus)

    def update_playing(self, delta_time):
        """Menjalankan gerakan dan collision pada state PLAYING."""
        self.move_timer += delta_time

        if self.move_timer < self.get_move_interval():
            return

        self.move_timer = 0.0
        self.snake.move()

        # Crash bila menabrak dinding atau tubuh sendiri.
        if self.snake.hits_wall() or self.snake.hits_self():
            self.state = STATE_GAME_OVER
            self.stop_bgm()
            self.play_sound(self.sfx_crash)
            return

        # Mengambil Data Core.
        if self.snake.body[0] == self.data_core.position:
            self.snake.grow()
            self.score += 100
            self.play_sound(self.sfx_eat)

            # Karena pertumbuhan terlihat setelah langkah berikutnya,
            # target dicek dengan panjang aktual + pertumbuhan tertunda.
            future_length = len(self.snake.body) + self.snake.grow_pending

            if future_length >= TARGET_LENGTH:
                self.state = STATE_WIN
                self.stop_bgm()
                self.play_sound(self.sfx_win)
            else:
                self.data_core.spawn(self.snake.body)

    # --------------------------------------------------------
    # INPUT PEMAIN
    # --------------------------------------------------------
    def handle_events(self):
        """Menangani event keyboard dan penutupan jendela."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                # SPACE memulai ulang dari menu, menang, atau crash.
                if event.key == pygame.K_SPACE and self.state != STATE_PLAYING:
                    self.start_new_game()

                if self.state == STATE_PLAYING:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.snake.set_direction((0, -1))
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.snake.set_direction((0, 1))
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.snake.set_direction((-1, 0))
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.snake.set_direction((1, 0))

    # --------------------------------------------------------
    # SISTEM RENDER
    # --------------------------------------------------------
    def draw_grid(self):
        """Menggambar grid tipis biru gelap di atas latar hitam."""
        for x in range(0, WIDTH + 1, CELL_SIZE):
            pygame.draw.line(self.screen, DARK_GRID, (x, 0), (x, HEIGHT), 1)

        for y in range(0, HEIGHT + 1, CELL_SIZE):
            pygame.draw.line(self.screen, DARK_GRID, (0, y), (WIDTH, y), 1)

    def draw_text(self, text, font, color, center, glow=True):
        """Menggambar teks terminal dengan efek glow sederhana."""
        rendered = font.render(text, True, color)
        rect = rendered.get_rect(center=center)

        if glow:
            glow_surface = font.render(text, True, color)
            glow_surface.set_alpha(70)

            for offset_x, offset_y in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                glow_rect = glow_surface.get_rect(
                    center=(center[0] + offset_x, center[1] + offset_y)
                )
                self.screen.blit(glow_surface, glow_rect)

        self.screen.blit(rendered, rect)

    def draw_hud(self):
        """Menampilkan informasi SCORE, LENGTH, dan TARGET di bagian atas."""
        hud_rect = pygame.Rect(0, 0, WIDTH, HUD_HEIGHT)
        pygame.draw.rect(self.screen, (4, 3, 14), hud_rect)
        pygame.draw.line(self.screen, CYAN, (0, HUD_HEIGHT), (WIDTH, HUD_HEIGHT), 2)

        score_text = f"SCORE: {self.score:05d}"
        length_text = f"LENGTH: {len(self.snake.body):02d}"
        target_text = f"TARGET: {TARGET_LENGTH:02d}"

        self.draw_text(score_text, self.font_small, CYAN, (160, 40))
        self.draw_text(length_text, self.font_small, NEON_GREEN, (WIDTH // 2, 40))
        self.draw_text(target_text, self.font_small, NEON_PURPLE, (WIDTH - 160, 40))

    def draw_menu(self):
        """Menggambar halaman MAIN MENU."""
        pulse = (pygame.time.get_ticks() // 500) % 2 == 0

        self.draw_text(
            "NEON SNAKE: CYBERRUN",
            self.font_large,
            CYAN,
            (WIDTH // 2, HEIGHT // 2 - 70),
        )
        self.draw_text(
            "CYBERNETIC INFILTRATION PROTOCOL",
            self.font_small,
            NEON_PURPLE,
            (WIDTH // 2, HEIGHT // 2),
        )

        if pulse:
            self.draw_text(
                "PRESS [SPACE] TO INITIATE HACK",
                self.font_medium,
                NEON_GREEN,
                (WIDTH // 2, HEIGHT // 2 + 100),
            )

    def draw_end_screen(self, title, color, subtitle):
        """Menggambar layar akhir untuk state WIN atau GAME OVER."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        self.draw_text(title, self.font_large, color, (WIDTH // 2, HEIGHT // 2 - 45))
        self.draw_text(
            subtitle,
            self.font_small,
            WHITE,
            (WIDTH // 2, HEIGHT // 2 + 25),
        )

        pulse = (pygame.time.get_ticks() // 500) % 2 == 0
        if pulse:
            self.draw_text(
                "PRESS [SPACE] TO REINITIATE",
                self.font_medium,
                NEON_GREEN,
                (WIDTH // 2, HEIGHT // 2 + 100),
            )

    def draw(self):
        """Merender tampilan berdasarkan state game saat ini."""
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
                    RED_NEON,
                    "INTRUSION DETECTED // CONNECTION TERMINATED",
                )

        pygame.display.flip()

    # --------------------------------------------------------
    # GAME LOOP UTAMA
    # --------------------------------------------------------
    def run(self):
        """Loop utama aplikasi."""
        while self.running:
            delta_time = self.clock.tick(FPS) / 1000.0

            self.handle_events()

            if self.state == STATE_PLAYING:
                self.update_playing(delta_time)

            self.draw()

        self.stop_bgm()
        pygame.quit()


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    Game().run()