# 🏥 Hospital Risk Intelligence Portal (V2)
### *Kinetic Surveillance & Predictive Harm Intelligence*

An executive-level surveillance engine that applies **kinematic principles (Velocity & Acceleration)** to hospital incident data. Instead of tracking static incident counts, this system identifies "Risk Surges" by calculating the momentum and pressure of harm before sentinel events occur.

## 🚀 The Strategic Theory: Harm Kinematics
Standard hospital reporting is **reactive**. This engine bridges the gap between the ICU and the Boardroom by applying **Classical Mechanics** to patient safety data:

1. **Quantization (Position):** Categorical Harm Levels (A-I) are encoded into a continuous **Risk Priority Number (RPN)**.
2. **Risk Velocity ($v$):** The first derivative of risk. It measures the rate at which harm accumulates over a sliding window ($w$).
3. **Risk Acceleration ($a$):** The second derivative. This is the **Early Warning Signal**. It detects if risk is *compounding*, predicting systemic breakdown.

## 📊 Methodology & Risk Appetite

### 1. Statistical Tolerance (The Sigma Filter)
The engine utilizes a **Risk Appetite Selector** allowing executives to define their tolerance for variance:
* **Zero Tolerance ($1\sigma$):** Alerts on top 32% of deviations.
* **Standard Oversight ($2\sigma$):** Alerts on top 5% (Statistical Outliers).
* **Critical Focus ($3\sigma$):** Alerts only on the top 0.3% of extreme events.



### 2. The Kinetic Algorithm
Using a discrete time-step ($\Delta t$) defined by the user-selected window ($w$):
* **Velocity ($v$):** $$v = \frac{RPN_t - RPN_{t-w}}{w}$$
* **Acceleration ($a$):** $$a = \frac{v_t - v_{t-w}}{w}$$

## 📂 System Architecture (Modular)
To ensure scalability and clinical reliability, the portal is architected into discrete functional modules:

* `app.py`: **The Orchestrator.** Manages the Streamlit UI and executive dashboard state.
* `risk_engine.py`: **The Mathematical Brain.** Contains the proprietary logic for RPN quantization, velocity derivatives, and Z-score thresholding.
* `ui_styles.py`: **The Design System.** Defines the Apple-matte UI/CSS and clinical nomenclature (NCC MERP mapping).
* `hospital_risk_data.csv`: The clinical dataset.

## 🛠️ Deployment
1. **Activate Environment:** `.\venv\Scripts\Activate.ps1`
2. **Install Dependencies:** `pip install -r requirements.txt`
3. **Launch Portal:** `streamlit run app.py`