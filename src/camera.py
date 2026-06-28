import cv2
import mediapipe as mp
import time
import urllib.request
import os
from dataclasses import dataclass

# MediaPipe Tasks API Aliases
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

@dataclass
class HandState:
    detected: bool
    x: int
    y: int
    handedness: str  # "Left" or "Right"

class HandTracker:
    def __init__(self, model_path='hand_landmarker.task'):
        # Try camera 0 first. If you have OBS, your real camera might be 1 or 2.
        self.camera_index = 0
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"CRITICAL: OpenCV could not connect to camera index {self.camera_index}. Check permissions or change the index.")
        self.model_path = model_path
        self._ensure_model_exists()
        
        # State storage for the asynchronous callback
        self.current_state = HandState(False, 0, 0, "")
        self.screen_dimensions = (1920, 1080) # Default fallback

        # Configure the landmarker for live streaming mode
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.model_path),
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=self._result_callback,
            num_hands=2
        )
        self.landmarker = HandLandmarker.create_from_options(options)

    def _ensure_model_exists(self):
        """Downloads the standalone TFLite model bundle if it's missing."""
        if not os.path.exists(self.model_path):
            print(f"Downloading {self.model_path} model asset...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, self.model_path)
            print("Download complete.")

    def _result_callback(self, result, output_image, timestamp_ms):
        """Asynchronous callback processing tracking frames."""
        if result.hand_landmarks and result.handedness:
            # Mirroring logic matches your legacy implementation (grab primary hand detected)
            hand_landmarks = result.hand_landmarks[0]
            handedness = result.handedness[0][0].category_name
            index_tip = hand_landmarks[8]

            # Convert normalized tracking coordinates directly into pixel scale
            w, h = self.screen_dimensions
            x = int(index_tip.x * w)
            y = int(index_tip.y * h)

            self.current_state = HandState(True, x, y, handedness)
        else:
            self.current_state = HandState(False, 0, 0, "")

    def get_hand_state(self, screen_width: int, screen_height: int) -> HandState:
        success, frame = self.cap.read()
        
        if not success:
            print("WARNING: Camera connected but dropped a frame.")
            return HandState(False, 0, 0, "")

        # --- DEBUG WINDOW ADDED HERE ---
        # This forces a window to open so you can physically see the feed
        cv2.imshow("Camera Debug Feed", frame)
        cv2.waitKey(1) 
        # -------------------------------

        self.screen_dimensions = (screen_width, screen_height)
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        timestamp_ms = int(time.perf_counter() * 1000)
        self.landmarker.detect_async(mp_image, timestamp_ms)

        return self.current_state

    def release(self):
        self.cap.release()
        self.landmarker.close()


if __name__ == "__main__":
    print("Testing HandTracker... Press CTRL+C to stop.")
    tracker = HandTracker()
    WIDTH, HEIGHT = 1920, 1080 
    
    try:
        while True:
            state = tracker.get_hand_state(WIDTH, HEIGHT)
            if state.detected:
                print(f"[{state.handedness} Hand] Index Tip -> X: {state.x}, Y: {state.y}")
            else:
                print("No hand detected...")
                
            time.sleep(0.03) # ~30 FPS polling rate to keep execution smooth
            
    except KeyboardInterrupt:
        print("\nTest complete. Shutting down camera.")
        tracker.release()