"""
app.py — DFU Detection + Ischemia Risk API
==========================================
Hybrid system:
  - EfficientNetB3  → ulcer detection  (deep learning)
  - Rule engine      → ischemia risk   (clinical logic)

Endpoint: POST /predict
  Form fields:
    image             — wound image file
    abi               — Ankle-Brachial Index     (float, e.g. 0.85)
    spo2              — Blood oxygen saturation  (float, e.g. 94.0)
    blood_sugar       — Blood glucose mg/dL      (float, e.g. 180.0)
    age               — Patient age in years     (int,   e.g. 65)
    diabetes_duration — Years with diabetes      (int,   e.g. 12)

Response JSON:
  {
    "ulcer":          "Yes" | "No",
    "confidence":     0-100,
    "ischemia_risk":  "High" | "Low" | "Not Applicable",
    "ischemia_score": 0-7,
    "reasons":        [...triggered factors],
    "all_scores":     {class_name: confidence%}
  }
"""

import os, json, uuid, logging
import numpy as np
from pathlib import Path
from PIL import Image, ExifTags
from flask import Flask, request, jsonify, send_from_directory

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR    = os.path.join(os.path.dirname(BASE_DIR), "frontend")
CLASS_INFO_FILE = os.path.join(BASE_DIR, "models", "class_info.json")
WEIGHTS_FILE    = os.path.join(BASE_DIR, "models", "model_weights.weights.h5")
IMG_SIZE        = (224, 224)
UPLOAD_FOLDER   = os.path.join(BASE_DIR, "uploads")
MAX_MB          = 16
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

# ── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Frontend routes — serve index.html on root, static files from frontend dir
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)


# ─────────────────────────────────────────────────────────────────────────────
# 0. Download weights from Google Drive if missing (for Render deployment)
# ─────────────────────────────────────────────────────────────────────────────
def download_weights_if_missing():
    """Download model weights from Google Drive if not present."""
    if os.path.exists(WEIGHTS_FILE):
        return
    
    import urllib.request
    FILE_ID = "1JyJWyubnnUhLl81aSG3C11JRNjmG55K9"
    url = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
    
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    log.info("Downloading model weights from Google Drive...")
    try:
        urllib.request.urlretrieve(url, WEIGHTS_FILE)
        log.info("Weights downloaded ✓")
    except Exception as e:
        log.error(f"Failed to download weights: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 1. Model loading — rebuilds architecture locally, loads weights only
#    Bypasses all Keras version serialisation issues entirely.
# ─────────────────────────────────────────────────────────────────────────────
_model       = None
_class_names = None


def load_model():
    global _model, _class_names

    # Load class names
    if os.path.exists(CLASS_INFO_FILE):
        with open(CLASS_INFO_FILE) as f:
            info = json.load(f)
        _class_names = info["class_names"]
        log.info(f"Classes: {_class_names}")
    else:
        _class_names = ["Abnormal", "Normal"]
        log.warning("class_info.json not found — using default class names")

    # Check weights exist
    if not os.path.exists(WEIGHTS_FILE):
        log.error(f"Weights not found: {WEIGHTS_FILE}")
        log.error("Copy model_weights.weights.h5 to backend/models/")
        return

    import tensorflow as tf
    from tensorflow.keras.applications import EfficientNetB3
    from tensorflow.keras import layers, Model

    try:
        # Rebuild exact same architecture used in Colab training
        NUM_CLASSES = len(_class_names)
        base = EfficientNetB3(weights=None, include_top=False,
                              input_shape=(224, 224, 3))
        x   = base.output
        x   = layers.GlobalAveragePooling2D()(x)
        x   = layers.BatchNormalization()(x)
        x   = layers.Dense(128, activation="relu")(x)
        x   = layers.Dropout(0.4)(x)
        out = layers.Dense(NUM_CLASSES, activation="softmax")(x)

        _model = Model(base.input, out)
        _model.load_weights(WEIGHTS_FILE)
        log.info(f"Model loaded ✓  input: {_model.input_shape}  classes: {_class_names}")
    except Exception as e:
        log.error(f"Failed to load model: {e}", exc_info=True)
        _model = None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Image preprocessing — must match Colab training exactly
#    EfficientNet uses preprocess_input (scales to [-1,1]), NOT rescale=1/255
# ─────────────────────────────────────────────────────────────────────────────
def preprocess(filepath: str) -> np.ndarray:
    from tensorflow.keras.applications.efficientnet import preprocess_input

    with Image.open(filepath) as img:
        # Fix EXIF rotation (common in phone photos)
        try:
            exif = img._getexif()
            if exif:
                tag = next((k for k, v in ExifTags.TAGS.items()
                            if v == "Orientation"), None)
                if tag and tag in exif:
                    img = img.rotate({3: 180, 6: 270, 8: 90}.get(exif[tag], 0),
                                     expand=True)
        except Exception:
            pass

        img = img.convert("RGB").resize(IMG_SIZE, Image.LANCZOS)
        arr = np.array(img, dtype=np.float32)   # [0,255] — do NOT divide by 255
        arr = preprocess_input(arr)             # scales to [-1,1]
        return np.expand_dims(arr, 0)           # (1,224,224,3)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Ischemia risk rule engine (clinical scoring)
#    Only runs when ulcer detected — never fires on normal images.
# ─────────────────────────────────────────────────────────────────────────────
def assess_ischemia(abi, spo2, blood_sugar, age, diabetes_duration) -> dict:
    score   = 0
    reasons = []

    if abi is not None:
        if abi < 0.6:
            score += 3
            reasons.append(f"ABI {abi:.2f} < 0.6 → Severe peripheral arterial disease (+3)")
        elif abi < 0.9:
            score += 2
            reasons.append(f"ABI {abi:.2f} < 0.9 → Peripheral arterial disease (+2)")

    if spo2 is not None:
        if spo2 < 92:
            score += 2
            reasons.append(f"SpO2 {spo2:.1f}% < 92% → Critical hypoxia (+2)")
        elif spo2 < 95:
            score += 1
            reasons.append(f"SpO2 {spo2:.1f}% < 95% → Mild hypoxia (+1)")

    if blood_sugar is not None:
        if blood_sugar > 300:
            score += 2
            reasons.append(f"Blood sugar {blood_sugar:.0f} mg/dL > 300 → Severe hyperglycaemia (+2)")
        elif blood_sugar > 200:
            score += 1
            reasons.append(f"Blood sugar {blood_sugar:.0f} mg/dL > 200 → Poor glycaemic control (+1)")

    if age is not None and age > 60:
        score += 1
        reasons.append(f"Age {age} > 60 → Elevated vascular risk (+1)")

    if diabetes_duration is not None:
        if diabetes_duration > 20:
            score += 2
            reasons.append(f"Diabetes {diabetes_duration} yrs > 20 → Very high complication risk (+2)")
        elif diabetes_duration > 10:
            score += 1
            reasons.append(f"Diabetes {diabetes_duration} yrs > 10 → Increased complication risk (+1)")

    return {"risk": "High" if score >= 4 else "Low",
            "score": score, "reasons": reasons}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Form value helpers
# ─────────────────────────────────────────────────────────────────────────────
def _float(key):
    try:
        return float(request.form.get(key, "").strip())
    except (ValueError, TypeError):
        return None

def _int(key):
    try:
        return int(float(request.form.get(key, "").strip()))
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":      "online",
        "model_ready": _model is not None,
        "classes":     _class_names,
    })


