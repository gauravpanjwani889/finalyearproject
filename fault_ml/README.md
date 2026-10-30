# fault_ml — Smart Grid Fault Detection & Classification (ML)

Simulink model (`main_model.slx`) ke data se **12 classes** (NORMAL + AG BG CG AB BC CA ABG BCG CAG ABC ABCG)
classify karta hai, aur fault resistance (Rf) estimate karta hai. Relay se independent hai: ML apna onset
detector khud chalata hai.

> **"Prediction" ka matlab:** model me fault schedule se inject hota hai, fault se *pehle* koi precursor signal nahi
> hota, isliye "fault hone se pehle predict" is simulation se possible nahi. Ye **detection + classification +
> severity estimation** hai. Report/viva me yahi likhna.

## Folder kahan rakhna hai
`Smart_Grid_Automation/fault_ml/` (matlab/ aur backend/ ke saath). Default model path `../matlab/main_model.slx` hai.

## Steps
```powershell
pip install -r requirements.txt            # + matlabengine==25.1 (MATLAB wali machine)
cd fault_ml

python generate_dataset.py --dry-run       # 1. plan dekho (MATLAB nahi chalta)
python generate_dataset.py --check         # 2. PEHLE YE: 2 AG run chalata hai aur Shreeya ke out.mat se compare karta hai
python generate_dataset.py                 # 3. 40 conditions x 12 classes = 480 runs (resumable)
python train.py --data data/simulink       # 4. train + grouped-CV report + confusion matrix -> models/
python -m pytest tests -q                  # 5. tests
```
Parallel chalana ho to alag terminals me `--shard 0/3`, `--shard 1/3`, `--shard 2/3`.
Run roke to dobara chalao — jo files ban chuki hain wo skip hoti hain. Failed runs `data/simulink/failures.log` me jaate hain.

## Backend/website me jodna
```python
# backend/main.py
from fault_ml.api_router import router as ml_router
app.include_router(ml_router)               # GET /api/ml/status, POST /api/ml/predict

# ya sim_runner.py me, ScopeData milte hi (full 20 kHz data, decimation se PEHLE):
from fault_ml.ml_predict import FaultPredictor
pred = FaultPredictor().predict_run(time, signals)   # signals: (N, 9)
# -> fault_type, confidence, top3, estimated_fault_resistance_ohm, onset_time_s, relay_tripped, trained_on
```
Frontend me "ML Diagnostics" card: predicted class + confidence + relay ka trip status side-by-side.
Agar `trained_on == "synthetic"` ho to response me `warning` aata hai — usko UI me dikhana, warna nakli result asli lagega.

## Kaise kaam karta hai
1. **Onset detector** (`ml_signals.detect_onset`): one-cycle difference `|i[k] - i[k-400]|`. Healthy periodic signal (PWM ripple dahil) me ~0, fault pe jump. Asli AG run pe 0.2003 s pe pakda (fault 0.2000 s).
2. **Features** (`ml_features.py`, 63): fault se pehle 1 cycle aur baad ke 2 cycles ke RMS ratios, 50 Hz phasors, current sequence components (I0/I1/I2), delta-phasors, voltage sag pattern, DC offset, harmonic content. Trip signal feature **nahi** hai (leak se bachne ke liye).
3. **Models**: RandomForest / ExtraTrees / HistGradientBoosting, best macro-F1 wala save hota hai. Evaluation **GroupKFold by operating condition** — test me wo conditions jo training me nahi thi.

## Asli out.mat se mili cheezein (AG run, Ia peak 593.83 A)
- Trip hone (0.2005 s) ke **baad bhi fault current 0.4 s tak bana rehta hai** (Ia RMS ~325 A; fault block 0.4 s pe khulne pe hi girta hai). Yaani is measurement point pe breaker fault clear karta nahi dikhta. Docs me "isolates faulted feeder" likha hai — Shreeya se confirm karo.
- Healthy `Imag` ≈ **9.6–10 A**, relay threshold **10 A**. Docs me steady Imag ≈ 1.5 A likha hai. Margin bahut patla hai → load badhne pe false trip ka risk.
- Va/Vb/Vc **line-to-line** (Vab, Vbc, Vca) hain (AG me Va, Vc sag, Vb nahi). Healthy ≈ 350 V RMS, docs ke 215/240 V se alag. Voltage se zero-sequence nahi milta; isliye I0 currents se liya hai.
- `PARAMETER_MAPPING.md` me **BCG** row galat hai (A=on dikhaya). Is project ka code letters se mapping banata hai. Shreeya ke backend me bhi check karo.
- Fault block ke switching-time parameter ka naam docs me `SwitchTimes` aur `TransitionTimes` dono likha hai; generator MATLAB se khud dhoondh leta hai.

## Limits (ईमानदारी se)
- `generate_dataset.py` MATLAB ke bina yahan test nahi hua. `--dry-run`, fault-flag mapping, aur baaki saara pipeline (features → train → predict → API) test hua hai: asli AG run pe features/onset/API tests + synthetic data pe end-to-end training. **Pehle `--check` zaroor chalao.**
- `make_smoke_data.py` nakli data banata hai sirf pipeline test ke liye. Uske accuracy numbers (≈93%) ka koi matlab nahi.
- Mushkil cases jo asli data me dikhenge: ABC vs ABCG, AB vs ABG (sirf ground current ka farak), aur Rf > ~10 Ω (fault current load current jitna). Report me confusion matrix ke saath ye discuss karo.
- Ranges `ml_config.py` me hain. Line R/L, Vf, Pm ranges chhote rakhe hain; agar koi run diverge kare to `failures.log` dekho.
- Load (500 MW) / generator (10 MVA) mismatch ko maine vary nahi kiya.

## Files
| File | Kaam |
|---|---|
| `generate_dataset.py` | Simulink se labelled runs (`--check`, `--dry-run`, `--shard`) |
| `ml_config.py` | classes, block paths, sampling ranges |
| `ml_signals.py` | uniform resampling, onset detector |
| `ml_features.py` | feature extraction |
| `train.py` | train + grouped CV + report |
| `ml_predict.py` / `api_router.py` | inference / FastAPI |
| `ml_matio.py` | Simulink `out.mat` (v7.3) → numpy |
| `make_smoke_data.py` | nakli data, sirf test |
| `reference/AG_reference_run.npz` | Shreeya ke out.mat ka AG run |
