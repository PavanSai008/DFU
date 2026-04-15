async function analyze() {

  const file = document.getElementById("image").files[0];

  if (!file) {
    alert("Please upload an image");
    return;
  }

  const formData = new FormData();
  formData.append("image", file);

  // Add vitals
  ["abi","spo2","blood_sugar","age","diabetes_duration"].forEach(id => {
    const val = document.getElementById(id).value;
    if (val) formData.append(id, val);
  });

  document.getElementById("result").innerText = "Processing...";

  try {
    const res = await fetch("http://127.0.0.1:5000/predict", {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    document.getElementById("result").innerText =
      "Prediction: " + data.predicted_class +
      "\nConfidence: " + data.confidence + "%" +
      "\nUlcer: " + data.ulcer +
      "\nIschemia Risk: " + data.ischemia_risk;

  } catch (err) {
    document.getElementById("result").innerText = "Error connecting to backend";
  }
}