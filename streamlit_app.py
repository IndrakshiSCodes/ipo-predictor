import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap
import joblib
import json
import os

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IPO Listing Gain Predictor",
    page_icon="📈",
    layout="wide"
)

# ── Load model and data ───────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    model = joblib.load('ml/models/ipo_predictor_rf.pkl')
    explainer = joblib.load('ml/models/shap_explainer.pkl')
    with open('ml/models/features.json') as f:
        features = json.load(f)
    return model, explainer, features

@st.cache_data
def load_data():
    df = pd.read_csv('data/processed/ipo_enriched_final.csv', parse_dates=['listing_date'])
    return df

model, explainer, FEATURES = load_model()
df = load_data()

# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.title("📈 IPO Predictor")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["🔮 Predict", "📊 Analytics", "📋 Historical Data", "🤖 Model Info"])

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — PREDICT
# ══════════════════════════════════════════════════════════════════════════════
if page == "🔮 Predict":
    st.title("🔮 IPO Listing Gain Predictor")
    st.markdown("Enter IPO details below to predict the expected listing day gain.")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📌 Basic Info")
        issue_price = st.number_input("Issue Price (₹)", min_value=1, max_value=10000, value=200)
        issue_amount_cr = st.number_input("Issue Size (₹ Cr)", min_value=1.0, max_value=50000.0, value=500.0)
        lot_size = st.number_input("Lot Size", min_value=1, max_value=10000, value=75)
        is_mainboard = st.selectbox("Category", ["Mainboard", "SME"])
        is_mainboard = 1 if is_mainboard == "Mainboard" else 0

    with col2:
        st.subheader("📊 Subscription Data")
        qib_x = st.number_input("QIB Subscription (x)", min_value=0.0, max_value=5000.0, value=10.0)
        nii_x = st.number_input("NII Subscription (x)", min_value=0.0, max_value=5000.0, value=15.0)
        retail_x = st.number_input("Retail Subscription (x)", min_value=0.0, max_value=5000.0, value=8.0)
        total_x = st.number_input("Total Subscription (x)", min_value=0.0, max_value=5000.0, value=10.0)

    with col3:
        st.subheader("🌑 Grey Market & Timing")
        gmp = st.number_input("GMP (₹)", min_value=0, max_value=5000, value=30)
        gmp_percent = st.number_input("GMP %", min_value=0.0, max_value=500.0, value=15.0)
        listing_month = st.selectbox("Listing Month", list(range(1, 13)),
                                     format_func=lambda x: ['Jan','Feb','Mar','Apr','May','Jun',
                                                             'Jul','Aug','Sep','Oct','Nov','Dec'][x-1])
        listing_year = st.selectbox("Listing Year", [2024, 2025, 2026])
        pe_ratio = st.number_input("P/E Ratio", min_value=0.0, max_value=500.0, value=25.0)

    st.markdown("---")
    predict_btn = st.button("🚀 Predict Listing Gain", use_container_width=True)

    if predict_btn:
        input_data = pd.DataFrame([{
            'issue_price': issue_price,
            'issue_amount_cr': issue_amount_cr,
            'lot_size': lot_size,
            'qib_x': qib_x,
            'nii_x': nii_x,
            'retail_x': retail_x,
            'total_x': total_x,
            'gmp': gmp,
            'gmp_percent': gmp_percent,
            'is_mainboard': is_mainboard,
            'listing_year': listing_year,
            'listing_month': listing_month
        }])

        prediction = model.predict(input_data)[0]

        # Display result
        st.markdown("### 🎯 Prediction Result")
        col_r1, col_r2, col_r3 = st.columns(3)

        with col_r1:
            color = "green" if prediction > 0 else "red"
            st.metric("Predicted Listing Gain", f"{prediction:.2f}%")

        with col_r2:
            expected_price = issue_price * (1 + prediction/100)
            st.metric("Expected Listing Price", f"₹{expected_price:.2f}")

        with col_r3:
            if prediction >= 20:
                signal = "🟢 Strong Buy Signal"
            elif prediction >= 5:
                signal = "🟡 Moderate — Apply"
            elif prediction >= 0:
                signal = "🟠 Weak — Risky"
            else:
                signal = "🔴 Avoid — Expected Loss"
            st.metric("Signal", signal)

        # SHAP explanation
        st.markdown("### 🧠 Why this prediction?")
        shap_vals = explainer.shap_values(input_data)

        fig, ax = plt.subplots(figsize=(10, 3))
        shap.force_plot(
            explainer.expected_value,
            shap_vals[0],
            input_data,
            feature_names=FEATURES,
            matplotlib=True,
            show=False
        )
        st.pyplot(fig)
        plt.close()

        # Feature contribution table
        contributions = pd.DataFrame({
            'Feature': FEATURES,
            'Value': input_data.iloc[0].values,
            'SHAP Impact': shap_vals[0]
        }).sort_values('SHAP Impact', ascending=False)
        contributions['Direction'] = contributions['SHAP Impact'].apply(
            lambda x: '🟢 Positive' if x > 0 else '🔴 Negative'
        )
        st.dataframe(contributions, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Analytics":
    st.title("📊 IPO Market Analytics")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total IPOs", len(df))
    col2.metric("Avg Listing Gain", f"{df['listing_gain_pct'].mean():.1f}%")
    col3.metric("Best Gain", f"{df['listing_gain_pct'].max():.1f}%")
    col4.metric("Worst Loss", f"{df['listing_gain_pct'].min():.1f}%")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Year-wise Average Gain")
        yearly = df.groupby('listing_year')['listing_gain_pct'].mean()
        fig, ax = plt.subplots(figsize=(8, 4))
        colors = ['#2ecc71' if v > 0 else '#e74c3c' for v in yearly.values]
        ax.bar(yearly.index, yearly.values, color=colors, edgecolor='white')
        ax.axhline(0, color='gray', linewidth=0.8)
        ax.set_xlabel('Year')
        ax.set_ylabel('Avg Gain (%)')
        ax.set_title('Year-wise IPO Performance')
        st.pyplot(fig)
        plt.close()

    with col_b:
        st.subheader("Gain Distribution")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(df['listing_gain_pct'], bins=30, color='steelblue', edgecolor='white', alpha=0.8)
        ax.axvline(df['listing_gain_pct'].mean(), color='red', linestyle='--',
                   label=f"Mean: {df['listing_gain_pct'].mean():.1f}%")
        ax.set_xlabel('Listing Gain (%)')
        ax.set_ylabel('Count')
        ax.set_title('Distribution of Listing Gains')
        ax.legend()
        st.pyplot(fig)
        plt.close()

    st.subheader("GMP % vs Listing Gain")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.scatter(df['gmp_percent'], df['listing_gain_pct'],
               alpha=0.6, color='steelblue', edgecolors='white', linewidth=0.3)
    ax.set_xlabel('GMP %')
    ax.set_ylabel('Listing Gain %')
    ax.set_title('Grey Market Premium vs Actual Listing Gain')
    ax.axhline(0, color='red', linestyle='--', alpha=0.5)
    st.pyplot(fig)
    plt.close()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — HISTORICAL DATA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Historical Data":
    st.title("📋 Historical IPO Data")
    st.markdown("---")

    search = st.text_input("🔍 Search by company name")
    year_filter = st.multiselect("Filter by year", sorted(df['listing_year'].dropna().unique().tolist()))

    df_display = df.copy()
    if search:
        df_display = df_display[df_display['ipo_name'].str.contains(search, case=False, na=False)]
    if year_filter:
        df_display = df_display[df_display['listing_year'].isin(year_filter)]

    df_display = df_display[[
        'ipo_name', 'listing_date', 'listing_year', 'issue_price',
        'qib_x', 'nii_x', 'retail_x', 'gmp_percent', 'listing_gain_pct'
    ]].sort_values('listing_date', ascending=False)

    st.dataframe(df_display, use_container_width=True)
    st.caption(f"Showing {len(df_display)} IPOs")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — MODEL INFO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Model Info":
    st.title("🤖 Model Information")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("Model", "Random Forest")
    col2.metric("R² Score", "0.50")
    col3.metric("Mean Absolute Error", "16.73%")

    st.markdown("""
    ### How it works
    This model predicts the listing day gain percentage for Indian IPOs using:
    - **Grey Market Premium (GMP%)** — strongest signal, 76% feature importance
    - **Subscription data** — QIB, NII, Retail times subscribed
    - **Issue details** — price, size, lot size
    - **Timing** — listing month and year

    ### Data Sources
    - **InvestorGain** — subscription + GMP data (1,380 IPOs, 2019–2026)
    - **IPOCentral** — historical listing performance data

    ### Model Performance
    | Metric | Value |
    |--------|-------|
    | R² Score | 0.50 |
    | MAE | 16.73% |
    | RMSE | 23.96% |
    | Training Data | 128 IPOs |
    | Features | 12 |
    """)

    st.subheader("Feature Importance")
    if os.path.exists('data/processed/plot_feature_importance_v2.png'):
        st.image('data/processed/plot_feature_importance_v2.png')

    st.subheader("SHAP Summary")
    if os.path.exists('data/processed/plot_shap_summary.png'):
        st.image('data/processed/plot_shap_summary.png')