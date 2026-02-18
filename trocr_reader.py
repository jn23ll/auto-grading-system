from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

print("⏳ Loading TrOCR model (ครั้งแรกจะช้านิดนึง)...")

processor = TrOCRProcessor.from_pretrained(
    "microsoft/trocr-base-handwritten"
)
model = VisionEncoderDecoderModel.from_pretrained(
    "microsoft/trocr-base-handwritten"
)

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

print("✅ TrOCR ready!")

def read_handwriting(cv2_img):
    """รับภาพ ROI แล้วคืนข้อความที่อ่านได้"""
    pil_img = Image.fromarray(cv2_img).convert("RGB")

    pixel_values = processor(
        images=pil_img,
        return_tensors="pt"
    ).pixel_values.to(device)

    generated_ids = model.generate(pixel_values)
    text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    return text.strip()
