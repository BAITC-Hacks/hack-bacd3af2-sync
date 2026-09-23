import sys, json, hashlib, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

sys.path.insert(0,str(ROOT/'ml'))
import numpy as np
import pandas as pd
from src.data.load import load_raw,parse_raw
from src.data.preprocess import aggregate_hourly
from src.training.validation import load_history,training_before,weather_inputs
from src.features.build_features import build_features
from src.training.models import create_model,load_model
from src.training.train import evaluate_window
parser=argparse.ArgumentParser(description='Read-only model reproduction and backtest audit; existing model artifacts are never changed.')
parser.add_argument('--raw-dir',type=Path,default=ROOT/'ml/data/raw')
parser.add_argument('--output',type=Path,default=ROOT/'ml/reports/audit_verification.json')
args=parser.parse_args()
results={}
for tid in (1,2):
    rawpath=args.raw_dir/f'turbine {tid}.csv'
    raw=load_raw(rawpath)
    hourly,_=aggregate_hourly(parse_raw(raw),tid)
    source=ROOT/f'ml/data/processed/turbine_{tid}_hourly.csv'
    history=load_history(source)
    pd.testing.assert_frame_equal(hourly,history,check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-12)
    record={'raw_rows':len(raw),'raw_sha256':hashlib.sha256(rawpath.read_bytes()).hexdigest(),'hourly_matches_raw':True,'models':[]}
    for sub in ('', 'asof_2026-01-31/'):
        folder=ROOT/f'ml/models/{sub}turbine_{tid}'
        meta=json.loads((folder/'metadata.json').read_text())
        path=folder/'model.cbm'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['artifact_sha256']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==meta['dataset_sha256']
        model=load_model(meta['model_type'],path)
        train=training_before(history,meta['training_cutoff_exclusive'])
        x=build_features(weather_inputs(train))[meta['features']]
        assert len(train)==meta['training_rows']
        fresh=create_model(meta['model_type'])
        fresh.fit(x,train.power_mean)
        delta=float(np.max(np.abs(fresh.predict(x)-model.predict(x))))
        assert delta<1e-12
        record['models'].append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'trees':model.tree_count_,'features':model.feature_names_,'rows':len(train),'start':str(train.timestamp.min()),'end':str(train.timestamp.max()),'available_at':str(train.available_at.max()),'refit_max_abs_difference':delta})
    predictions=pd.read_csv(ROOT/f'ml/reports/turbine_{tid}_validation_predictions.csv.gz',parse_dates=['timestamp','forecast_origin'])
    metrics=json.loads((ROOT/f'ml/models/turbine_{tid}/metrics.json').read_text())
    differences=[]
    for fold in metrics['selection']+[metrics['holdout']]:
        subset=predictions.loc[predictions.window.eq(fold['label'])]
        joined=subset.merge(history[['timestamp','power_mean']],on='timestamp',suffixes=('','_raw'),validate='many_to_one')
        assert np.allclose(joined.power_mean,joined.power_mean_raw,atol=1e-12,rtol=0)
        for name, values in fold['models'].items():
            y=subset.power_mean.to_numpy(); p=subset[name].to_numpy(); err=y-p
            calc={'mae':float(np.abs(err).mean()),'rmse':float(np.sqrt((err**2).mean())),'r2':float(1-(err**2).sum()/((y-y.mean())**2).sum())}
            differences.extend(abs(calc[k]-values['overall'][k]) for k in calc)
    record['all_saved_metric_max_difference']=max(differences)
    _,freshpred=evaluate_window(history,'2025-12-01','2026-02-01',('power_curve','catboost_weather'),'holdout')
    saved=predictions.loc[predictions.window.eq('holdout')].reset_index(drop=True)
    record['holdout_reproduction']={name:float(np.max(np.abs(freshpred[name].to_numpy()-saved[name].to_numpy()))) for name in ('persistence','seasonal_persistence','power_curve','catboost_weather')}
    assert max(record['holdout_reproduction'].values())<1e-12
    record['holdout_metrics']={k:v['overall'] for k,v in metrics['holdout']['models'].items()}
    results[tid]=record
    print(json.dumps(record,ensure_ascii=False),flush=True)
weather=pd.read_csv(ROOT/'data/weather/february_backtest.csv')
wx=weather.pivot(index=['forecast_origin','timestamp'],columns='turbine_id',values=['wind_speed','temperature'])
assert (wx['wind_speed'][1]==wx['wind_speed'][2]).all() and (wx['temperature'][1]==wx['temperature'][2]).all()
from src.backtesting.csv_replay import replay_csv
import tempfile
with tempfile.TemporaryDirectory() as temp:
    rerun=replay_csv(ROOT/'data/weather/february_backtest.csv',Path(temp)/'replay')
    for h,frame in rerun.items():
        folder=ROOT/f'ml/reports/february_backtest/{h}h'
        old=pd.read_csv(folder/'predictions.csv')
        note=json.loads((folder/'run.json').read_text())
        assert hashlib.sha256((folder/'predictions.csv').read_bytes()).hexdigest()==note['predictions_sha256']
        assert hashlib.sha256((ROOT/'data/weather/february_backtest.csv').read_bytes()).hexdigest()==note['weather_csv_sha256']
        assert np.allclose(frame.predicted_power,old.predicted_power,atol=1e-12,rtol=0)
        print('BACKTEST',h,len(frame),'max_delta',float(np.max(np.abs(frame.predicted_power-old.predicted_power))),flush=True)
args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('AUDIT CHECKS PASSED',flush=True)
