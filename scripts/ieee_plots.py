import pandas as pd
import numpy as np
import ast
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib as mpl
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. تنظیمات گرافیکی IEEE
# ==========================================
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
mpl.rcParams['font.size'] = 11
mpl.rcParams['axes.titlesize'] = 13
mpl.rcParams['axes.labelsize'] = 12
mpl.rcParams['figure.dpi'] = 300

COLORS_BAR = {
    'Masked': '#2E8B57',       
    'Tolerable': '#66CDAA',    
    'Critical': '#F4A460',     
    'Fatal': '#CD5C5C'         
}

COLORS_RADAR = ['#808080', '#2E8B57', '#4682B4', '#CD5C5C']

TOLERANCE_MARGIN_FRE = 0.30
TOLERANCE_MARGIN_CV = 0.30

AREA_OVERHEADS = {
    'Baseline': 1.0,
    'Homeostasis': 1.44,
    'Light TMR': 2.13,
    'Ultimate TMR': 2.60
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "campaign_archive"

def get_taxonomy(row):
    fre = row['FRE']
    cv = row['CV']
    if row['flt_spikes'] == row['gld_spikes']: return 'Masked'
    if row['flt_spikes'] == 0 or row['flt_spikes'] > 400: return 'Fatal'
    if fre <= TOLERANCE_MARGIN_FRE and cv <= TOLERANCE_MARGIN_CV: return 'Tolerable'
    return 'Critical'

def process_data(model_dir):
    csv_dir = ARCHIVE_DIR / model_dir / "csv_data"
    if not csv_dir.exists(): return pd.DataFrame()
    
    files = list(csv_dir.glob("*_results.csv"))
    if not files: return pd.DataFrame()
    
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    
    fre_list, cv_list = [], []
    for _, row in df.iterrows():
        gld = row['gld_spikes']
        flt = row['flt_spikes']
        if gld == 0 or flt == 0:
            fre_list.append(float('inf'))
            cv_list.append(float('inf'))
            continue
            
        fre = abs(flt - gld) / gld
        try:
            f_times = ast.literal_eval(row['flt_times'])
            if len(f_times) > 2:
                isi = np.diff(f_times)
                cv = np.std(isi) / np.mean(isi) if np.mean(isi) > 0 else float('inf')
            else:
                cv = float('inf')
        except:
            cv = float('inf')
            
        fre_list.append(fre)
        cv_list.append(cv)
        
    df['FRE'] = fre_list
    df['CV'] = cv_list
    df['Taxonomy'] = df.apply(get_taxonomy, axis=1)
    return df

print("Loading and processing CSV datasets...")
models_data = {
    'Baseline': process_data("baseline_neuron2"),
    'Homeostasis': process_data("homeostatic_neuron2"),
    'Light TMR': process_data("light_tmr_neuron2"),
    'Ultimate TMR': process_data("ultimate_tmr_neuron2")
}

# ==========================================
# 2. ایجاد قاب تصویر دو پنلی
# ==========================================
fig = plt.figure(figsize=(15.5, 6.5)) # قاب کمی عریض‌تر شد

# ---- پنل چپ: Stacked Bar Chart ----
ax1 = fig.add_subplot(1, 2, 1)
categories = ['Masked', 'Tolerable', 'Critical', 'Fatal']
data_matrix = []
valid_names = []
dynamic_stats = {}

for name, df in models_data.items():
    if df.empty: continue
    valid_names.append(name)
    counts = df['Taxonomy'].value_counts()
    total = len(df)
    
    masked = counts.get('Masked', 0)
    tolerable = counts.get('Tolerable', 0)
    critical = counts.get('Critical', 0)
    fatal = counts.get('Fatal', 0)
    
    data_matrix.append([masked/total*100, tolerable/total*100, critical/total*100, fatal/total*100])
    
    survival_rate = (masked + tolerable) / total
    avf = (critical + fatal) / total
    area = AREA_OVERHEADS[name]
    sigma = area * avf
    
    dynamic_stats[name] = {
        'survival': survival_rate,
        'area_eff': 1.0 / area,
        'avf_resist': 1.0 - avf,
        'sigma': sigma
    }

matrix = np.array(data_matrix)
bottom = np.zeros(len(valid_names))

for i, cat in enumerate(categories):
    ax1.bar(valid_names, matrix[:, i], bottom=bottom, label=cat, color=COLORS_BAR[cat], edgecolor='white', width=0.55)
    bottom += matrix[:, i]
    
ax1.set_ylabel('Percentage of Injected Faults (%)', weight='bold')
ax1.set_title('(a) Biological Fault Taxonomy\n(FRE ≤ 30%, CV ≤ 0.30)', pad=15, weight='bold')

for x in range(len(valid_names)):
    y_offset = 0
    for i in range(len(categories)):
        val = matrix[x, i]
        if val > 6: 
            ax1.text(x, y_offset + val/2, f'{val:.1f}%', ha='center', va='center', color='black', fontsize=10)
        y_offset += val

ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, frameon=False)


