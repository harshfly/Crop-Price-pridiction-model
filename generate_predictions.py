import sys
import json
sys.path.append(".")
from src.predict import predict_price

crops = ['Onion', 'Tomato', 'Wheat']
results = []
for crop in crops:
    try:
        res = predict_price(crop, 'Indore')
        results.append(res)
    except Exception as e:
        print(f"Failed for {crop}: {e}")

# Format into markdown
md = "# 🌾 KrishiMitra AI - Live Crop Predictions\n\n"
for res in results:
    md += f"## 🌿 {res['crop']} @ {res['mandi']}\n"
    md += f"- **Current Price (Past/Live):** ₹{res['current_price']}\n"
    md += f"- **Predicted Price (7-days):** ₹{res['predicted_price']}\n"
    md += f"- **Confidence:** {res['confidence_pct']}%\n"
    md += f"- **Signal:** **{res['signal']}**\n\n"
    
    md += "### 📈 7-Day Forecast\n"
    for i, p in enumerate(res['7_day_forecast']):
        md += f"- Day {i+1}: ₹{p}\n"
    md += "\n"
    
    md += "### 🔍 Key Factors (SHAP)\n"
    for f in res['shap_factors']:
        icon = "🟢" if f['direction'] == 'up' else "🔴"
        md += f"- {icon} {f['factor']}: {f['direction'].upper()} (Impact: ₹{f['impact_rs']})\n"
    md += "---\n\n"

with open("predictions_report.md", "w", encoding="utf-8") as f:
    f.write(md)
print("Report generated at predictions_report.md")
