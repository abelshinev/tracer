import pygame
import win32api
import win32con
import win32gui
import sys
from vision import HandTracker  # Importing your clean API

# Initialize Pygame
pygame.init()

WIDTH, HEIGHT = 1780, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)

# Define Colors
FUCHSIA = (255, 0, 128)
DARK_GREEN = (0, 100, 0)
NEON_GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
WHITE = (255, 255, 255)

# Windows Transparency Magic
hwnd = pygame.display.get_surface_id() if hasattr(pygame.display, 'get_surface_id') else pygame.display.get_wm_info()['window']
current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, current_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*FUCHSIA), 0, win32con.LWA_COLORKEY)

font = pygame.font.SysFont("Arial", 20, bold=True)
clock = pygame.time.Clock()

# --- Initialize the Vision Module ---
print("Warming up Vision API...")
tracker = HandTracker()
running = True

print("Phase 2 Integration: Overlay should now track both hands independently.")

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False

    screen.fill(FUCHSIA)

    # 1. PULL DATA STATE (The API Handshake)
    state = tracker.get_tracking_state(WIDTH, HEIGHT)
    
    # Draw UI Header Box
    pygame.draw.rect(screen, DARK_GREEN, (10, 10, 450, 90), border_radius=10)
    text_surface = font.render("[Phase 2: Dual Hand Overlay]", True, NEON_GREEN)
    screen.blit(text_surface, (20, 15))

    # 2. RENDER RIGHT HAND (The Cursor)
    if "Right" in state.hands:
        rh = state.hands["Right"]
        pygame.draw.circle(screen, NEON_GREEN, (rh.x, rh.y), 25, 0)
        pygame.draw.circle(screen, WHITE, (rh.x, rh.y), 35, 2)
        
        status_r = font.render(f"Right Cursor: X={rh.x}, Y={rh.y}", True, WHITE)
        screen.blit(status_r, (20, 45))

    # 3. RENDER LEFT HAND (The Mode Selector)
    if "Left" in state.hands:
        lh = state.hands["Left"]
        # Make the left hand visual distinct (e.g., Cyan Box instead of Green Circle)
        pygame.draw.rect(screen, CYAN, (lh.x - 25, lh.y - 25, 50, 50), 3, border_radius=5)
        
        status_l = font.render(f"Left Mode: X={lh.x}, Y={lh.y}", True, WHITE)
        screen.blit(status_l, (20, 70))

    pygame.display.update()
    clock.tick(120)

tracker.release()
pygame.quit()
sys.exit()