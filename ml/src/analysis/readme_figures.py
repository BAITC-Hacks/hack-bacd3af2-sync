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
COLORS = ("#168B91", "#E69654")
NOTE = "Декабрь 2025 — январь 2026 · проверка на фактической погоде"


def main():
    out = REPORTS / "figures"
    out.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.labelcolor": "#263445",
                         "text.color": "#263445", "figure.facecolor": "#F5F8FA",
                         "axes.facecolor": "#F5F8FA", "axes.edgecolor": "#D7E0E7",
                         "xtick.color": "#64748B", "ytick.color": "#64748B",
                         "axes.axisbelow": True, "savefig.facecolor": "#F5F8FA"})
    data = {}
    for tid in (1, 2):
        frame = pd.read_csv(REPORTS / f"turbine_{tid}_validation_predictions.csv.gz",
                            parse_dates=["timestamp", "forecast_origin"])
        data[tid] = frame.loc[frame.window.eq("holdout")].copy()

    def save(fig, name, title, subtitle, footer):
        fig.suptitle(title, x=.075, y=.96, ha="left", fontsize=17, fontweight="bold")
        fig.text(.075, .897, subtitle, fontsize=9, color="#64748B")
        fig.text(.075, .035, footer, fontsize=8, color="#64748B")
        fig.savefig(out / name, dpi=140)
        plt.close(fig)
        print(out / name)

    # Deduplicate overlapping origins for the physical relationship plot.
    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.subplots_adjust(left=.09, right=.96, bottom=.16, top=.83)
    for tid, color in zip((1, 2), COLORS):
        frame = data[tid].sort_values("forecast_origin").drop_duplicates("timestamp").copy()
        frame["bin"] = np.floor(frame.wind_speed_mean).astype(int)
        curve = frame.groupby("bin").agg(actual=("power_mean", "mean"),
                    predicted=("catboost_weather", "mean"), n=("power_mean", "size"))
        curve = curve.reindex(range(int(curve.index.max()) + 1))
        curve.loc[curve.n.lt(20), ["actual", "predicted"]] = np.nan
        x = curve.index.to_numpy() + .5
        ax.plot(x, curve.actual, color=color, marker="o", markersize=4, lw=2.3, label=f"Турбина {tid} · факт")
        ax.plot(x, curve.predicted, color=color, ls="--", lw=2.3, label=f"Турбина {tid} · модель")
    ax.set(xlabel="Скорость ветра, м/с", ylabel="Мощность · 1 = 100% номинальной", ylim=(0, 1.05))
    ax.grid(axis="y", alpha=.18)
    ax.legend(ncol=2, loc="upper left", frameon=False, fontsize=9)
    save(fig, "readme_power_curve.png", "Больше ветра — больше мощности", NOTE,
         "Средние по диапазонам 1 м/с · не менее 20 уникальных часов в каждом диапазоне")

    names = ["persistence", "seasonal_persistence", "power_curve", "catboost_weather"]
    labels = ["Последнее\nзначение", "Предыдущий\nдень", "Зависимость\nот ветра", "CatBoost"]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.subplots_adjust(left=.09, right=.96, bottom=.18, top=.81)
    for tid, color, shift in ((1, COLORS[0], -.19), (2, COLORS[1], .19)):
        frame = data[tid]
        maes = [float((frame[name] - frame.power_mean).abs().mean()) for name in names]
        saved = json.loads((REPORTS.parent / f"models/turbine_{tid}/metrics.json").read_text())
        for name, value in zip(names, maes):
            assert np.isclose(value, saved["holdout"]["models"][name]["overall"]["mae"], atol=1e-12)
        bars = ax.bar(np.arange(4)+shift, maes, .32, color=color, label=f"Турбина {tid}")
        ax.bar_label(bars, labels=[f"{v:.3f}".replace('.', ',') for v in maes], padding=5, fontsize=10)
    ax.set(xticks=np.arange(4), xticklabels=labels, ylabel="Средняя ошибка (MAE) · меньше — лучше", ylim=(0,.45))
    ax.grid(axis="y", alpha=.18)
    ax.legend(frameon=False, loc="upper right")
    save(fig, "readme_baseline_mae.png", "CatBoost: средняя ошибка ниже на 29%", NOTE,
         "Сравнение с зависимостью от ветра · первые два способа погоду не используют")

    origins = pd.to_datetime(["2025-12-05", "2025-12-20", "2026-01-15"])
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.3), sharey=True)
    fig.subplots_adjust(left=.11, right=.97, bottom=.17, top=.79, wspace=.20, hspace=.55)
    for row, tid in enumerate((1,2)):
        for col, origin in enumerate(origins):
            ax = axes[row,col]
            frame = data[tid].loc[data[tid].forecast_origin.eq(origin)].set_index("timestamp")
            assert not frame.empty and frame.index.is_unique
            frame = frame.reindex(pd.date_range(origin, periods=48, freq="h"))
            ax.plot(frame.index, frame.power_mean, color="#334155", lw=1.8, label="Факт")
            ax.plot(frame.index, frame.catboost_weather, color=COLORS[row], lw=2, ls="--", label="Модель")
            mae = (frame.power_mean-frame.catboost_weather).abs().mean()
            ax.set_title(f"{origin:%d.%m.%Y} · 48 часов\nMAE {mae:.3f}".replace('MAE 0.', 'MAE 0,'), fontsize=10, loc="left")
            ax.set_ylim(-.04,1.04)
            ax.xaxis.set_major_locator(mdates.DayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
            ax.tick_params(axis="x", labelsize=9)
            ax.grid(alpha=.15)
            if col == 0:
                ax.set_ylabel(f"Турбина {tid}\nМощность, 0–1")
                ax.legend(frameon=False, fontsize=8, loc="upper right")
    save(fig, "readme_holdout_prediction_vs_actual.png", "Модель видит подъёмы и спады", NOTE,
         "Три фиксированных окна без отбора лучших ошибок · время Asia/Almaty")

    edges = [0,3,6,9,12,np.inf]
    bins = ["0–3", "3–6", "6–9", "9–12", "12+"]
    fig, ax = plt.subplots(figsize=(10,5.8))
    fig.subplots_adjust(left=.09, right=.96, bottom=.18, top=.81)
    maximum = 0
    for tid, color, shift in ((1,COLORS[0],-.19),(2,COLORS[1],.19)):
        frame = data[tid].assign(error=(data[tid].catboost_weather-data[tid].power_mean).abs())
        groups = frame.groupby(pd.cut(frame.wind_speed_mean,edges,right=False,labels=bins),observed=True).error.agg(["mean","size"]).reindex(bins)
        assert groups["size"].sum() == len(frame)
        saved = json.loads((REPORTS.parent / f"models/turbine_{tid}/metrics.json").read_text())
        for label, value in groups["mean"].items():
            assert np.isclose(value,saved["holdout"]["models"]["catboost_weather"]["by_wind_bin"][label.replace("–","-")]["mae"],atol=1e-12)
        bars = ax.bar(np.arange(5)+shift,groups["mean"],.32,color=color,label=f"Турбина {tid}")
        ax.bar_label(bars,labels=[f"{v:.3f}".replace('.', ',') for v in groups["mean"]],padding=5,fontsize=10)
        maximum=max(maximum,float(groups["mean"].max()))
    ax.set(xticks=np.arange(5),xticklabels=bins,xlabel="Скорость ветра, м/с",
           ylabel="Средняя ошибка (MAE) · меньше — лучше",ylim=(0,maximum*1.42))
    ax.grid(axis="y",alpha=.18)
    ax.legend(frameon=False,loc="upper left")
    save(fig,"readme_mae_by_wind_bin.png","При каком ветре ошибка выше",NOTE,
         "Один час может оцениваться с разных дат прогноза · ошибка всей погодной цепочки здесь не измерена")


if __name__ == "__main__":
    main()
