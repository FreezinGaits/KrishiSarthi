from app.config import get_settings; from pathlib import Path; s = get_settings(); print(f'Model Path: {s.classifier_model_path}'); print(f'Exists: {Path(s.classifier_model_path).exists()}')
