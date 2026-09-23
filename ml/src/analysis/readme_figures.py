"""Render presentation figures from saved holdout predictions; never fit/load models."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPORTS = Path(__file__).resolve().parents[2] / "reports"
COLORS = ("#087F8C", "#D66A30")
NOTE = "Observed-weather holdout | Dec 2025–Jan 2026 | Power-model quality, not end-to-end forecast accuracy"


def main():
    out = REPORTS / "figures"
    out.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.labelcolor": "#263445",
                         "text.color": "#263445", "figure.facecolor": "white",
                         "axes.axisbelow": True, "savefig.facecolor": "white"})
    data = {}
    for tid in (1, 2):
        frame = pd.read_csv(REPORTS / f"turbine_{tid}_validation_predictions.csv.gz",
                            parse_dates=["timestamp", "forecast_origin"])
        data[tid] = frame.loc[frame.window.eq("holdout")].copy()

    def save(fig, name, title, subtitle, footer):
        fig.suptitle(title, x=.065, y=.97, ha="left", fontsize=22, fontweight="bold")
        fig.text(.065, .912, subtitle, fontsize=11, color="#596575")
        fig.text(.065, .028, footer, fontsize=10, color="#596575")
        fig.savefig(out / name, dpi=180)
        plt.close(fig)
        print(out / name)

    # Deduplicate overlapping origins for the physical relationship plot.
    fig, ax = plt.subplots(figsize=(13, 7.3))
    fig.subplots_adjust(left=.09, right=.96, bottom=.16, top=.83)
    for tid, color in zip((1, 2), COLORS):
        frame = data[tid].sort_values("forecast_origin").drop_duplicates("timestamp").copy()
        frame["bin"] = np.floor(frame.wind_speed_mean).astype(int)
        curve = frame.groupby("bin").agg(actual=("power_mean", "mean"),
                    predicted=("catboost_weather", "mean"), n=("power_mean", "size"))
        curve = curve.reindex(range(int(curve.index.max()) + 1))
        curve.loc[curve.n.lt(20), ["actual", "predicted"]] = np.nan
        x = curve.index.to_numpy() + .5
        ax.plot(x, curve.actual, color=color, marker="o", lw=2.5, label=f"Turbine {tid} · actual")
        ax.plot(x, curve.predicted, color=color, ls="--", lw=2.5, label=f"Turbine {tid} · CatBoost")
    ax.set(xlabel="Observed wind speed (m/s) · 1 m/s bins", ylabel="Mean normalized power", ylim=(0, 1.05))
    ax.grid(axis="y", alpha=.18)
    ax.legend(ncol=2, loc="upper left", frameon=False, fontsize=11)
    save(fig, "readme_power_curve.png", "Power curve · observed and learned relationship", NOTE,
         "One observation per target hour. Bins with fewer than 20 hours are omitted; curves show empirical agreement, not a physics guarantee.")

    names = ["persistence", "seasonal_persistence", "power_curve", "catboost_weather"]
    labels = ["Persistence", "Seasonal\npersistence", "Power curve", "CatBoost"]
    fig, ax = plt.subplots(figsize=(13, 7.3))
    fig.subplots_adjust(left=.09, right=.96, bottom=.18, top=.81)
    for tid, color, shift in ((1, COLORS[0], -.19), (2, COLORS[1], .19)):
        frame = data[tid]
        maes = [float((frame[name] - frame.power_mean).abs().mean()) for name in names]
        saved = json.loads((REPORTS.parent / f"models/turbine_{tid}/metrics.json").read_text())
        for name, value in zip(names, maes):
            assert np.isclose(value, saved["holdout"]["models"][name]["overall"]["mae"], atol=1e-12)
        bars = ax.bar(np.arange(4)+shift, maes, .35, color=color, label=f"Turbine {tid}")
        ax.bar_label(bars, labels=[f"{v:.4f}" for v in maes], padding=5, fontsize=12)
    ax.set(xticks=np.arange(4), xticklabels=labels, ylabel="MAE · normalized power (lower is better)", ylim=(0,.45))
    ax.grid(axis="y", alpha=.18)
    ax.legend(frameon=False, loc="upper right")
    save(fig, "readme_baseline_mae.png", "CatBoost improves MAE over the empirical power curve", NOTE,
         "MAE reduction vs power curve: T1 29.44% · T2 29.59%. Weather-based models receive actual future weather; persistence does not.")

    origins = pd.to_datetime(["2025-12-05", "2025-12-20", "2026-01-15"])
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), sharey=True)
    fig.subplots_adjust(left=.065, right=.98, bottom=.17, top=.79, wspace=.13, hspace=.55)
    for row, tid in enumerate((1,2)):
        for col, origin in enumerate(origins):
            ax = axes[row,col]
            frame = data[tid].loc[data[tid].forecast_origin.eq(origin)].set_index("timestamp")
            assert not frame.empty and frame.index.is_unique
            frame = frame.reindex(pd.date_range(origin, periods=48, freq="h"))
            ax.plot(frame.index, frame.power_mean, color="#263445", lw=2, label="Actual power")
            ax.plot(frame.index, frame.catboost_weather, color=COLORS[row], lw=2, ls="--", label="CatBoost")
            mae = (frame.power_mean-frame.catboost_weather).abs().mean()
            ax.set_title(f"{origin:%d %b %Y} · 48h\nMAE {mae:.4f}", fontsize=12, loc="left")
            ax.set_ylim(-.04,1.04)
            ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0,12]))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M"))
            ax.tick_params(axis="x", labelsize=9)
            ax.grid(alpha=.15)
            if col == 0:
                ax.set_ylabel(f"Turbine {tid}\nNormalized power")
                ax.legend(frameon=False, fontsize=10, loc="upper right")
    save(fig, "readme_holdout_prediction_vs_actual.png", "Holdout examples · predicted and actual power", NOTE,
         "Fixed illustrative origins, not ranked by error. Asia/Almaty; each window starts at origin. Missing eligible hours remain gaps.")

    edges = [0,3,6,9,12,np.inf]
    bins = ["0–3", "3–6", "6–9", "9–12", "12+"]
    fig, ax = plt.subplots(figsize=(13,7.3))
    fig.subplots_adjust(left=.09, right=.96, bottom=.18, top=.81)
    maximum = 0
    for tid, color, shift in ((1,COLORS[0],-.19),(2,COLORS[1],.19)):
        frame = data[tid].assign(error=(data[tid].catboost_weather-data[tid].power_mean).abs())
        groups = frame.groupby(pd.cut(frame.wind_speed_mean,edges,right=False,labels=bins),observed=True).error.agg(["mean","size"]).reindex(bins)
        assert groups["size"].sum() == len(frame)
        saved = json.loads((REPORTS.parent / f"models/turbine_{tid}/metrics.json").read_text())
        for label, value in groups["mean"].items():
            assert np.isclose(value,saved["holdout"]["models"]["catboost_weather"]["by_wind_bin"][label.replace("–","-")]["mae"],atol=1e-12)
        bars = ax.bar(np.arange(5)+shift,groups["mean"],.35,color=color,label=f"Turbine {tid}")
        ax.bar_label(bars,labels=[f"{v:.4f}\nn={int(n):,}" for v,n in zip(groups["mean"],groups["size"])],padding=5,fontsize=10)
        maximum=max(maximum,float(groups["mean"].max()))
    ax.set(xticks=np.arange(5),xticklabels=bins,xlabel="Observed wind speed (m/s) · left-inclusive bins",
           ylabel="CatBoost MAE · normalized power",ylim=(0,maximum*1.42))
    ax.grid(axis="y",alpha=.18)
    ax.legend(frameon=False,loc="upper left")
    save(fig,"readme_mae_by_wind_bin.png","Where the model is accurate · error by wind speed",NOTE,
         "n = origin–target pairs, not independent hours. Overlapping targets count per origin, matching the saved validation metrics.")


if __name__ == "__main__":
    main()
