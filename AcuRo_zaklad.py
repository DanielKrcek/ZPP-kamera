
import asyncio
import cv2
import queue
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection
from unitree_webrtc_connect.constants import WebRTCConnectionMethod
import numpy as np

frame_queue = queue.Queue()

#ArUco nastavení 
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

async def video_callback(track):
    print("Video track received, starting stream...")
    while True:
        frame = await track.recv()
        img = frame.to_ndarray(format="bgr24")
        frame_queue.put(img)

async def main():
    conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalAP)
    await conn.connect()
    print("Connected! Enabling video...")

    conn.video.add_track_callback(video_callback)
    conn.video.switchVideoChannel(True)

    print("ArUco detektor spuštěn - hledej marker 42")

    while True:
        if not frame_queue.empty():
            img = frame_queue.get()

            # DETEKCE ARUCO NA ŽIVÉM OBRAZU 
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            corners, ids, rejected = detector.detectMarkers(gray)

            if ids is not None:
                cv2.aruco.drawDetectedMarkers(img, corners, ids)  # zelené rámečky + ID
                print(f"Detekováno! ID: {ids.flatten()}")
                if  42 in ids.flatten():
                    print("hello world")

            cv2.imshow("Go2 Camera + ArUco", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        await asyncio.sleep(0.001)

    cv2.destroyAllWindows()

asyncio.run(main())