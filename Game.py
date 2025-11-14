import pygame

"""
Apparently pygame creators prefer that people do this like big comment thing right here. 
This project took so long, i think I grew a second butt, like i understand why people drink coffee from doing this project.
I dont plan on publishing this as I did use AI and i did take ideas from others. for help so its not all original, it will be in the acknowledgement

"""

import pygame
import random
import sys
import os
from dataclasses import dataclass
from typing import List

# ---------- CONFIG ----------
WIDTH, HEIGHT = 900, 600
FPS = 60

PLAYER_SIZE = 44
PLAYER_SPEED = 5

COLLECTIBLE_SIZE = 16
ASTEROID_SIZE_MIN = 24
ASTEROID_SIZE_MAX = 72

START_ASTEROID_SPEED = 2.0
ASTEROID_SPEED_INCREASE = 0.02  # per difficulty step

START_COLLECTIBLE_SPAWN = 2000  # milliseconds between spawns
START_ASTEROID_SPAWN = 1500  # milliseconds between asteroid spawns

DIFFICULTY_STEP_MS = 7000  # every X ms increase difficulty

HIGH_SCORE_FILE = "highscore.txt"

# Colors
COLOR_BG = (8, 8, 16)
COLOR_PLAYER = (0, 200, 255)
COLOR_COLLECT = (255, 240, 80)
COLOR_ASTEROID = (150, 120, 100)
COLOR_TEXT = (230, 230, 230)
COLOR_HIT = (255, 80, 80)

# ---------- Pygame init ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space-Style Collector (Pygame)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20)
big_font = pygame.font.SysFont("consolas", 48)

# Optional: set up mixer for future sounds (no files included here)
if pygame.mixer:
    try:
        pygame.mixer.init()
    except Exception:
        pass

# ---------- Helpers ----------
def load_high_score() -> int:
    try:
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, "r") as f:
                return int(f.read().strip() or "0")
    except Exception:
        pass
    return 0

def save_high_score(score: int):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass

def clamp(val, lo, hi):
    return max(lo, min(val, hi))

