---
title: Krishimitra AI
emoji: 🌾
colorFrom: green
colorTo: yellow
sdk: docker
pinned: false
app_port: 7860
---
# 🌾 KrishiMitra AI — Crop Price Prediction

An LSTM+GRU ensemble deep learning model that predicts Indian agricultural commodity prices using weather, mandi, and market data.

## Architecture

```
DATA IN   →  AGMARKNET Prices · IMD Weather · Mandi Arrivals · Festival Calendar
CLEAN     →  Pandas · Fill Missing · Normalize · Create Time Windows  
TRAIN     →  LSTM (3-layer) · GRU (2-layer) · XGBoost Baseline · Ensemble
SERVE     →  FastAPI · Docker · REST API · PostgreSQL + TimescaleDB
APP       →  KrishiMitra Frontend · fetch() API · Price Charts · Hold/Sell Signals
```

## Quick Start

```bash
# 1. Clone & enter project
git clone https://github.com/your-username/krishimitra-ai.git
cd krishimitra-ai

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment config
cp .env.example .env
# Edit .env with your API keys

# 5. Run the API server
uvicorn api.main:app --reload --port 8000

# 6. Open API docs
# Visit http://localhost:8000/docs
```

## Docker

```bash
docker-compose up -d          # Start all services
docker-compose logs -f api    # Watch API logs
docker-compose down           # Stop everything
```

## Training Models

```bash
# Train a single crop model
python -m src.train --crop onion --mandi indore

# Train all crops (batch)
python -m src.train --all
```

## Project Structure

```
krishimitra-ai/
├── data/raw/              ← Downloaded CSVs from AGMARKNET
├── data/processed/        ← Cleaned data
├── data/external/         ← Weather, fuel, festival data
├── notebooks/             ← Jupyter exploration & training
├── src/                   ← Core ML code
│   ├── data_loader.py     ← Data fetching functions
│   ├── features.py        ← Feature engineering
│   ├── model.py           ← LSTM + GRU architecture
│   ├── train.py           ← Training script
│   └── predict.py         ← Prediction runner
├── api/                   ← FastAPI backend
│   ├── main.py            ← App entry point
│   ├── routes.py          ← API endpoints
│   ├── schemas.py         ← Request/response models
│   └── database.py        ← SQLAlchemy + TimescaleDB
├── models/saved/          ← Trained .h5 and .pkl files
├── tests/                 ← Unit tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Key APIs

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/predict/price` | POST | AI price prediction with SHAP |
| `/prices/live` | GET | Today's live mandi prices |
| `/prices/history` | GET | 30-day price history |
| `/mandis/compare` | GET | Compare prices across mandis |
| `/weather/impact` | GET | Weather impact on prices |
| `/alerts/set` | POST | Set price alert |

## Target Metrics

| Model | sMAPE | MAE (₹) | Direction Accuracy |
|---|---|---|---|
| LSTM+GRU Ensemble | <10% | <₹150 | >85% |

## Tech Stack

Python 3.10 · TensorFlow · Keras · FastAPI · PostgreSQL · TimescaleDB · Docker · XGBoost · SHAP

## License

MIT
