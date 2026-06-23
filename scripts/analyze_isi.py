import pandas as pd
import numpy as np
import ast
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# تنظیمات آستانه بر اساس استانداردهای ژورنال
TOLERANCE_MARGIN_FRE = 0.25  # اگر اختلاف نرخ شلیک کمتر از 25% باشد، قابل تحمل است
TOLERANCE_MARGIN_CV = 0.50   # اگر CV زیر 0.5 باشد، ریتم هنوز منظم است

# پیدا کردن هوشمند مسیر پوشه campaign_archive
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "campaign_archive"

def calculate_metrics(gld_times_str, flt_times_str, gld_spikes, flt_spikes):
    """محاسبه پارامترهای فیزیولوژیک از روی رشته‌های CSV"""
    if flt_spikes == 0 or gld_spikes == 0:
        return float('inf'), float('inf') 
        
    try:
        g_times = ast.literal_eval(gld_times_str)
        f_times = ast.literal_eval(flt_times_str)
    except:
        return float('inf'), float('inf')

    # 1. محاسبه خطای نرخ شلیک (FRE)
    fre = abs(flt_spikes - gld_spikes) / gld_spikes

    # 2. محاسبه فواصل بین ضربه‌ها (ISI) و ضریب تغییرات (CV)
    if len(f_times) > 2:
        isi_arr = np.diff(f_times)
        if np.mean(isi_arr) > 0:
            cv = np.std(isi_arr) / np.mean(isi_arr)
        else:
            cv = float('inf')
    else:
        cv = float('inf') 
        
    return fre, cv

def biological_taxonomy(row):
    """طبقه‌بندی دقیق بر اساس گزارش Deep Research"""
    if row['gld_spikes'] == row['flt_spikes']:
        return 'Masked (Perfect)'
        
    if row['flt_spikes'] == 0 or row['flt_spikes'] > 400:
        return 'Fatal (Silent/Saturated)'
        
    fre, cv = calculate_metrics(row['gld_times'], row['flt_times'], row['gld_spikes'], row['flt_spikes'])
    
    if fre <= TOLERANCE_MARGIN_FRE and cv <= TOLERANCE_MARGIN_CV:
        return 'Benign/Tolerable (Graceful Degradation)'
    else:
        return 'Critical (Rhythm Corrupted)'

def load_and_merge_csvs(model_name):
    """پیدا کردن و ترکیب تمام پارت‌های CSV یک مدل"""
    csv_dir = ARCHIVE_DIR / model_name / "csv_data"
    if not csv_dir.exists():
        print(f"⚠️ پوشه {csv_dir} پیدا نشد!")
        return None
        
    csv_files = list(csv_dir.glob("*_results.csv"))
    if not csv_files:
        print(f"⚠️ هیچ فایل CSV در {csv_dir} یافت نشد!")
        return None
        
    df_list = [pd.read_csv(f) for f in csv_files]
    return pd.concat(df_list, ignore_index=True)

def print_stats(name, df):
    if df is None or df.empty:
        return
        
    total = len(df)
    masked = len(df[df['class'] == 'Masked (Perfect)'])
    benign = len(df[df['class'] == 'Benign/Tolerable (Graceful Degradation)'])
    survival_rate = ((masked + benign) / total) * 100
    
    print(f"\n{'='*50}")
    print(f" 📊 {name} (Total Faults: {total})")
    print(f"{'='*50}")
    print(df['class'].value_counts().to_string())
    print("-" * 50)
    print(f"👉 Functional Survival Rate: {survival_rate:.2f}%\n")

# ==========================================
# اجرای تحلیل
# ==========================================
print("\n⏳ Analyzing SNN Physiological Metrics (FRE & ISI-CV)...")

models_to_analyze = {
    "Baseline SNN": "baseline_neuron2",
    "Adaptive Homeostasis SNN": "homeostatic_neuron2",
    "Light TMR SNN": "light_tmr_neuron2",
    "Ultimate TMR SNN": "ultimate_tmr_neuron2"
}

for display_name, folder_name in models_to_analyze.items():
    df = load_and_merge_csvs(folder_name)
    if df is not None:
        df['class'] = df.apply(biological_taxonomy, axis=1)
        print_stats(display_name, df)