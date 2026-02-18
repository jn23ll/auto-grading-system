import cv2
import os

img = cv2.imread("image/img_5.jpg")

if img is None:
    raise Exception("❌ ไม่พบไฟล์ภาพ ตรวจ path ให้ถูกต้อง")

orig_h, orig_w = img.shape[:2]

DISPLAY_WIDTH = 900
scale = DISPLAY_WIDTH / orig_w

display_boxes = [
    (625,243,788,311),(622,309,785,382),(624,384,784,448),
    (622,454,805,529),(622,533,785,613),(624,619,783,685),
    (622,689,785,754),(622,762,783,823),(622,830,783,895),
    (621,899,783,965),
]

def crop_handwriting_zone(roi):
    h, w = roi.shape[:2]
    left   = int(w * 0.20)
    right  = int(w * 0.95)
    top    = int(h * 0.15)
    bottom = int(h * 0.85)
    return roi[top:bottom, left:right]

os.makedirs("cropped_answers", exist_ok=True)

for i, (x1, y1, x2, y2) in enumerate(display_boxes, 1):

    x1 = int(x1 / scale)
    y1 = int(y1 / scale)
    x2 = int(x2 / scale)
    y2 = int(y2 / scale)

    # clamp กันพิกัดเกินภาพ
    x1 = max(0, min(x1, orig_w-1))
    x2 = max(0, min(x2, orig_w))
    y1 = max(0, min(y1, orig_h-1))
    y2 = max(0, min(y2, orig_h))

    if x2 <= x1 or y2 <= y1:
        print(f"❌ Box {i} ผิดพิกัด")
        continue

    roi = img[y1:y2, x1:x2]
    hand = crop_handwriting_zone(roi)

    path = f"cropped_answers/answer_{i}.png"
    cv2.imwrite(path, hand)

    print(f"✅ saved {path}")

print("\n🎉 Crop เสร็จทั้งหมด")
