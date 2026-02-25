import cv2
import numpy as np
import torch
import win32gui
import win32ui
import win32con
import win32api
from PIL import Image
import pyautogui
import time
import keyboard
import vgamepad as vg

# Initialisation du gamepad virtuel (à placer en haut du fichier, après les imports)
gamepad = vg.VX360Gamepad()

# Capture PS Remote Play window

def capture_window(window_name="PS Remote Play"):
    hwnd = win32gui.FindWindow(None, window_name)
    if hwnd == 0:
        raise Exception("Fenêtre PS Remote Play non trouvée")
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bot - top
    hwindc = win32gui.GetWindowDC(hwnd)
    srcdc = win32ui.CreateDCFromHandle(hwindc)
    memdc = srcdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, width, height)
    memdc.SelectObject(bmp)
    memdc.BitBlt((0, 0), (width, height), srcdc, (0, 0), win32con.SRCCOPY)
    bmpinfo = bmp.GetInfo()
    bmpstr = bmp.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype=np.uint8)
    img.shape = (height, width, 4)
    srcdc.DeleteDC()
    memdc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwindc)
    win32gui.DeleteObject(bmp.GetHandle())
    return img[..., :3]  # RGB

# YOLO detection

def detect_enemies(image, model_path="customModels/Fortnite/best.pt"):
    model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path, force_reload=True)
    results = model(image)
    enemies = []
    boxes = []
    for *box, conf, cls in results.xyxy[0]:
        if int(cls) == 0:  # Classe 0 = ennemi (à adapter selon le modèle)
            enemies.append(box)
            boxes.append(box)
    return enemies, boxes

def center_of_box(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)

def move_and_shoot(target, window_name="PS Remote Play"):
    hwnd = win32gui.FindWindow(None, window_name)
    if hwnd == 0:
        print("Fenêtre PS Remote Play non trouvée pour viser.")
        return
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    win_x, win_y = left, top
    # Déplacer la souris au centre de la cible (dans la fenêtre)
    cx, cy = center_of_box(target)
    abs_x = int(win_x + cx)
    abs_y = int(win_y + cy)
    pyautogui.moveTo(abs_x, abs_y, duration=0.05)
    time.sleep(0.02)
    pyautogui.mouseDown()
    time.sleep(0.05)
    pyautogui.mouseUp()

def move_and_shoot_virtual(target, window_name="PS Remote Play"):
    hwnd = win32gui.FindWindow(None, window_name)
    if hwnd == 0:
        print("Fenêtre PS Remote Play non trouvée pour viser.")
        return
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    win_width = right - left
    win_height = bot - top
    cx, cy = center_of_box(target)
    # Normaliser la position cible par rapport au centre de la fenêtre
    stick_x = int(((cx - win_width/2) / (win_width/2)) * 32767)
    stick_y = int(((cy - win_height/2) / (win_height/2)) * 32767)
    stick_x = max(-32768, min(32767, stick_x))
    stick_y = max(-32768, min(32767, stick_y))
    # Déplacer le stick droit
    gamepad.right_joystick(x_value=stick_x, y_value=stick_y)
    gamepad.update()
    time.sleep(0.05)
    # Tirer (RT)
    gamepad.right_trigger(value=255)
    gamepad.update()
    time.sleep(0.1)
    gamepad.right_trigger(value=0)
    gamepad.right_joystick(x_value=0, y_value=0)
    gamepad.update()

if __name__ == "__main__":
    print("Appuie sur F8 pour activer/désactiver l'auto-aim. F9 pour quitter.")
    auto_aim = False
    try:
        while True:
            if keyboard.is_pressed('F9'):
                print("Arrêt demandé (F9)")
                break
            if keyboard.is_pressed('F8'):
                auto_aim = not auto_aim
                print(f"Auto-aim {'activé' if auto_aim else 'désactivé'}")
                time.sleep(0.5)  # anti-rebond
            if auto_aim:
                try:
                    frame = capture_window()
                    enemies, boxes = detect_enemies(frame)
                    print(f"Ennemis détectés : {len(enemies)}")
                    # Affichage des boxes autour des ennemis
                    frame_draw = frame.copy()
                    for box in boxes:
                        x1, y1, x2, y2 = [int(coord) for coord in box]
                        cv2.rectangle(frame_draw, (x1, y1), (x2, y2), (0,255,0), 2)
                        cv2.putText(frame_draw, 'Ennemi', (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                    cv2.imshow('Tracking Fortnite', frame_draw)
                    cv2.waitKey(1)
                    if enemies:
                        hwnd = win32gui.FindWindow(None, "PS Remote Play")
                        left, top, right, bot = win32gui.GetWindowRect(hwnd)
                        def dist(box):
                            cx, cy = center_of_box(box)
                            return (cx - (right-left)/2)**2 + (cy - (bot-top)/2)**2
                        target = min(enemies, key=dist)
                        move_and_shoot_virtual(target)
                        print("Tir automatique manette virtuelle effectué.")
                except Exception as e:
                    print(f"Erreur : {e}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Arrêt manuel (Ctrl+C)")
