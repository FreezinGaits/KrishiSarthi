
import asyncio
import torch
import torchvision.transforms as T
from PIL import Image
import json
import os
from app.services.classifier_service import _load_model, classify_image

async def test():
    print("Loading model...")
    _load_model()
    
    # Create a dummy green image to simulate a leaf
    img = Image.new('RGB', (256, 256), color = (0, 128, 0))
    img.save("test_leaf.jpg")
    
    with open("test_leaf.jpg", "rb") as f:
        img_bytes = f.read()

    print("Running full classification pipeline (with fallback)...")
    result = await classify_image(img_bytes, "test_leaf.jpg", "req-123")
    
    output = f"\nTop Disease: {result.top_disease}\nConfidence: {result.top_confidence:.4f}\nModel Version: {result.model_version}\nPredictions: {result.predictions}"
    print(output)
    with open("classifier_output.txt", "w") as f:
        f.write(output)

if __name__ == "__main__":
    import sys
    sys.path.append(os.getcwd())
    asyncio.run(test())
