# Hospital Risk Velocity Engine 🏥 📈

An executive-level surveillance dashboard that applies **kinematic principles (Velocity & Acceleration)** to hospital incident data. Instead of just tracking incident volume, this engine identifies "Risk Surges" by calculating the momentum of harm.

## 🚀 The Core Theory: Harm Kinematics
Standard hospital reporting is **reactive**, focusing on static counts. This engine applies **Classical Mechanics** to patient safety data:

1.  **Quantization (Position):** We map categorical Harm Levels (A-I) to a numerical **Risk Priority Number (RPN)**. 
    * *Scale:* A=1 (Near Miss) ... I=9 (Death).
2.  **Risk Velocity ($v$):** The first derivative of risk. It measures the speed at which harm is accumulating over a sliding window ($w$).
3.  **Risk Acceleration ($a$):** The second derivative. This is our **Early Warning Signal**. It detects if risk is *compounding* (increasing at an increasing rate), predicting a systemic breakdown before it occurs.



## 📊 Data Engineering & Methodology

### 1. The NCC MERP Mapping
We use a linear quantization scale to transform the **NCC MERP Index** (National Coordinating Council for Medication Error Reporting and Prevention) into a computable metric:
| Harm Level | Description | RPN Score |
| :--- | :--- | :--- |
| **A - D** | No Harm / Near Miss | 1 - 4 |
| **E - H** | Permanent / Temporary Harm | 5 - 8 |
| **I** | Death | 9 |

### 2. The "Risk Position" (Aggregation)
To determine the "Position" of a unit in the risk field at any time ($t$), we calculate the **Total Risk Magnitude**:
$$RPN_{total} = \sum (Harm\_Scores)$$
**Why Sum?** By using the sum (which is effectively Average Severity $\times$ Incident Count), we ensure that the engine is sensitive to both **Volume** (many small incidents) and **Gravity** (one major event). Unlike a Median or Mean, the Sum ensures that high-severity "Black Swan" events are never mathematically suppressed.

### 3. The Kinetic Algorithm
Using a discrete time-step ($\Delta t$) defined by the user-selected window ($w$):

* **Velocity ($v$):** $$v = \frac{RPN_t - RPN_{t-w}}{w}$$
* **Acceleration ($a$):** $$a = \frac{v_t - v_{t-w}}{w}$$



## 🛠️ Features
- **Dynamic Sensitivity:** Toggle between Tactical (3-day), Operational (7-day), and Strategic (15-day) views.
- **Automated Hotspot Detection:** The app automatically identifies the specific unit with the highest risk momentum (Acceleration).
- **Apple-Matte UI:** A clean, executive-friendly interface built with Streamlit.
- **Strategic Action Plan:** Automatically generates intervention recommendations based on data trends.

## 📦 Installation & Usage
1. **Clone the repository.**
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Generate the static brief:** `python risk_velocity_engine.py`
4. **Launch the dashboard:** `streamlit run app.py`

## 📂 Project Structure
* `app.py`: The Streamlit dashboard and UI logic.
* `risk_velocity_engine.py`: The backend calculation and PNG report generator.
* `mock_dataset.py`: Script to generate 500+ rows of synthetic clinical data.
* `hospital_risk_data.csv`: The quantized dataset for analysis.