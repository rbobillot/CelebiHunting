import cv2
import numpy as np
import os
from pygame import mixer
import time

import serial

cap = cv2.VideoCapture(2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Initialize variables for color detection
greenish_start_time = None
pinkish_start_time = None
color_detected = None

def ring_a_bell():
    mixer.init() #you must initialize the mixer
    alert=mixer.Sound('bell.wav')
    alert.play()

while True:
    ret, frame = cap.read()

    # Convert the frame to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_blue = np.array([100, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Check if there is a contour within a 100x100 area at the center of the screen
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    center_x = int(frame.shape[1] / 2)
    center_y = int(frame.shape[0] / 2)
    x1 = center_x - 50
    y1 = center_y - 50
    x2 = center_x + 50
    y2 = center_y + 50
    roi = frame[y1:y2, x1:x2]
    average_color = np.average(np.average(roi, axis=0), axis=0)

    # Check if the average color is greenish, pinkish, or else, for at least 1 second
    if average_color[1] > average_color[2] + 10:
        if color_detected != "greenish":
            greenish_start_time = time.time()
            pinkish_start_time = None
            color_detected = "greenish"
        elif time.time() - greenish_start_time >= 1:
            # Send serial message to Arduino with millis() timestamp
            serial_message = "celebi_hunt_status,timestamp:" + str(int(time.time() * 1000)) + ",celebi_normal"
            print(serial_message)
            serial_message = serial_message.encode()
            # ser.write(serial_message)
            color_detected = None
    elif average_color[2] > average_color[1] + 10:
        if color_detected != "pinkish":
            pinkish_start_time = time.time()
            greenish_start_time = None
            color_detected = "pinkish"
        elif time.time() - pinkish_start_time >= 2:
            # Send serial message to Arduino with millis() timestamp
            print("celebi_hunt_status,timestamp:" + str(int(time.time() * 1000)) + ",celebi_shiny")
            # the arduino might not be detected, so we try to detect it again
            arduino = [arduino for arduino in os.listdir("/dev/") if arduino.startswith("ttyACM")]
            if len(arduino) > 0:
                ser = serial.Serial("/dev/" + arduino[0], 9600)
                ser.write("S".encode()) # send a '!' to the arduino, meaning the shiny celebi has been found
                ser.close()
                color_detected = None
                while True:
                    ring_a_bell()
            else:
                print("No Arduino found, you just missed a shiny celebi!")
    else:
        greenish_start_time = None
        pinkish_start_time = None
        color_detected = "other"

    # Draw a green, pink, or gray rectangle around the 100x100 area at the center of the screen
    if color_detected == "greenish":
        color = (0, 255, 0)
    elif color_detected == "pinkish":
        color = (255, 0, 255)
    else:
        color = (128, 128, 128)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # Display the frame
    cv2.imshow('frame', frame)

    # Check for key presses
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()