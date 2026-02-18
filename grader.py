import cv2, numpy as np, re, easyocr, torch
from PIL import Image
from tensorflow.keras.models import load_model
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# =========================
# LOAD MODELS
# =========================
cnn_model = load_model("digit_cnn_finetuned.h5")
reader = easyocr.Reader(['en'], gpu=False)

processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

# =========================
# ANSWER KEY
# =========================
ANSWER_KEY = {
    1:"1690",2:"1842",3:"27820",4:"75.5",5:"30",
    6:"164.16",7:"2258",8:"3960",9:"1463",10:"5200"
}

# =========================
# TROCR
# =========================
def trocr_read(roi):
    roi = cv2.copyMakeBorder(roi,20,20,20,20,cv2.BORDER_CONSTANT,value=255)
    pil_img = Image.fromarray(roi).convert("RGB")

    pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values
    ids = trocr_model.generate(pixel_values)
    text = processor.batch_decode(ids, skip_special_tokens=True)[0]
    return text

# =========================
# EASY OCR
# =========================
def easyocr_read(roi):
    res = reader.readtext(roi, detail=0, allowlist="0123456789.")
    return res[0] if res else ""

# =========================
# CNN DIGIT
# =========================
def predict_digit(img):
    img=cv2.resize(img,(28,28))/255.0
    img=img.reshape(1,28,28,1)
    return str(np.argmax(cnn_model.predict(img,verbose=0)))

# =========================
# HYBRID READ
# =========================
def read_number(roi):

    # 1) TrOCR
    text = trocr_read(roi)
    text = re.sub(r"[^0-9.]", "", text)
    if len(text)>0:
        return text

    # 2) EasyOCR
    text = easyocr_read(roi)
    text = re.sub(r"[^0-9.]", "", text)
    if len(text)>0:
        return text

    return ""

# =========================
# ROI POSITIONS
# =========================
BOXES=[
(1724,660,2162,864),(1716,864,2157,1062),(1720,1062,2159,1249),
(1720,1249,2159,1474),(1714,1483,2156,1699),(1707,1699,2159,1892),
(1717,1892,2159,2080),(1704,2094,2172,2291),(1704,2277,2166,2488),
(1707,2483,2166,2662)
]

# =========================
# GRADE EXAM
# =========================
def grade_exam(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    results=[]
    score=0

    for i,(x1,y1,x2,y2) in enumerate(BOXES,1):
        roi=gray[y1:y2,x1:x2]
        pred=read_number(roi)
        ans=ANSWER_KEY[i]
        ok=pred==ans
        score+=int(ok)
        results.append((i,pred,ans,ok))

    return score, results
