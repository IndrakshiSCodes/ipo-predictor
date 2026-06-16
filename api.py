from auth import router as auth_router
from database import init_db
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'ipo_enriched_final.csv')

MODEL_DIR = os.path.join(BASE_DIR, 'ml', 'models')
model = joblib.load(os.path.join(MODEL_DIR, 'ipo_predictor_rf.pkl'))
explainer = joblib.load(os.path.join(MODEL_DIR, 'shap_explainer.pkl'))
with open(os.path.join(MODEL_DIR, 'features.json')) as f:
    FEATURES = json.load(f)

app = FastAPI(
    title="ListIQ API",
    description="IPO listing gain prediction API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router, prefix="/auth")

@app.on_event("startup")
def startup():
    init_db()

class IPOInput(BaseModel):
    issue_price: float
    issue_amount_cr: float
    lot_size: float
    qib_x: float
    nii_x: float
    retail_x: float
    total_x: float
    gmp: float
    gmp_percent: float
    is_mainboard: int
    listing_year: int
    listing_month: int

@app.get("/")
def root():
    return {
        "name": "ListIQ API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(data: IPOInput):
    try:
        input_df = pd.DataFrame([data.dict()])
        input_df = input_df[FEATURES]

        prediction = float(model.predict(input_df)[0])
        expected_price = data.issue_price * (1 + prediction / 100)

        if prediction >= 20:
            signal = "strong"
        elif prediction >= 5:
            signal = "moderate"
        elif prediction >= 0:
            signal = "weak"
        else:
            signal = "avoid"

        shap_values = explainer.shap_values(input_df)
        shap_contributions = [
            {
                "feature": feat,
                "value": float(input_df[feat].iloc[0]),
                "impact": float(shap_values[0][i])
            }
            for i, feat in enumerate(FEATURES)
        ]
        shap_contributions.sort(key=lambda x: abs(x["impact"]), reverse=True)

        return {
            "prediction": round(prediction, 2),
            "expected_listing_price": round(expected_price, 2),
            "signal": signal,
            "shap_contributions": shap_contributions,
            "model": "Random Forest",
            "r2_score": 0.50
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/historical")
def historical(limit: int = 500):
    try:
        df = pd.read_csv(DATA_PATH)
        df = df.sort_values('listing_date', ascending=False).head(limit)
        df = df[[
            'ipo_name', 'listing_date', 'listing_year',
            'issue_price', 'qib_x', 'nii_x', 'retail_x',
            'gmp_percent', 'listing_gain_pct'
        ]].fillna(0)
        return {"data": df.to_dict(orient='records'), "total": len(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/summary")
def analytics_summary():
    try:
        df = pd.read_csv(DATA_PATH)
        yearly = df.groupby('listing_year')['listing_gain_pct'].agg(
            ['mean', 'count', 'std']
        ).reset_index()
        yearly.columns = ['year', 'avg_gain', 'count', 'std']

        return {
            "total_ipos": len(df),
            "avg_gain": round(float(df['listing_gain_pct'].mean()), 2),
            "best_gain": round(float(df['listing_gain_pct'].max()), 2),
            "worst_loss": round(float(df['listing_gain_pct'].min()), 2),
            "yearly": yearly.to_dict(orient='records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))