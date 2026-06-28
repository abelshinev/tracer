import cv2
import mediapipe as mp
import time
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Dict

# --- Independent Data Structures ---
@dataclass
class Hand:
    detected: bool
    handedness: str
    x: int
    y: int

@dataclass
class TrackingState:
    hands: Dict[str, Hand] = field(default_factory=dict)
    timestamp_ms: int = 0

# --- The Vision Engine ---
class HandTracker:
    def __init__(self, model_path='hand_landmarker.task'):
        self.camera_index = 0
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"CRITICAL: OpenCV could not connect to camera index {self.camera_index}.")

        self.model_path = model_path
        self._ensure_model_exists()
        
        # Renamed to correctly reflect the destination canvas
        self.overlay_dimensions = (1920, 1080) 
        self.current_state = TrackingState()

        # MediaPipe Tasks API Setup
        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.model_path),
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=self._result_callback,
            num_hands=2 # We want both Mode (Left) and Cursor (Right)
        )
        self.landmarker = HandLandmarker.create_from_options(options)

    def _ensure_model_exists(self):
        if not os.path.exists(self.model_path):
            print("Downloading model asset...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, self.model_path)

    def _result_callback(self, result, output_image, timestamp_ms):
        """Translates MediaPipe arrays into our clean TrackingState dictionary."""
        new_hands = {}
        
        if result.hand_landmarks and result.handedness:
            w, h = self.overlay_dimensions
            
            # Zip allows us to iterate through both lists simultaneously
            for landmarks, handedness_info in zip(result.hand_landmarks, result.handedness):
                handedness = handedness_info[0].category_name
                index_tip = landmarks[8]
                
                new_hands[handedness] = Hand(
                    detected=True,
                    handedness=handedness,
                    x=int(index_tip.x * w),
                    y=int(index_tip.y * h)
                )
                
        # Update state asynchronously
        self.current_state = TrackingState(hands=new_hands, timestamp_ms=timestamp_ms)

    def get_tracking_state(self, overlay_width: int, overlay_height: int) -> TrackingState:
        """The only public method the renderer is allowed to call."""
        success, frame = self.cap.read()
        
        if not success:
            return self.current_state

        self.overlay_dimensions = (overlay_width, overlay_height)
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        timestamp_ms = int(time.perf_counter() * 1000)
        self.landmarker.detect_async(mp_image, timestamp_ms)

        return self.current_state

    def release(self):
        self.cap.release()
        self.landmarker.close()