# ---------- Game objects ----------
@dataclass
class Player:
    x: float
    y: float
    size: int = PLAYER_SIZE
    speed: float = PLAYER_SPEED
    color: tuple = COLOR_PLAYER
    rect: pygame.Rect = None

    def __post_init__(self):
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def update_rect(self):
        self.rect.topleft = (int(self.x), int(self.y))

    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = clamp(self.x, 0, WIDTH - self.size)
        self.y = clamp(self.y, 0, HEIGHT - self.size)
        self.update_rect()

    def draw(self, surf):
        # Replace this with an image if you want:
        pygame.draw.rect(surf, self.color, self.rect, border_radius=6)
        # simple "cockpit" highlight
        inner = self.rect.inflate(-self.size//3, -self.size//3)
        pygame.draw.ellipse(surf, (20, 30, 50), inner)

@dataclass
class Collectible:
    x: float
    y: float
    size: int = COLLECTIBLE_SIZE
    color: tuple = COLOR_COLLECT
    rect: pygame.Rect = None

    def __post_init__(self):
        self.rect = pygame.Rect(int(self.x), int(self.y), self.size, self.size)

    def draw(self, surf):
        # Draw a glowing orb-like circle
        pygame.draw.circle(surf, self.color, self.rect.center, self.size // 2)
        pygame.draw.circle(surf, (255,255,255), self.rect.center, max(2, self.size // 6))

@dataclass
class Asteroid:
    x: float
    y: float
    size: int
    vx: float
    vy: float
    color: tuple = COLOR_ASTEROID
    rect: pygame.Rect = None

    def __post_init__(self):
        self.rect = pygame.Rect(int(self.x), int(self.y), int(self.size), int(self.size))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surf):
        # irregular polygon-like ellipse
        pygame.draw.ellipse(surf, self.color, self.rect)
        # simple crater highlight
        crater = pygame.Rect(self.rect.left + self.size//6, self.rect.top + self.size//6,
                            self.size//3, self.size//3)
        pygame.draw.ellipse(surf, (120, 90, 70), crater)

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surf):
        if self.life > 0:
            alpha = clamp(int(255 * (self.life / 1.0)), 0, 255)
            s = pygame.Surface((4,4), pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surf.blit(s, (int(self.x), int(self.y)))

# ---------- Game state ----------
player = Player(WIDTH//2 - PLAYER_SIZE//2, HEIGHT - PLAYER_SIZE - 20)
collectibles: List[Collectible] = []
asteroids: List[Asteroid] = []
particles: List[Particle] = []

score = 0
high_score = load_high_score()
running = True
paused = False
game_over = False

# Timing and difficulty control
last_collect_spawn = pygame.time.get_ticks()
last_asteroid_spawn = pygame.time.get_ticks()
start_time = pygame.time.get_ticks()
last_difficulty_step = start_time

asteroid_speed = START_ASTEROID_SPEED
collectible_spawn_ms = START_COLLECTIBLE_SPAWN
asteroid_spawn_ms = START_ASTEROID_SPAWN

# ---------- Spawn functions ----------
def spawn_collectible():
    # spawn somewhere not too close to the player
    margin = 20
    for _ in range(30):
        x = random.randint(margin, WIDTH - COLLECTIBLE_SIZE - margin)
        y = random.randint(margin, HEIGHT - COLLECTIBLE_SIZE - margin)
        rect = pygame.Rect(x, y, COLLECTIBLE_SIZE, COLLECTIBLE_SIZE)
        if rect.colliderect(player.rect):
            continue
        c = Collectible(x, y)
        collectibles.append(c)
        return

def spawn_asteroid():
    # spawn from any side with velocity toward roughly center area
    size = random.randint(ASTEROID_SIZE_MIN, ASTEROID_SIZE_MAX)
    side = random.choice(["top","bottom","left","right"])
    speed = asteroid_speed + random.random() * 1.4
    if side == "top":
        x = random.randint(0, WIDTH - size)
        y = -size
        vx = (random.random() - 0.5) * 1.2
        vy = speed
    elif side == "bottom":
        x = random.randint(0, WIDTH - size)
        y = HEIGHT + size
        vx = (random.random() - 0.5) * 1.2
        vy = -speed
    elif side == "left":
        x = -size
        y = random.randint(0, HEIGHT - size)
        vx = speed
        vy = (random.random() - 0.5) * 1.2
    else:  # right
        x = WIDTH + size
        y = random.randint(0, HEIGHT - size)
        vx = -speed
        vy = (random.random() - 0.5) * 1.2

    ast = Asteroid(x, y, size, vx, vy)
    asteroids.append(ast)

def create_hit_particles(x, y, color=COLOR_HIT, count=18):
    for _ in range(count):
        angle = random.random() * 2 * 3.14159
        speed = random.random() * 3 + 1
        vx = speed * random.uniform(-1.0,1.0)
        vy = speed * random.uniform(-1.0,1.0)
        p = Particle(x, y, vx, vy, life=0.8 + random.random()*0.6, color=color)
        particles.append(p)

# ---------- Game control helpers ----------
def reset_game():
    global collectibles, asteroids, particles, score, game_over, start_time
    global asteroid_speed, collectible_spawn_ms, asteroid_spawn_ms, last_difficulty_step
    collectibles = []
    asteroids = []
    particles = []
    score = 0
    game_over = False
    asteroid_speed = START_ASTEROID_SPEED
    collectible_spawn_ms = START_COLLECTIBLE_SPAWN
    asteroid_spawn_ms = START_ASTEROID_SPAWN
    player.x = WIDTH//2 - PLAYER_SIZE//2
    player.y = HEIGHT - PLAYER_SIZE - 20
    player.update_rect()
    start_time = pygame.time.get_ticks()
    last_difficulty_step = start_time

# ---------- Main loop ----------
def draw_hud():
    score_surf = font.render(f"Score: {score}", True, COLOR_TEXT)
    screen.blit(score_surf, (10, 10))
    hs_surf = font.render(f"High: {high_score}", True, COLOR_TEXT)
    screen.blit(hs_surf, (10, 34))
    instr = font.render("Arrows/WASD - Move   P - Pause   R - Restart   Esc - Quit", True, (180,180,200))
    screen.blit(instr, (10, HEIGHT - 28))

def draw_game_over():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,180))
    screen.blit(overlay, (0,0))
    txt = big_font.render("GAME OVER", True, (240,80,80))
    txt_rect = txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 60))
    screen.blit(txt, txt_rect)
    score_txt = font.render(f"Final Score: {score}", True, COLOR_TEXT)
    hs_txt = font.render(f"High Score: {high_score}", True, COLOR_TEXT)
    screen.blit(score_txt, (WIDTH//2 - score_txt.get_width()//2, HEIGHT//2))
    screen.blit(hs_txt, (WIDTH//2 - hs_txt.get_width()//2, HEIGHT//2 + 26))
    note = font.render("Press R to play again or Esc to quit", True, (200,200,200))
    screen.blit(note, (WIDTH//2 - note.get_width()//2, HEIGHT//2 + 70))

def update_difficulty(now_ms):
    global asteroid_speed, collectible_spawn_ms, asteroid_spawn_ms, last_difficulty_step
    if now_ms - last_difficulty_step >= DIFFICULTY_STEP_MS:
        last_difficulty_step = now_ms
        asteroid_speed += ASTEROID_SPEED_INCREASE * 10
        # reduce spawn intervals slightly, but keep sensible lower bounds
        collectible_spawn_ms = max(600, int(collectible_spawn_ms * 0.92))
        asteroid_spawn_ms = max(400, int(asteroid_spawn_ms * 0.95))

def handle_collisions():
    global score, game_over, high_score
    # Player - collectible
    for c in collectibles[:]:
        if player.rect.colliderect(c.rect):
            collectibles.remove(c)
            score += 10
            create_hit_particles(c.rect.centerx, c.rect.centery, color=COLOR_COLLECT, count=10)
            # Optionally: play collection sound here

    # Player - asteroid
    for a in asteroids[:]:
        if player.rect.colliderect(a.rect):
            # hit -> game over
            create_hit_particles(player.x + player.size/2, player.y + player.size/2, color=COLOR_HIT, count=28)
            game_over = True
            if score > high_score:
                high_score = score
                save_high_score(high_score)
            return

def cleanup_offscreen_objects():
    # remove asteroids far off-screen to avoid memory growth
    for a in asteroids[:]:
        if a.x < -200 or a.x > WIDTH + 200 or a.y < -200 or a.y > HEIGHT + 200:
            asteroids.remove(a)

    # collectibles don't move; no need to trim

# ---------- Run ----------
reset_game()

while running:
    dt = clock.tick(FPS) / 60.0  # normalize to ~1 per frame at 60fps
    now = pygame.time.get_ticks()

    # ----- events -----
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_p:
                paused = not paused
            elif event.key == pygame.K_r:
                reset_game()

    if not paused and not game_over:
        # ----- input -----
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        # normalize diagonal movement
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
        player.move(dx, dy)

        # ----- spawn logic -----
        if now - last_collect_spawn >= collectible_spawn_ms:
            last_collect_spawn = now
            spawn_collectible()

        if now - last_asteroid_spawn >= asteroid_spawn_ms:
            last_asteroid_spawn = now
            spawn_asteroid()

        # difficulty progression
        update_difficulty(now)

        # ----- update objects -----
        for a in asteroids:
            a.update()
        cleanup_offscreen_objects()

        # particles update
        for p in particles[:]:
            p.update(1.0)  # dt not used here; simple fixed step
            if p.life <= 0:
                particles.remove(p)

        # collisions
        handle_collisions()

    # ----- drawing -----
    screen.fill(COLOR_BG)
    # background stars (simple procedural)
    for i in range(40):
        # draw faint stars with a static-ish pattern seeded by index for cheap effect
        sx = (i * 73) % WIDTH
        sy = ((i * 127) + (now//7)) % HEIGHT
        star_size = ((i * 19) % 3) + 1
        screen.fill((20, 20, 30), (sx, sy, star_size, star_size))

    # draw collectibles and asteroids
    for c in collectibles:
        c.draw(screen)
    for a in asteroids:
        a.draw(screen)
    player.draw(screen)

    # draw particles
    for p in particles:
        p.draw(screen)

    # draw HUD overlays
    draw_hud()
    if paused:
        pause_txt = big_font.render("PAUSED", True, (200,200,255))
        screen.blit(pause_txt, (WIDTH//2 - pause_txt.get_width()//2, HEIGHT//2 - 30))
    if game_over:
        draw_game_over()

    pygame.display.flip()

# quit gracefully
pygame.quit()
sys.exit()
