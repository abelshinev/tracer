import cv2
import mediapipe as mp
import time
import os
import urllib.request
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any

# --- Independent Data Structures ---
@dataclass
class Hand:
    handedness: str
    landmarks: List[Any]  # Stores all 21 MediaPipe landmark objects
    
    @property
    def index_tip(self):
        return self.landmarks[8]
        
    @property
    def thumb_tip(self):
        return self.landmarks[4]
        
    def get_pixel(self, landmark_idx, w, h):
        """Safely scales normalized coordinates to the final canvas size."""
        return int(self.landmarks[landmark_idx].x * w), int(self.landmarks[landmark_idx].y * h)
        
    @property
    def gesture(self) -> str:
        """Self-contained geometric gesture evaluation."""
        index_up = self.landmarks[8].y < self.landmarks[6].y
        middle_up = self.landmarks[12].y < self.landmarks[10].y
        ring_up = self.landmarks[16].y < self.landmarks[14].y
        pinky_up = self.landmarks[20].y < self.landmarks[18].y

        if index_up and not middle_up and not ring_up and not pinky_up:
            return "Pointer"
        elif index_up and middle_up and not ring_up and not pinky_up:
            return "Arrow"
        elif index_up and middle_up and ring_up and pinky_up:
            return "Open"
        elif not index_up and not middle_up and not ring_up and not pinky_up:
            return "Fist"
            
        return "Unknown"

@dataclass
class TrackingState:
    hands: Dict[str, Hand] = field(default_factory=dict)
    timestamp_ms: int = 0

# --- The Asynchronous Vision Engine ---
class HandTracker:
    def __init__(self, model_path='hand_landmarker.task'):
        self.camera_index = 1  # OBS Virtual Camera
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"CRITICAL: OpenCV could not connect to camera index {self.camera_index}.")

        self.model_path = model_path
        self._ensure_model_exists()
        
        # Dual Mailboxes
        self.latest_frame = None
        self.latest_state = TrackingState()
        self.thread_running = True
        
        # Initialize MediaPipe (IMAGE Mode)
        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.model_path),
            running_mode=VisionRunningMode.IMAGE,
            num_hands=2
        )
        self.landmarker = HandLandmarker.create_from_options(options)

        # Start background workers
        self.cam_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.inf_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.cam_thread.start()
        self.inf_thread.start()

    def _ensure_model_exists(self):
        if not os.path.exists(self.model_path):
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, self.model_path)

    def _camera_loop(self):
        """Thread 1: Feeds the frame mailbox."""
        while self.thread_running:
            success, frame = self.cap.read()
            if success:
                self.latest_frame = frame
            else:
                time.sleep(0.001)

    def _inference_loop(self):
        """Thread 2: Pulls frame, downscales, runs AI, feeds state mailbox."""
        while self.thread_running:
            if self.latest_frame is None:
                time.sleep(0.001)
                continue
                
            frame_to_process = self.latest_frame.copy()
            
            # OPTIMIZATION: Downscale by 3x to crush inference latency
            small_frame = cv2.resize(frame_to_process, (640, 360))
            
            rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            
            # Synchronous inference on the tiny image
            result = self.landmarker.detect(mp_image)

            new_hands = {}
            if result.hand_landmarks and result.handedness:
                for landmarks, handedness_info in zip(result.hand_landmarks, result.handedness):
                    handedness = handedness_info[0].category_name
                    new_hands[handedness] = Hand(handedness=handedness, landmarks=landmarks)

            self.latest_state = TrackingState(hands=new_hands, timestamp_ms=int(time.perf_counter() * 1000))
            
            # Yield slightly to prevent thread starvation
            time.sleep(0.005) 

    def get_tracking_state(self) -> TrackingState:
        """O(1) Instant Return for Pygame (No blocking!)."""
        return self.latest_state

    def release(self):
        self.thread_running = False
        self.cam_thread.join(timeout=1.0)
        self.inf_thread.join(timeout=1.0)
        self.cap.release()
        self.landmarker.close()