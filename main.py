import cv2
from src.camera import Camera

camera = Camera()

while True:
    frame = camera.read()

    cv2.imshow("GestureCam", frame)