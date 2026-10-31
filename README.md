# 🏥 Hospital Risk Intelligence Portal (v2.1)
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

## 📸 What it looks like (v2.1.0)
Desktop (1440 px):

![Risk early warning dashboard, desktop view](docs/screenshots/app_v2_1440.png)

Phone (390 px):

![Risk early warning dashboard, phone view](docs/screenshots/app_v2_390.png)

The page opens on the unit with the highest risk. Each card says in words what it shows. The status card gives the reason in one line. The Momentum card shows the latest day and the trend side by side, so the two never contradict each other.

## 📂 System Architecture (Modular)
* `app.py`: **The Orchestrator.** Streamlit page: unit, period, window and tolerance selectors, wired to the engine.
* `risk_kinematics/`: **The Mathematical Brain.** `harm.py` (harm levels A-I to RPN weights) and `kinetics.py` (velocity, acceleration, control limit, sigma, strategic status, trend rule).
* `clinical_risk_dashboard/presentation.py`: **Words and colours.** Status labels, reason lines, momentum text. It computes no risk number.
* `clinical_risk_dashboard/view.py`: **HTML parts.** KPI cards, SVG trend, drivers, footer.
* `clinical_risk_dashboard/static/`: **Design system.** One stylesheet and the font (SIL OFL), loaded from disk. No network call.
* `clinical_risk_dashboard/sample_data.py`: **Synthetic incident log** used by the page.
* `tests/`: **224 tests.** Dashboard (page, presentation, view, sample data) and engine characterisation tests.
* `hospital_risk_data.csv`: example dataset (synthetic).

## 🛠️ Deployment
1. **Create an environment:** `python -m venv venv`, then activate it (`.env\Scripts\Activate.ps1` on Windows).
2. **Install dependencies:** `pip install -r requirements.txt` (Streamlit 1.64 or newer, pandas, numpy). For tests also `pip install pytest`.
3. **Launch the portal** from the repository root: `streamlit run app.py`
4. **Run the tests:** `python -m pytest` (224 tests).

## Licence

Code is licensed under **AGPL-3.0-or-later** (see [`LICENSE`](LICENSE)); a commercial licence is available on request from the author via [LinkedIn](https://www.linkedin.com/in/martin-monteagudo-farina/). Non-code content is under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Details in [`LICENSING.md`](LICENSING.md).

## Disclaimer

Research and demonstration software. Not a medical device and not intended for clinical decision-making, diagnosis or treatment. Provided "as is", without warranty of any kind; the author accepts no liability for any use. Uses synthetic data only.

Built with AI assistance (Claude); all code and claims reviewed by the author. See [`LICENSE`](LICENSE) for the full warranty terms.

## Independence and data notice

**Independence and data notice.** This is a personal project, developed independently in my own time and on my own equipment. It is not affiliated with, endorsed by, or representative of my employer or any other organisation. It contains no employer data, systems, code or confidential information. All data in this repository is synthetic or fictitious, and any resemblance to real patients, staff or events is coincidental. Views are my own.
