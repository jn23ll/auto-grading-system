import cv2
import easyocr
import os

reader = easyocr.Reader(['en'], gpu=False)

results = []

for i in range(1, 11):
    path = f"cropped_answers/answer_{i}.png"
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    # --- preprocess ให้เหมาะกับลายมือ ---
    img = cv2.GaussianBlur(img, (5,5), 0)
    _, img = cv2.threshold(img, 0, 255,
                            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    texts = reader.readtext(
        img,
        allowlist='0123456789',
        detail=0
    )

    results.append("".join(texts))

print("ผลลัพธ์ที่อ่านได้:", results)