# ai-service/infer_classifier.py

import json
import torch
from torchvision import models, transforms
from PIL import Image
from pathlib import Path

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "models" / "classifier.pth"
LABEL_PATH = BASE_DIR / "class_labels.json"

IMAGE_SIZE = 260

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load labels
with open(LABEL_PATH, "r", encoding="utf-8") as f:
    idx_to_class = json.load(f)

num_classes = len(idx_to_class)

# Build model
model = models.efficientnet_b2(weights=None)
model.classifier[1] = torch.nn.Linear(
    model.classifier[1].in_features,
    num_classes
)

model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def predict_image(image_path: str):
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.softmax(outputs, dim=1)
        confidence, pred_idx = torch.max(probs, 1)

    class_name = idx_to_class[str(pred_idx.item())]

    return {
        "disease": class_name,
        "confidence": float(confidence.item())
    }


if __name__ == "__main__":
    result = predict_image("ai_service/data/raw/_combined_training/Potato___healthy/Pla_0b3e5032-8ae8-49ac-8157-a1cac3df01dd___RS_HL 1817.JPG")
    print(result)