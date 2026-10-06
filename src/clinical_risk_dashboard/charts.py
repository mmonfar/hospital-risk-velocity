"""Plotly figures, styled with the bundled theme.

Sequential teal only, no categorical rainbow; threshold lines dashed at 34 % ink; chart
titles are the template's teal label. Inputs are ``risk_kinematics`` outputs or plain
display aggregations (sums per category/unit/week) of the scored incident log.
"""

from typing import cast

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from clinical_risk_dashboard import brand as tokens

tokens.register_plotly()
pio.templates.default = "mmonfar"

TEMPLATE = "mmonfar"
TRACE = "rgba(0, 128, 128, 0.42)"  # brand "trace"
BAND = "rgba(0, 128, 128, 0.16)"  # brand "band"
THRESHOLD = "rgba(23, 36, 43, 0.34)"  # brand threshold line: canvas at 34 %
INK_LABEL = "rgba(23, 36, 43, 0.62)"  # brand secondary text: canvas at 62 %
# The on-light teal cascade, light to dark: the brand's only tint ramp.
CASCADE = ["#FDFBF7", "#E4EFEB", "#BBDBD8", "#ACD4D1", "#89C2C0", "#60AFAD", tokens.TEAL]
PLOT_CONFIG = {"displayModeBar": False}
_MARGIN = {"t": 48, "b": 24, "l": 48, "r": 16}


def spc_chart(
    daily: pd.DataFrame, ucl: float, sigma: float, rising_trend: bool = False
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=daily["Date"], y=daily["weighted_score"], name="Daily", line={"color": TRACE})
    )
    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["smooth"],
            name="Trend",
            line={"color": tokens.TEAL, "width": 3},
        )
    )
    fig.add_hline(
        y=ucl,
        line_dash="5px,5px",
        line_color=THRESHOLD,
        annotation_text=f"TOLERANCE ({sigma:g}σ)",
        annotation_font_color=INK_LABEL,
    )
    if rising_trend and not daily.empty:
        last = daily.iloc[-1]
        fig.add_annotation(
            x=last["Date"],
            y=last["smooth"],
            text="RISING TREND",
            showarrow=True,
            ax=-40,
            ay=-30,
            font={"color": INK_LABEL},
        )
    fig.update_layout(
        title="STATISTICAL CONTROL (SPC)",
        height=300,
        template=TEMPLATE,
        margin=_MARGIN,
        showlegend=False,
    )
    return fig


def acceleration_chart(daily: pd.DataFrame) -> go.Figure:
    fig = px.area(daily, x="Date", y="acceleration", template=TEMPLATE)
    fig.update_traces(line_color=tokens.TEAL, fillcolor=BAND)
    fig.update_layout(
        title="TREND ACCELERATION", height=220, margin=_MARGIN, xaxis_title="", yaxis_title=""
    )
    return fig


def harm_distribution_chart(df: pd.DataFrame) -> go.Figure:
    cat_sum = cast(pd.Series, df.groupby("Category")["weighted_score"].sum()).sort_values()
    fig = go.Figure(
        go.Bar(
            x=cat_sum.values,
            y=cat_sum.index,
            orientation="h",
            marker={"color": tokens.TEAL},
            text=[f"{str(cat).upper()}  ·  {val:,.0f} RPN" for cat, val in cat_sum.items()],
            textposition="inside",
            insidetextanchor="end",
            textfont={"family": tokens.LABEL_FONT_STACK, "size": 12, "color": tokens.CREAM},
        )
    )
    fig.update_layout(
        title="HARM DISTRIBUTION",
        height=544,
        bargap=0.25,
        template=TEMPLATE,
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"t": 48, "b": 16, "l": 8, "r": 8},
    )
    return fig


def intensity_matrix(df: pd.DataFrame) -> go.Figure:
    totals = cast(pd.Series, df.groupby(["Date", "Unit"])["weighted_score"].sum())
    pivot = totals.unstack().fillna(0)
    if not pivot.empty:  # complete daily calendar: quiet days are zero, not missing
        pivot = pivot.reindex(
            pd.date_range(pivot.index.min(), pivot.index.max(), freq="D"), fill_value=0
        )
    heat = pivot.resample("W").sum().T
    fig = px.imshow(heat, color_continuous_scale=CASCADE, aspect="auto", template=TEMPLATE)
    fig.update_layout(
        height=300,
        xaxis_title="",
        yaxis_title="",
        coloraxis_showscale=False,
        margin={"t": 8, "b": 8, "l": 8, "r": 8},
    )
    return fig
