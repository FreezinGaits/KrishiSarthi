"""
EfficientNet-B2 Crop Disease Classifier — Training Script

Trains a disease classifier on PlantVillage dataset.
Uses transfer learning with EfficientNet-B2 pretrained on ImageNet.

Usage:
    uv run python ai-service/train_classifier.py

This will:
1. Load & prepare PlantVillage dataset
2. Apply strong data augmentation
3. Fine-tune EfficientNet-B2
4. Save trained model to ai-service/models/classifier.pth
5. Save class labels to ai-service/class_labels.json
6. Generate training report
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms
from tqdm import tqdm

# ── Configuration ─────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "raw"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_SAVE_PATH = MODELS_DIR / "classifier.pth"
CLASS_LABELS_PATH = BASE_DIR / "class_labels.json"

# Dataset directories
# PLANTVILLAGE_DIR = DATA_DIR / "PlantVillage"
PLANTVILLAGE_DIR = DATA_DIR / "PlantVillage"

RICE_DIR = DATA_DIR / "rice_leaf_diseases"
PLANTDOC_DIR = DATA_DIR / "PlantDoc-Dataset" / "train"

# Training hyperparameters
BATCH_SIZE = 32
NUM_EPOCHS = 15
LEARNING_RATE = 0.001
LR_STEP_SIZE = 5
LR_GAMMA = 0.3
TRAIN_SPLIT = 0.85
IMAGE_SIZE = 260
NUM_WORKERS = 0  # Windows-safe default

# ── Class name mapping ───────────────────────────
# Map raw folder names to standardized disease keys
FOLDER_TO_CLASS = {
    # PlantVillage tomato
    "Tomato_Bacterial_spot": "Tomato___Bacterial_spot",
    "Tomato_Early_blight": "Tomato___Early_blight",
    "Tomato_Late_blight": "Tomato___Late_blight",
    "Tomato_Leaf_Mold": "Tomato___Leaf_Mold",
    "Tomato_Septoria_leaf_spot": "Tomato___Septoria_leaf_spot",
    "Tomato_Spider_mites_Two_spotted_spider_mite": "Tomato___Spider_mites",
    "Tomato__Target_Spot": "Tomato___Target_Spot",
    "Tomato__Tomato_YellowLeaf__Curl_Virus": "Tomato___YellowLeaf_Curl_Virus",
    "Tomato__Tomato_mosaic_virus": "Tomato___Mosaic_Virus",
    "Tomato_healthy": "Tomato___healthy",
    # PlantVillage potato
    "Potato___Early_blight": "Potato___Early_blight",
    "Potato___Late_blight": "Potato___Late_blight",
    "Potato___healthy": "Potato___healthy",
    # PlantVillage pepper
    "Pepper__bell___Bacterial_spot": "Pepper___Bacterial_spot",
    "Pepper__bell___healthy": "Pepper___healthy",
    # Rice leaf diseases
    "Bacterial leaf blight": "Rice___Bacterial_Blight",
    "Brown spot": "Rice___Brown_Spot",
    "Leaf smut": "Rice___Leaf_Smut",
    # PlantDoc mappings
    "Tomato leaf late blight": "Tomato___Late_blight",
    "Tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "Tomato leaf mosaic virus": "Tomato___Mosaic_Virus",
    "Tomato leaf yellow virus": "Tomato___YellowLeaf_Curl_Virus",
    "Tomato Early blight leaf": "Tomato___Early_blight",
    "Tomato Septoria leaf spot": "Tomato___Septoria_leaf_spot",
    "Tomato mold leaf": "Tomato___Leaf_Mold",
    "Tomato leaf": "Tomato___healthy",

    "Potato leaf early blight": "Potato___Early_blight",
    "Potato leaf late blight": "Potato___Late_blight",

    "Bell_pepper leaf": "Pepper___healthy",
    "Bell_pepper leaf spot": "Pepper___Bacterial_spot",

    "Apple Scab Leaf": "Apple___Scab",
    "Apple rust leaf": "Apple___Rust",
    "Apple leaf": "Apple___healthy",

}


def discover_classes(data_dirs: List[Path]) -> Tuple[Dict[str, str], List[str]]:
    """
    Discover all class folders across multiple dataset directories.
    Returns mapping of folder names to class keys and ordered list of class keys.
    """
    class_set = set()
    folder_map = {}

    for data_dir in data_dirs:
        if not data_dir.exists():
            print(f"  ⚠  Skipping {data_dir} (not found)")
            continue

        for subfolder in sorted(data_dir.iterdir()):
            if not subfolder.is_dir() or subfolder.name.startswith("."):
                continue

            # Check if there's a nested duplicate (PlantVillage has this)
            nested = subfolder / subfolder.name
            if nested.exists() and nested.is_dir():
                pass  # Will be handled by ImageFolder

            class_key = FOLDER_TO_CLASS.get(subfolder.name, subfolder.name)
            folder_map[subfolder.name] = class_key
            class_set.add(class_key)

            img_count = len([f for f in subfolder.rglob("*") if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}])
            print(f"  📁 {subfolder.name} → {class_key} ({img_count} images)")

    class_keys = sorted(class_set)
    return folder_map, class_keys


def build_class_label_json(class_keys: List[str]) -> Dict[str, str]:
    """Build and save index→class_key mapping for inference."""
    labels = {str(i): key for i, key in enumerate(class_keys)}
    with open(CLASS_LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)
    print(f"  💾 Saved {len(labels)} class labels to {CLASS_LABELS_PATH}")
    return labels


def create_combined_dataset(
    data_dirs: List[Path], class_keys: List[str], transform
) -> datasets.ImageFolder:
    """
    Create a combined dataset from multiple directories.
    Uses symlinks or copies to create a unified folder structure.
    """
    import shutil

    combined_dir = DATA_DIR / "_combined_training"

    # Clean and recreate combined dir
    if combined_dir.exists():
        shutil.rmtree(combined_dir)
    combined_dir.mkdir(parents=True)

    # Create class subfolders and link images
    stats = {}
    for data_dir in data_dirs:
        if not data_dir.exists():
            continue

        for subfolder in data_dir.iterdir():
            if not subfolder.is_dir() or subfolder.name.startswith("."):
                continue

            class_key = FOLDER_TO_CLASS.get(subfolder.name, subfolder.name)
            if class_key not in class_keys:
                continue

            target_dir = combined_dir / class_key
            target_dir.mkdir(parents=True, exist_ok=True)

            images = [f for f in subfolder.rglob("*") if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
            prefix = data_dir.name[:3]  # Prefix to avoid name collisions

            for img in images:
                dest = target_dir / f"{prefix}_{img.name}"
                if not dest.exists():
                    shutil.copy2(img, dest)

            stats[class_key] = stats.get(class_key, 0) + len(images)

    print("\n  📊 Combined dataset statistics:")
    total = 0
    for cls, count in sorted(stats.items()):
        print(f"     {cls}: {count} images")
        total += count
    print(f"     TOTAL: {total} images across {len(stats)} classes\n")

    dataset = datasets.ImageFolder(str(combined_dir), transform=transform)
    return dataset


def train():
    """Main training loop."""
    print("=" * 60)
    print("🌾 Krishi-Sarthi Crop Disease Classifier — Training")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n  🖥  Device: {device}")
    if device.type == "cuda":
        print(f"     GPU: {torch.cuda.get_device_name(0)}")
        print(f"     Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # ── Discover classes ──────────────────────────
    print("\n📂 Discovering datasets...")
    # data_dirs = [PLANTVILLAGE_DIR, RICE_DIR, PLANTDOC_DIR]
    data_dirs = [PLANTVILLAGE_DIR]
    _, class_keys = discover_classes(data_dirs)
    print("\nDetected Classes:")
    for cls in class_keys:
        print(" -", cls)

    num_classes = len(class_keys)
    print(f"\n  ✅ Found {num_classes} classes")

    # Save class labels
    build_class_label_json(class_keys)

    # ── Data augmentation ─────────────────────────
    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(25),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # ── Create dataset ────────────────────────────
    print("\n📦 Building combined dataset (this may take a minute)...")
    combined_dir = DATA_DIR / "_combined_training"

    # Build once
    _ = create_combined_dataset(data_dirs, class_keys, train_transforms)

    full_dataset = datasets.ImageFolder(str(combined_dir), transform=train_transforms)

    train_size = int(TRAIN_SPLIT * len(full_dataset))
    val_size = len(full_dataset) - train_size

    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    # IMPORTANT: create separate val dataset object
    val_dataset = torch.utils.data.Subset(
        datasets.ImageFolder(str(combined_dir), transform=val_transforms),
        val_dataset.indices
    )


    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)



    from collections import Counter

    targets = [train_dataset.dataset.targets[i] for i in train_dataset.indices]


    class_counts = Counter(targets)

    total_samples = sum(class_counts.values())
    class_weights = []

    for i in range(num_classes):
        class_weights.append(total_samples / class_counts[i])

    class_weights = torch.tensor(class_weights, dtype=torch.float32).to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.05)


    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

    print(f"  📊 Train: {train_size} | Val: {val_size}")

    # ── Build model ───────────────────────────────
    print("\n🧠 Building EfficientNet-B2 model...")
    model = models.efficientnet_b2(weights=models.EfficientNet_B2_Weights.IMAGENET1K_V1)

    # Freeze backbone for first few epochs (transfer learning)
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace classifier head
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    model = model.to(device)

    # criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=LR_STEP_SIZE, gamma=LR_GAMMA)


    # ── MixUp augmentation ─────────────────────────────
    def mixup_data(x, y, alpha=0.2):
        import numpy as np
        lam = np.random.beta(alpha, alpha)
        batch_size = x.size(0)
        index = torch.randperm(batch_size).to(x.device)

        mixed_x = lam * x + (1 - lam) * x[index]
        y_a, y_b = y, y[index]

        return mixed_x, y_a, y_b, lam



    # ── Training loop ─────────────────────────────
    print(f"\n🚀 Starting training for {NUM_EPOCHS} epochs...\n")
    best_val_acc = 0.0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    for epoch in range(NUM_EPOCHS):
        # Unfreeze backbone after epoch 3
        if epoch == 3:
            print("  🔓 Unfreezing backbone layers (fine-tuning)...")
            for param in model.features.parameters():
                param.requires_grad = True
            optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE * 0.1)
            scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=LR_STEP_SIZE, gamma=LR_GAMMA)

        # ── Train phase ──
        model.train()
        running_loss, running_correct, running_total = 0.0, 0, 0

        pbar = tqdm(train_loader, desc=f"  Epoch {epoch+1}/{NUM_EPOCHS} [Train]", leave=False)
        for images, labels in pbar:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            images, targets_a, targets_b, lam = mixup_data(images, labels)
            outputs = model(images)
            loss = lam * criterion(outputs, targets_a) + (1 - lam) * criterion(outputs, targets_b)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            running_correct += (
                lam * (preds == targets_a).sum().item() +
                (1 - lam) * (preds == targets_b).sum().item()
            )

            running_total += targets_a.size(0)


            pbar.set_postfix(loss=f"{loss.item():.4f}", acc=f"{running_correct/running_total:.3f}")

        train_loss = running_loss / running_total
        train_acc = running_correct / running_total

        # ── Validation phase ──
        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0

        with torch.no_grad():
            for images, labels in tqdm(val_loader, desc=f"  Epoch {epoch+1}/{NUM_EPOCHS} [Val]  ", leave=False):
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_loss /= val_total
        val_acc = val_correct / val_total

        scheduler.step()
        lr = scheduler.get_last_lr()[0]

        # Save history
        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        # Save best model
        improved = ""
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), str(MODEL_SAVE_PATH))
            improved = " ← BEST ✅"

        print(
            f"  Epoch {epoch+1:2d}/{NUM_EPOCHS} │ "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.3f} │ "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.3f} │ "
            f"LR: {lr:.6f}{improved}"
        )

    # ── Final report ──────────────────────────────
    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print(f"  Best validation accuracy: {best_val_acc:.3f} ({best_val_acc*100:.1f}%)")
    print(f"  Model saved to: {MODEL_SAVE_PATH}")
    print(f"  Model size: {MODEL_SAVE_PATH.stat().st_size / 1e6:.1f} MB")
    print(f"  Class labels: {CLASS_LABELS_PATH}")
    print(f"  Classes: {num_classes}")
    print("=" * 60)

    # Save training report
    report = {
        "best_val_accuracy": best_val_acc,
        "num_classes": num_classes,
        "num_epochs": NUM_EPOCHS,
        "class_keys": class_keys,
        "history": history,
        "model_path": str(MODEL_SAVE_PATH),
        "device": str(device),
    }
    report_path = MODELS_DIR / "training_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n  📋 Training report: {report_path}")


if __name__ == "__main__":
    train()
