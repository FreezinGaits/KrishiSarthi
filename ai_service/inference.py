import torch
import json
from pathlib import Path
from torchvision import transforms
from PIL import Image
from torchvision import models
import torch.nn as nn

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "models" / "classifier.pth"
CLASS_LABELS_PATH = BASE_DIR / "class_labels.json"

IMAGE_SIZE = 260

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load class labels
with open(CLASS_LABELS_PATH, "r") as f:
    class_labels = json.load(f)

# Load model
num_classes = len(class_labels)
model = models.efficientnet_b2(weights=None)
model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model = model.to(device)
model.eval()

# Preprocessing
transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

def predict_disease(image_path: str):
    image = Image.open(image_path).convert("RGB")
    image = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(image)
        probs = torch.softmax(outputs, dim=1)
        confidence, predicted = torch.max(probs, 1)

    class_name = class_labels[str(predicted.item())]

    return {
        "class_name": class_name,
        "confidence": float(confidence.item())
    }