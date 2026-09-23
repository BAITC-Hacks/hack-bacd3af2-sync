"""Generate EDA figures and a report from hourly data without fitting a model."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.config import PROCESSED_DIR, REPORT_DIR

COLORS = ("#087f8c", "#c65b26")


def generate(data_dir: Path, report_dir: Path) -> None:
    figures = report_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    data = [pd.read_csv(data_dir / f"turbine_{i}_hourly.csv", parse_dates=["timestamp", "available_at"])
            for i in (1, 2)]
    # A persisted Boolean flag must agree with counts before filtering.
    for frame in data:
        counts = frame[["observation_count", "wind_speed_count", "temperature_count", "power_count"]]
        if not frame.training_eligible.eq(counts.eq(6).all(axis=1)).all():
            raise ValueError("training_eligible disagrees with coverage counts")
    complete = [frame.loc[frame.training_eligible].copy() for frame in data]
    if any(frame.empty for frame in complete):
        raise ValueError("EDA requires at least one complete hour for each turbine")
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.titleweight": "bold"})
    names = []

    def save(fig, name, title):
        fig.suptitle(title, fontsize=15, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, .94))
        fig.savefig(figures / f"{name}.png", dpi=150)
        plt.close(fig)
        names.append((name, title))

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, col, label in zip(axes, ("power_mean", "wind_speed_mean", "temperature_mean"),
                              ("Normalized power", "Wind speed (m/s)", "Temperature (°C)")):
        values = pd.concat([d[col] for d in complete])
        bins = np.linspace(values.min(), values.max(), 41)
        for i, frame in enumerate(complete):
            ax.hist(frame[col], bins=bins, density=True, histtype="step", linewidth=2, color=COLORS[i], label=f"Turbine {i+1}")
        ax.set(xlabel=label, ylabel="Density")
        ax.legend()
    save(fig, "distributions", "Distributions of complete hourly measurements")

    for col, label, name in (("wind_speed_mean", "Wind speed (m/s)", "wind_power"),
                             ("temperature_mean", "Temperature (°C)", "temperature_power")):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        for i, (ax, frame) in enumerate(zip(axes, complete)):
            dots = ax.hexbin(frame[col], frame.power_mean, gridsize=55, mincnt=1, bins="log", cmap="viridis")
            fig.colorbar(dots, ax=ax, label="Hour count (log scale)")
            ax.set(title=f"Turbine {i+1}", xlabel=label, ylabel="Normalized power", ylim=(-.02, 1.02))
        save(fig, name, f"{label.split(' (')[0]} versus power: all complete hours")

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    curves = []
    for i, frame in enumerate(complete):
        bins = np.floor(frame.wind_speed_mean).astype(int)
        curve = frame.groupby(bins).power_mean.agg(["mean", "count", "std"]).reset_index()
        curve = curve.rename(columns={"wind_speed_mean": "wind_bin_lower"})
        curve["turbine_id"] = i + 1
        curves.append(curve)
        x = curve.wind_bin_lower + .5
        axes[0].plot(x, curve["mean"], "o-", label=f"Turbine {i+1}", color=COLORS[i])
        axes[1].plot(x, curve["count"], "o-", color=COLORS[i])
    axes[0].set(ylabel="Mean normalized power", ylim=(-.02, 1.02))
    axes[0].legend()
    axes[1].set(xlabel="Wind speed bin midpoint (m/s); bins are [lower, lower + 1)", ylabel="Complete hours", yscale="log")
    save(fig, "power_curve", "Empirical power curve and supporting sample counts")
    pd.concat(curves).to_csv(report_dir / "power_curve.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for i, (ax, frame) in enumerate(zip(axes, data)):
        series = frame.set_index("timestamp").power_mean.where(frame.set_index("timestamp").training_eligible)
        ax.plot(series.resample("D").mean(), color=COLORS[i], linewidth=.8)
        ax.set(title=f"Turbine {i+1}", ylabel="Daily mean power", ylim=(0, 1))
    axes[1].set_xlabel("Source-local date; daily averages of available complete hours")
    save(fig, "power_time", "Power over time (missing days remain gaps)")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for i, frame in enumerate(complete):
        for ax, key, label in ((axes[0], frame.timestamp.dt.month, "Month of year"),
                                (axes[1], frame.timestamp.dt.hour, "Source-local hour")):
            profile = frame.groupby(key).power_mean.mean()
            ax.plot(profile.index, profile.values, "o-", color=COLORS[i], label=f"Turbine {i+1}")
            ax.set(xlabel=label, ylabel="Mean normalized power")
            ax.legend()
    axes[0].set_xticks(range(1, 13))
    axes[1].set_xticks(range(0, 24, 3))
    save(fig, "seasonality", "Descriptive seasonal profiles (coverage varies by period)")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for i, (ax, frame) in enumerate(zip(axes, complete)):
        corr = frame[["wind_speed_mean", "temperature_mean", "power_mean"]].corr()
        im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(3), ["Wind", "Temperature", "Power"])
        ax.set_yticks(range(3), ["Wind", "Temperature", "Power"])
        for row in range(3):
            for col in range(3):
                value = corr.iloc[row, col]
                ax.text(col, row, f"{value:.2f}", ha="center", va="center", color="white" if abs(value) > .6 else "black")
        ax.set_title(f"Turbine {i+1}")
        fig.colorbar(im, ax=ax, label="Pearson correlation")
    save(fig, "correlations", "Hourly correlations; association does not establish causation")

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for i, frame in enumerate(data):
        daily = frame.set_index("timestamp").observation_count.resample("D").sum() / 144
        axes[1].plot(daily.index, daily.values, linewidth=.8, label=f"Turbine {i+1}", color=COLORS[i])
        monthly = frame.set_index("timestamp").observation_count.resample("MS").sum()
        axes[0].plot(monthly.index, monthly.values, "o-", label=f"Turbine {i+1}", color=COLORS[i])
    axes[0].set(ylabel="10-minute observations")
    axes[1].set(ylabel="Daily coverage fraction", xlabel="Source-local date", ylim=(-.03, 1.05))
    axes[0].legend()
    save(fig, "coverage", "Monthly observations and daily gaps")

    paired = complete[0][["timestamp", "power_mean"]].merge(complete[1][["timestamp", "power_mean"]], on="timestamp", suffixes=("_1", "_2"))
    fig, ax = plt.subplots(figsize=(6, 5))
    dots = ax.hexbin(paired.power_mean_1, paired.power_mean_2, gridsize=45, mincnt=1, bins="log", cmap="viridis")
    fig.colorbar(dots, ax=ax, label="Paired hour count (log scale)")
    ax.plot([0, 1], [0, 1], "--", color="#ba3b37")
    ax.set(xlabel="Turbine 1 normalized power", ylabel="Turbine 2 normalized power")
    save(fig, "turbine_comparison", "Turbines compared at matching complete hours")

    lines = ["# Exploratory data analysis", "", "Stage 2 uses the supplied historical measurements only. These are descriptive statistics, not forecast validation scores.", "",
             "Sensor charts use hours with six finite, physically admissible values for every sensor. Coverage charts include every hour. No imputation is applied.", "",
             "| Turbine | Total hours | Complete hours | Empty hours | Partial hours |", "| --- | ---: | ---: | ---: | ---: |"]
    for i, frame in enumerate(data):
        lines.append(f"| {i+1} | {len(frame)} | {len(complete[i])} | {frame.observation_count.eq(0).sum()} | {frame.observation_count.between(1,5).sum()} |")
    lines += ["", f"Turbine comparison uses {len(paired):,} matching complete hours. Mean absolute power difference: {(paired.power_mean_1 - paired.power_mean_2).abs().mean():.4f} normalized units.", "",
              "## Wind and power findings", "",
              "Fixed wind bins describe the empirical relationship; counts expose how much evidence supports each mean.", "",
              "| Turbine | Wind bin (m/s) | Mean normalized power | Complete hours |",
              "| --- | --- | ---: | ---: |"]
    for curve in curves:
        for _, row in curve.loc[curve.wind_bin_lower.isin([3, 7, 11, 13, 18])].iterrows():
            lower = int(row.wind_bin_lower)
            lines.append(f"| {int(row.turbine_id)} | [{lower}, {lower+1}) | {row['mean']:.4f} | {int(row['count'])} |")
    lines += ["", "For these datasets, the curves rise steeply through intermediate wind speeds and approach a plateau around 11–13 m/s. Both turbines have similar curves. The thin high-wind tail cannot establish a cut-out threshold.", "",
              "The paired plot also contains observations far from equal output. Retain these for review; the supplied columns alone cannot establish whether curtailment, availability or sensor behavior explains the differences.", "",
              "## Interpretation limits", "",
              "- Power curves use fixed 1 m/s bins and include counts. Sparse high-wind bins should not determine a cut-out rule or extrapolation policy.",
              "- Seasonal profiles pool years and reflect the available coverage. Missing periods can bias these averages.",
              "- The hourly target is the arithmetic mean of six equally spaced power samples, not energy in kWh.",
              "- Wind and temperature here are observed measurements. They cannot replace archived forecast weather in a historical operational backtest.",
              "- All clock times mean Asia/Almaty; no UTC conversion is applied. Backend supplies aligned weather in the same timezone.",
              "- Warm regional temperatures are retained and are not flagged as temperature outliers.", ""]
    for name, title in names:
        lines += [f"## {title}", "", f"![{title}](figures/{name}.png)", ""]
    (report_dir / "eda.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved {len(names)} figures and eda.md to {report_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    generate(args.data_dir, args.report_dir)


if __name__ == "__main__":
    main()
