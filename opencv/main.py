import cv2
import dataclasses
import numpy as np
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide" # hide pygame welcome message
from PIL import Image
from pygame import mixer
import serial
import time

@dataclasses.dataclass
class Detected:
    should_detect: bool = False
    celebi: bool = False
    current_color: str = None

# pause program, and play a song forever
def loop_play(audio_file):
    while True:
        mixer.init()
        alert=mixer.Sound(audio_file)
        alert.play()

celebi = Image.open('celebi.png').convert('L')
celebi_threshold = 0.7 # precision of the celebi image detection

# Initialize the webcam and set the resolution to 640x480
# because on Linux, webcam stream is not working well with 1280x720 (low framerate)
# I selected index 2, my 720p webcam
cap = cv2.VideoCapture(2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

detected = Detected()

print("Starting Celebi detector...")

while True:
    # Capture frame-by-frame from the webcam, on each loop iteration
    ret, frame = cap.read()

    # Reset the detection state for each frame
    detected.should_detect = False
    detected.celebi = False
    detected.current_color = None

    # Convert the frame to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Check if there is a contour within a 100x100 area at the center of the screen
    lower_blue = np.array([100, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    center_x = int(frame.shape[1] / 2)
    center_y = int(frame.shape[0] / 2)
    x1 = center_x - 50
    y1 = center_y - 50
    x2 = center_x + 50
    y2 = center_y + 50
    roi = frame[y1:y2, x1:x2]
    average_color = np.average(np.average(roi, axis=0), axis=0)

    # Draw a 100x100 rectangle at the center of the screen
    # its color depends on the average color of the area
    # and if Celebi is detected in this area or not
    def draw_detection_area():
        if detected.celebi and (detected.current_color == "greenish"):
            color = (0, 255, 0) # green
            celebi_text = "Normal Celebi"
        elif detected.celebi and (detected.current_color == "pinkish"):
            color = (255, 0, 255) # pink (quite purple actually)
            celebi_text = "Shiny Celebi"
        else:
            color = (128, 128, 128) # grey
            celebi_text = "No Celebi"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        if detected.should_detect:
            cv2.putText(frame, celebi_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    def notify_arduino(payload):
        # List all the ttyACM* devices (available arduino ports)
        # as I use only one arduino, I'll just take the first one
        arduino = [arduino for arduino in os.listdir("/dev/") if arduino.startswith("ttyACM")]
        # If there is at least one arduino, send the message to it (wether it's NORMAL or SHINY Celebi)
        if len(arduino) > 0:
            try:
                ser = serial.Serial(port="/dev/" + arduino[0], write_timeout=0.1)
                print(payload.capitalize() + " Celebi detected")
                ser.write(payload.encode())
                time.sleep(0.1)
                ser.flush()
                if ("SHINY" == payload):
                    loop_play('bell.wav')
            except Exception as err:
                print("Error: " + str(err))
                loop_play('error.wav')
        else:
            print("Error: No Arduino found")
            loop_play('error.wav')

    def check_for_celebi_in_area() -> bool:
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        celebi_matches = cv2.matchTemplate(roi_gray, np.array(celebi), cv2.TM_CCOEFF_NORMED)
        return np.max(celebi_matches) >= celebi_threshold

    def detect_color_and_celebi_in_area():
        # Check if the average color of the area is greenish or pinkish
        if average_color[1] > average_color[2] + 10:
            detected.current_color = "greenish"
        elif average_color[2] > average_color[1] + 10:
            detected.current_color = "pinkish"
        else:
            detected.current_color = "other"
        # Check if Celebi is detected in the area
        detected.celebi = check_for_celebi_in_area()
        draw_detection_area()
        if detected.celebi:
            if detected.current_color == "greenish":
                notify_arduino("NORMAL")
            elif detected.current_color == "pinkish":
                notify_arduino("SHINY")
        else:
            print("No Celebi detected")
            loop_play('error.wav')

    draw_detection_area()

    # Wait for Arduino to ask for Celebi detection (via serial)
    arduino = [arduino for arduino in os.listdir("/dev/") if arduino.startswith("ttyACM")]
    if len(arduino) > 0:
        ser = serial.Serial(port="/dev/" + arduino[0], timeout=0.1) # tries to read every 0.1s from Serial
        line = ""
        try:
            line = ser.readline().decode('utf-8').rstrip() # until Arduino sends something, each readline will be empty
            if line == "DETECT":
                # print("Arduino asked for Celebi detection")
                detected.should_detect = True
                celebi_detected = detect_color_and_celebi_in_area()
        except Exception as err:
            print("Error: " + str(err))
            loop_play('error.wav')

    # Display the current webcam frame
    cv2.imshow('frame', frame)

    # Check for key presses when webcam window is focused
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()