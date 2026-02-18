import cv2
import numpy as np

def detect_answer_boxes(gray):
    """หา bounding box ช่องคำตอบอัตโนมัติ"""
    
    blur = cv2.GaussianBlur(gray,(5,5),0)
    thresh = cv2.adaptiveThreshold(
        blur,255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,31,15
    )

    kernel = np.ones((5,5),np.uint8)
    dilate = cv2.dilate(thresh,kernel,2)

    contours,_ = cv2.findContours(
        dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes=[]
    for c in contours:
        x,y,w,h = cv2.boundingRect(c)
        area = w*h

        # filter ให้เหลือเฉพาะ "ช่องคำตอบ"
        if area < 15000: 
            continue
        if h < 120:
            continue

        boxes.append((x,y,w,h))

    # เรียงจากบน → ล่าง
    boxes = sorted(boxes, key=lambda b: b[1])

    return boxes[:10]  # เอา 10 ช่อง