# ---- پنل راست: Radar Chart ----
ax2 = fig.add_subplot(1, 2, 2, polar=True)

# 🌟 خاموش کردن لیبل‌های چپ و راست در تنظمات خودکار 🌟
labels_auto = ['Functional Survival', '', 'AVF Resistance', '']

min_sigma = min([s['sigma'] for s in dynamic_stats.values()])
num_vars = 4
angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]

for i, (name, stats) in enumerate(dynamic_stats.items()):
    color = COLORS_RADAR[i]
    norm_values = [
        stats['survival'],
        stats['area_eff'],
        stats['avf_resist'],
        min_sigma / stats['sigma']  
    ]
    norm_values += norm_values[:1] 
    
    ax2.plot(angles, norm_values, color=color, linewidth=2.5, linestyle='solid', marker='o', markersize=6, label=name)
    ax2.fill(angles, norm_values, color=color, alpha=0.15)

ax2.set_theta_offset(np.pi / 2)
ax2.set_theta_direction(-1)

# رسم لیبل‌های بالا و پایین
ax2.set_thetagrids(np.degrees(angles[:-1]), labels_auto, fontsize=12, weight='bold')
ax2.tick_params(pad=15) # فاصله استاندارد برای بالا و پایین

ax2.set_ylim(0, 1)
ax2.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
ax2.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], color="#777777", size=9)
ax2.grid(color='#BBBBBB', linestyle='--', linewidth=0.7)
ax2.spines['polar'].set_color('#444444')

# ==========================================
# 🌟 رسم دستی و حرفه‌ای لیبل‌های چپ و راست 🌟
# شعاع 1.25 باعث می‌شود متن دقیقاً بیرون دایره قرار بگیرد
# ==========================================
LABEL_RADIUS = 1.25

# لیبل سمت راست (Area Efficiency) -> در زاویه 90 درجه (pi/2)
ax2.text(np.pi / 2, LABEL_RADIUS, 'Area Efficiency', 
         rotation=-90, ha='center', va='center', fontsize=12, weight='bold')

# لیبل سمت چپ (Cross-Section) -> در زاویه 270 درجه (3*pi/2)
ax2.text(3 * np.pi / 2, LABEL_RADIUS, 'Cross-Section Eff ($\sigma$)', 
         rotation=90, ha='center', va='center', fontsize=12, weight='bold')

ax2.set_title('(b) SWaP-C vs. Reliability Trade-off (Radar)', pad=30, weight='bold')
ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)

# ==========================================
# 3. تنظیم فاصله‌ها و ذخیره تصویر
# ==========================================
plt.subplots_adjust(wspace=0.45) # فاصله زیاد بین دو پنل برای جلوگیری از تداخل
plt.savefig('ieee_results_summary.png', bbox_inches='tight', dpi=300)
print("✅ Output saved as 'ieee_results_summary.png' with PERFECT vertical side labels.")