@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if Path(file.filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return jsonify({"error": "Invalid file type. Use JPG, PNG or WEBP"}), 400

    if _model is None:
        return jsonify({"error": "Model not loaded. Check backend/models/ folder."}), 503

    ext      = Path(file.filename).suffix.lower()
    filepath = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}{ext}")
    file.save(filepath)

    try:
        img_array = preprocess(filepath)
        probs     = _model.predict(img_array, verbose=0)[0]

        top_idx    = int(np.argmax(probs))
        top_class  = _class_names[top_idx]
        top_conf   = round(float(probs[top_idx]) * 100, 1)
        all_scores = {_class_names[i]: round(float(p) * 100, 1)
                      for i, p in enumerate(probs)}

        is_ulcer = top_class.lower() in {"abnormal", "ulcer", "infected"}

        if is_ulcer:
            ischemia      = assess_ischemia(_float("abi"), _float("spo2"),
                                            _float("blood_sugar"), _int("age"),
                                            _int("diabetes_duration"))
            ischemia_risk = ischemia["risk"]
            reasons       = ischemia["reasons"]
            isc_score     = ischemia["score"]
        else:
            ischemia_risk = "Not Applicable"
            reasons       = ["No ulcer detected — ischemia assessment skipped"]
            isc_score     = 0

        return jsonify({
            "ulcer":           "Yes" if is_ulcer else "No",
            "confidence":      top_conf,
            "predicted_class": top_class,
            "ischemia_risk":   ischemia_risk,
            "ischemia_score":  isc_score,
            "reasons":         reasons,
            "all_scores":      all_scores,
        })

    except Exception as e:
        log.error(f"Prediction error: {e}", exc_info=True)
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": f"File too large. Max {MAX_MB} MB"}), 413


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    download_weights_if_missing()
    load_model()
    log.info("DFU API running on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)