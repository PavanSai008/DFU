import os, json, uuid
import numpy as np
from pathlib import Path
from PIL import Image, ExifTags
from flask import Flask, request, jsonify, send_from_directory

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
WEIGHTS_FILE = os.path.join(BASE_DIR, "models", "model_weights.weights.h5")
CLASS_FILE   = os.path.join(BASE_DIR, "models", "class_info.json")
UPLOAD_DIR   = os.path.join(BASE_DIR, "uploads")
IMG_SIZE     = (224, 224)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

_model, _class_names = None, None

def load_model():
    global _model, _class_names

    _class_names = json.load(open(CLASS_FILE))["class_names"] if os.path.exists(CLASS_FILE) else ["Abnormal", "Normal"]

    import tensorflow as tf
    from tensorflow.keras.applications import EfficientNetB3
    from tensorflow.keras import layers, Model

    base = EfficientNetB3(weights=None, include_top=False, input_shape=(224, 224, 3))
    x    = layers.GlobalAveragePooling2D()(base.output)
    x    = layers.BatchNormalization()(x)
    x    = layers.Dense(128, activation="relu")(x)
    x    = layers.Dropout(0.4)(x)
    out  = layers.Dense(len(_class_names), activation="softmax")(x)

    _model = Model(base.input, out)
    _model.load_weights(WEIGHTS_FILE)

def preprocess(filepath):
    from tensorflow.keras.applications.efficientnet import preprocess_input

    with Image.open(filepath) as img:
        try:
            exif = img._getexif()
            if exif:
                tag = next((k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None)
                if tag and tag in exif:
                    img = img.rotate({3: 180, 6: 270, 8: 90}.get(exif[tag], 0), expand=True)
        except:
            pass
        img = img.convert("RGB").resize(IMG_SIZE, Image.LANCZOS)
        arr = np.array(img, dtype=np.float32)
        return np.expand_dims(preprocess_input(arr), 0)

def assess_ischemia(abi, spo2, blood_sugar, age, diabetes_duration):
    score, reasons = 0, []

    if abi is not None:
        if abi < 0.6:   score += 3; reasons.append(f"ABI {abi:.2f} < 0.6 → Severe PAD (+3)")
        elif abi < 0.9: score += 2; reasons.append(f"ABI {abi:.2f} < 0.9 → PAD (+2)")

    if spo2 is not None:
        if spo2 < 92:   score += 2; reasons.append(f"SpO2 {spo2:.1f}% < 92% → Critical hypoxia (+2)")
        elif spo2 < 95: score += 1; reasons.append(f"SpO2 {spo2:.1f}% < 95% → Mild hypoxia (+1)")

    if blood_sugar is not None:
        if blood_sugar > 300:   score += 2; reasons.append(f"Sugar {blood_sugar:.0f} > 300 → Severe hyperglycaemia (+2)")
        elif blood_sugar > 200: score += 1; reasons.append(f"Sugar {blood_sugar:.0f} > 200 → Poor glycaemic control (+1)")

    if age is not None and age > 60:
        score += 1; reasons.append(f"Age {age} > 60 → Elevated vascular risk (+1)")

    if diabetes_duration is not None:
        if diabetes_duration > 20:   score += 2; reasons.append(f"Diabetes {diabetes_duration}yrs > 20 → Very high risk (+2)")
        elif diabetes_duration > 10: score += 1; reasons.append(f"Diabetes {diabetes_duration}yrs > 10 → Increased risk (+1)")

    return {"risk": "High" if score >= 4 else "Low", "score": score, "reasons": reasons}

def _float(k):
    try: return float(request.form.get(k, "").strip())
    except: return None

def _int(k):
    try: return int(float(request.form.get(k, "").strip()))
    except: return None

@app.route("/health")
def health():
    return jsonify({"status": "online", "model_ready": _model is not None})

@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if "image" not in request.files or request.files["image"].filename == "":
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if Path(file.filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return jsonify({"error": "Invalid file type"}), 400

    if _model is None:
        return jsonify({"error": "Model not loaded"}), 503

    filepath = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{Path(file.filename).suffix.lower()}")
    file.save(filepath)

    try:
        probs     = _model.predict(preprocess(filepath), verbose=0)[0]
        top_idx   = int(np.argmax(probs))
        top_class = _class_names[top_idx]
        is_ulcer  = top_class.lower() in {"abnormal", "ulcer", "infected"}

        clinical = [_float("abi"), _float("spo2"), _float("blood_sugar"), _int("age"), _int("diabetes_duration")]
        if any(v is not None for v in clinical):
            isc = assess_ischemia(*clinical)
            ischemia_risk = isc["risk"] if is_ulcer else f"{isc['risk']} (No ulcer - preventive)"
            reasons, isc_score = isc["reasons"], isc["score"]
        else:
            ischemia_risk, reasons, isc_score = "Not Provided", ["No clinical inputs"], 0

        return jsonify({
            "ulcer":           "Yes" if is_ulcer else "No",
            "confidence":      round(float(probs[top_idx]) * 100, 1),
            "predicted_class": top_class,
            "ischemia_risk":   ischemia_risk,
            "ischemia_score":  isc_score,
            "reasons":         reasons,
            "all_scores":      {_class_names[i]: round(float(p) * 100, 1) for i, p in enumerate(probs)},
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(filepath): os.remove(filepath)

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Max 16MB"}), 413

if __name__ == "__main__":
    load_model()
    app.run(host="0.0.0.0", port=5000)