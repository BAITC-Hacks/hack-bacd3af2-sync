"""Refit already-selected candidates at an earlier cutoff without February data."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from src.config import MODEL_DIR, PROCESSED_DIR, SELECTION_WINDOWS, TRAINING_CUTOFF
from src.time_utils import local_timestamp
from src.training.validation import load_history, training_before, weather_inputs
from src.training.models import create_model, feature_names, save_model, load_model, parameters
from src.features.build_features import build_features


def prepare(cutoff, output_dir, data_dir=PROCESSED_DIR, selection_dir=MODEL_DIR):
    cutoff = local_timestamp(cutoff)
    if pd.isna(cutoff) or cutoff != cutoff.floor("h") or cutoff > pd.Timestamp(TRAINING_CUTOFF):
        raise ValueError("Snapshot cutoff must be a whole hour no later than February 1")
    if cutoff < max(pd.Timestamp(end) for _, end in SELECTION_WINDOWS):
        raise ValueError("Model selection used data not yet available at this cutoff")
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError("Snapshot output must be a new directory; existing models are never overwritten")
    inputs = []
    for turbine in (1, 2):
        path = Path(data_dir) / f"turbine_{turbine}_hourly.csv"
        history = load_history(path)
        if not history.turbine_id.eq(turbine).all():
            raise ValueError("Turbine identity mismatch")
        meta_path = Path(selection_dir) / f"turbine_{turbine}" / "metadata.json"
        source = json.loads(meta_path.read_text(encoding="utf-8"))
        if source["model_type"] != min(source["selection_mean_mae"], key=source["selection_mean_mae"].get):
            raise ValueError("Selected model disagrees with pre-holdout selection scores")
        if source["parameters"] != parameters(source["model_type"]):
            raise ValueError("Candidate parameters changed since model selection")
        inputs.append((turbine, path, source, training_before(history, cutoff)))
    output_dir.mkdir(parents=True)
    for turbine, path, source, train in inputs:
        name = source["model_type"]
        x = build_features(weather_inputs(train))[feature_names(name)]
        model = create_model(name)
        with threadpool_limits(limits=4):
            model.fit(x, train.power_mean)
        folder = output_dir / f"turbine_{turbine}"
        folder.mkdir()
        artifact = save_model(model, name, folder)
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        np.testing.assert_allclose(model.predict(x.iloc[:32]), load_model(name, artifact).predict(x.iloc[:32]), atol=1e-10)
        source.update(model_file=artifact.name, model_version=f"{name}-{digest[:12]}", artifact_sha256=digest,
                      training_start=train.timestamp.min().isoformat(), training_end=train.timestamp.max().isoformat(),
                      training_last_available_at=train.available_at.max().isoformat(),
                      training_cutoff_exclusive=cutoff.isoformat(), training_rows=len(train),
                      dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      created_at=datetime.now(timezone.utc).isoformat(),
                      selection_available_at=max(end for _, end in SELECTION_WINDOWS),
                      snapshot_note="Pre-holdout selection retained; refit on hours available at cutoff; no snapshot holdout evaluation")
        source.pop("holdout_metrics", None)
        source["limitations"] = ["No February data used", "Archived weather performance has not been evaluated for this snapshot"]
        if name.startswith("catboost"):
            source["feature_importance"] = dict(zip(feature_names(name), model.feature_importances_.tolist()))
        (folder / "metadata.json").write_text(json.dumps(source, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(f"Turbine {turbine}: snapshot through {source['training_end']}, {len(train)} hours", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", default="2026-01-31 00:00:00")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--selection-dir", type=Path, default=MODEL_DIR)
    args = parser.parse_args()
    prepare(args.cutoff, args.output_dir, args.data_dir, args.selection_dir)


if __name__ == "__main__":
    main()
