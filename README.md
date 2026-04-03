# DFU Wound Intelligence

Hybrid system for Diabetic Foot Ulcer detection combining:
- **EfficientNetB3** — deep learning image classifier (ulcer vs normal)
- **Clinical rule engine** — ischemia risk scoring from patient vitals

---

## Project Structure

```
dfu_final/
├── backend/
│   ├── app.py              ← Flask API (main entry point)
│   ├── requirements.txt
│   ├── models/
│   │   ├── model.h5        ← trained weights (from Colab)
│   │   └── class_info.json ← class name mapping (from Colab)
│   └── uploads/            ← temp image storage (auto-created)
├── frontend/
│   └── index.html          ← single-page UI
├── Dockerfile
├── run_windows.bat
├── run_mac_linux.sh
└── README.md
```

---

## Step 1 — Add your trained model

After training in Google Colab, copy the two output files:

```
model.h5        →  backend/models/model.h5
class_info.json →  backend/models/class_info.json
```

---

## Step 2 — Run

### Windows
```
run_windows.bat
```

### Mac / Linux
```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

### Manual
```bash
pip install -r backend/requirements.txt
cd backend && python app.py
```

### Docker
```bash
docker build -t dfu-app .
docker run -p 5000:5000 -v $(pwd)/backend/models:/app/backend/models dfu-app
```

Open `frontend/index.html` in your browser after the server starts.

---

## API Reference

### GET /health
```json
{ "status": "online", "model_ready": true, "classes": ["Abnormal", "Normal"] }
```

### POST /predict

**Form-data fields:**

| Field               | Type  | Required | Description                    |
|---------------------|-------|----------|--------------------------------|
| `image`             | File  | Yes      | Wound image (JPG/PNG/WEBP)     |
| `abi`               | float | No       | Ankle-Brachial Index (0 – 1.4) |
| `spo2`              | float | No       | Blood oxygen %                 |
| `blood_sugar`       | float | No       | Blood glucose mg/dL            |
| `age`               | int   | No       | Patient age in years           |
| `diabetes_duration` | int   | No       | Years with diabetes            |

**Response:**
```json
{
  "ulcer":           "Yes",
  "confidence":      96.9,
  "predicted_class": "Abnormal",
  "ischemia_risk":   "High",
  "ischemia_score":  5,
  "reasons": [
    "ABI 0.75 < 0.9 → Peripheral arterial disease (+2)",
    "SpO2 90.0% < 92% → Critical hypoxia (+2)",
    "Age 65 > 60 → Elevated vascular risk (+1)"
  ],
  "all_scores": {
    "Abnormal": 96.9,
    "Normal": 3.1
  }
}
```

---

## Ischemia Scoring Rules

| Factor                     | Points |
|----------------------------|--------|
| ABI < 0.6                  | +3     |
| ABI < 0.9                  | +2     |
| SpO2 < 92%                 | +2     |
| SpO2 < 95%                 | +1     |
| Blood sugar > 300 mg/dL    | +2     |
| Blood sugar > 200 mg/dL    | +1     |
| Age > 60                   | +1     |
| Diabetes duration > 20 yrs | +2     |
| Diabetes duration > 10 yrs | +1     |

**Score ≥ 4 → High Risk | Score < 4 → Low Risk**

Ischemia is only assessed when the image model detects an ulcer.
If the image is classified as Normal, ischemia returns "Not Applicable".

---

## Test with Postman

1. Method: **POST**
2. URL: `http://localhost:5000/predict`
3. Body: **form-data**

| Key                 | Value         |
|---------------------|---------------|
| `image`             | (file upload) |
| `abi`               | `0.75`        |
| `spo2`              | `90`          |
| `blood_sugar`       | `250`         |
| `age`               | `65`          |
| `diabetes_duration` | `12`          |

---

## Notes

- The `compiled metrics` warning from TensorFlow on model load is harmless.
- Vitals are optional — if not provided, ischemia returns "Not Applicable".
- The model expects 224×224 RGB images normalised with EfficientNet's `preprocess_input`.
- For deployment on Render or Railway, set the start command to `python backend/app.py`.
