import sys
import pygame
import win32api
import win32con
import win32gui
from vision import HandTracker

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
BRUSH_COLOR = (0, 150, 255) # A nice glowing blue for the ink

# Windows Transparency Magic
hwnd = pygame.display.get_surface_id() if hasattr(pygame.display, 'get_surface_id') else pygame.display.get_wm_info()['window']
current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, current_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*FUCHSIA), 0, win32con.LWA_COLORKEY)

font = pygame.font.SysFont("Arial", 20, bold=True)
clock = pygame.time.Clock()

# --- THE DRAWING CANVAS ---
# This surface holds our permanent ink. We set its transparent color to Fuchsia.
canvas = pygame.Surface((WIDTH, HEIGHT))
canvas.fill(FUCHSIA)
canvas.set_colorkey(FUCHSIA)

tracker = HandTracker()
running = True

# We need to remember where the brush was last frame to draw smooth continuous lines
prev_rx, prev_ry = None, None

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False

    # 1. Clear the main screen
    screen.fill(FUCHSIA)

    # 2. PULL DATA STATE
    state = tracker.get_tracking_state()
    
    # 3. GET LEFT HAND STATE (The Commander)
    left_gesture = "Unknown"
    if "Left" in state.hands:
        lh = state.hands["Left"]
        left_gesture = lh.gesture
        lx, ly = lh.get_pixel(8, WIDTH, HEIGHT)
        
        # Draw Left Hand UI
        pygame.draw.rect(screen, CYAN, (lx - 25, ly - 25, 50, 50), 3, border_radius=5)
        status_l = font.render(f"Left Mode: {left_gesture}", True, WHITE)
        screen.blit(status_l, (lx - 40, ly - 50))
        
        # ACTION: Clear Canvas on Fist
        if left_gesture == "Fist":
            canvas.fill(FUCHSIA)

    # 4. GET RIGHT HAND STATE (The Brush)
    if "Right" in state.hands:
        rh = state.hands["Right"]
        rx, ry = rh.get_pixel(8, WIDTH, HEIGHT)
        
        # ACTION: Draw on Canvas if Left Hand is Pointing
        if left_gesture == "Pointer":
            if prev_rx is not None and prev_ry is not None:
                # Draw a thick anti-aliased line on the CANVAS, not the screen
                pygame.draw.line(canvas, BRUSH_COLOR, (prev_rx, prev_ry), (rx, ry), 10)
                # Cap the ends with circles so the line looks perfectly smooth
                pygame.draw.circle(canvas, BRUSH_COLOR, (rx, ry), 5)
            
            # Brush Cursor (Solid when drawing)
            pygame.draw.circle(screen, BRUSH_COLOR, (rx, ry), 15, 0)
        else:
            # Hover Cursor (Hollow when not drawing)
            pygame.draw.circle(screen, NEON_GREEN, (rx, ry), 15, 2)
            
        # Save current position for the next frame's line drawing
        prev_rx, prev_ry = rx, ry
    else:
        # If right hand is lost, break the continuous line
        prev_rx, prev_ry = None, None

    # 5. COMPOSITE THE IMAGE
    # Slap the permanent canvas onto the main screen
    screen.blit(canvas, (0, 0))

    # Draw UI Header Box on top of everything
    pygame.draw.rect(screen, DARK_GREEN, (10, 10, 350, 60), border_radius=10)
    text_surface = font.render("[Phase 4: AR Whiteboard]", True, NEON_GREEN)
    screen.blit(text_surface, (20, 15))
    fps_surface = font.render(f"Renderer FPS: {int(clock.get_fps())}", True, WHITE)
    screen.blit(fps_surface, (20, 40))

    pygame.display.update()
    clock.tick(120)

tracker.release()
pygame.quit()
sys.exit()