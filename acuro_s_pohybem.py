import asyncio
import cv2
import queue
import numpy as np
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection
from unitree_webrtc_connect.constants import WebRTCConnectionMethod

frame_queue = queue.Queue()

async def video_callback(track):
    print("Video track received...")
    while True:
        frame = await track.recv()
        img = frame.to_ndarray(format="bgr24")
        frame_queue.put(img)

async def main():
    # Připojení – LocalAP když jsi připojený k WiFi robota, nebo Remote když jsi na stejné síti
    conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalAP)   # nebo Remote
    await conn.connect()
    conn.video.add_track_callback(video_callback)
    conn.video.switchVideoChannel(True)

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    while True:
        if not frame_queue.empty():
            img = frame_queue.get()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)

            if ids is not None:
                cv2.aruco.drawDetectedMarkers(img, corners, ids)
                print(f"Nalezen marker: {ids.flatten()}")

                # Tady přijde logika "jak se má pes hýbat"
                # Např. pokud vidí marker 42 → jdi dopředu, otoč se, atd.

            cv2.imshow("Go2 Camera + ArUco", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        await asyncio.sleep(0.001)

    cv2.destroyAllWindows()

asyncio.run(main())