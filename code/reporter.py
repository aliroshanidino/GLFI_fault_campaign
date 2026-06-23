# reporter.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import ast
import warnings
from utils import PathManager, setup_logger
warnings.filterwarnings("ignore")

class UltimateReporterAgent:
    """Layer C: Generates High-Density, Publication-Ready 4-Panel Artifacts for TCAS-I."""
    def __init__(self):
        self.logger = setup_logger("UltimateReporter")
        self.csv_path = PathManager.LATEST_RUN_DIR / "classified_results.csv"
        self.report_dir = PathManager.LATEST_RUN_DIR.parent.parent / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        plt.style.use('seaborn-v0_8-whitegrid')
        self.font_params = {'font.family': 'serif', 'font.size': 12, 'axes.labelsize': 13}
        plt.rcParams.update(self.font_params)

    def extract_features(self, times_list):
        if len(times_list) < 3: 
            return len(times_list), 0, 0
        isi = [times_list[i] - times_list[i-1] for i in range(1, len(times_list))]
        mean_isi = np.mean(isi)
        std_isi = np.std(isi)
        cv_isi = std_isi / mean_isi if mean_isi > 0 else 0
        return len(times_list), mean_isi, cv_isi

    def execute(self):
        self.logger.info("Engaging 4-Panel Dashboard Generation...")
        if not self.csv_path.exists():
            self.logger.error("Classified CSV not found!")
            return
            
        df = pd.read_csv(self.csv_path)
        
        gld_times = ast.literal_eval(df['gld_times'].iloc[0])
        self.gld_f, self.gld_isi, self.gld_cv = self.extract_features(gld_times)
        
        features = []
        for _, row in df.iterrows():
            flt_times = ast.literal_eval(row['flt_times'])
            f_count, f_isi, f_cv = self.extract_features(flt_times)
            features.append({
                'SpikeCount': f_count,
                'MeanISI': f_isi,
                'ISI_CV': f_cv,
                'FaultVal': row['fault_val'],
                'FaultClass': row['Fault_Class'],
                'Zone': row['zone']  # 🌟 استفاده از منطقه معماری (Zone) 🌟
            })
        self.df_feat = pd.DataFrame(features)

        self._plot_4panel_dashboard(df)
        self.logger.info(f"Visual artifacts compiled in: {self.report_dir}")

    def _plot_4panel_dashboard(self, df):
        fig, axes = plt.subplots(2, 2, figsize=(22, 16))
        ax1, ax2, ax3, ax4 = axes.flatten()
        
        # ==========================================
        # Panel A: Fault Taxonomy Distribution
        # ==========================================
        class_counts = df['Fault_Class'].value_counts()
        sns.barplot(x=class_counts.values, y=class_counts.index, ax=ax1, palette='viridis')
        ax1.set_title("(A) Hybrid Fault Taxonomy Distribution", fontweight='bold', fontsize=16)
        ax1.set_xlabel("Fault Count", fontweight='bold')
        
        total = len(df)
        for i, v in enumerate(class_counts.values):
            ax1.text(v + (total*0.01), i, f"{(v/total)*100:.1f}%", va='center', fontweight='bold', fontsize=12)

        # ==========================================
        # Panel B: Architectural Zone Sensitivity
        # ==========================================
        # چطور هر منطقه (Datapath, Control) در برابر خطا واکنش نشان داده است؟
        zone_class = df.groupby(['zone', 'Fault_Class']).size().unstack(fill_value=0)
        zone_pct = zone_class.div(zone_class.sum(axis=1), axis=0) * 100
        zone_pct.plot(kind='bar', stacked=True, ax=ax2, colormap='Spectral')
        
        ax2.set_title("(B) Architectural Zone Sensitivity", fontweight='bold', fontsize=16)
        ax2.set_xlabel("Hardware Zone", fontweight='bold')
        ax2.set_ylabel("Percentage (%)", fontweight='bold')
        ax2.legend(title="Biological Class", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
        ax2.set_xticklabels(ax2.get_xticklabels(), rotation=0, fontweight='bold')

        # ==========================================
        # Panel C: Hardware Reliability Factor (Fault Coverage)
        # ==========================================
        # دسته بندی ایمن در برابر کشنده
        safe_classes = ['Masked (Perfect)', 'Tolerated (Dynamic Recovery)']
        self.df_feat['Reliability'] = self.df_feat['FaultClass'].apply(lambda x: 'Safe/Recovered' if x in safe_classes else 'System Failure')
        
        rel_data = self.df_feat.groupby(['Zone', 'Reliability']).size().unstack(fill_value=0)
        rel_pct = rel_data.div(rel_data.sum(axis=1), axis=0) * 100
        rel_pct.plot(kind='bar', stacked=True, ax=ax3, color=['#d62728', '#2ca02c'], edgecolor='black')
        
        ax3.set_title("(C) Reliability Factor & Fault Coverage", fontweight='bold', fontsize=16)
        ax3.set_xlabel("Hardware Zone", fontweight='bold')
        ax3.set_ylabel("Fault Coverage (%)", fontweight='bold')
        ax3.legend(title="Status", bbox_to_anchor=(1.05, 1), loc='upper left')
        ax3.set_xticklabels(ax3.get_xticklabels(), rotation=0, fontweight='bold')
        
        for p in ax3.patches:
            w, h = p.get_width(), p.get_height()
            x, y = p.get_xy()
            if h > 5:
                ax3.text(x+w/2, y+h/2, f"{h:.1f}%", ha='center', va='center', color='white', fontweight='bold', fontsize=12)

        # ==========================================
        # Panel D: Dynamic Rhythm Scatter Map
        # ==========================================
        # نمایش پراکندگی FRE (محور X) در برابر ISI CV (محور Y)
        valid_spikes = self.df_feat[self.df_feat['SpikeCount'] > 0]
        
        sns.scatterplot(data=valid_spikes, x='SpikeCount', y='ISI_CV', hue='FaultVal', 
                        style='FaultVal', palette=['#1f77b4', '#d62728'], s=80, alpha=0.7, ax=ax4)
        
        # ستاره طلایی (Golden Reference)
        ax4.scatter([self.gld_f], [self.gld_cv], color='#32cd32', marker='*', s=400, edgecolors='black', linewidth=1.5, label='Fault-Free (Golden)', zorder=10)
        
        # رسم مرزهای تحمل هموستاتیک (Tolerated Zone)
        ax4.axvspan(15, 85, color='green', alpha=0.1, label='Tolerated FRE Zone')
        ax4.axhline(y=0.5, color='red', linestyle='--', linewidth=2, label='Max Allowable CV (0.5)')
        
        ax4.set_title("(D) Firing Rhythm Topology (Spikes vs CV)", fontweight='bold', fontsize=16)
        ax4.set_xlabel("Total Spikes (10k Cycles)", fontweight='bold')
        ax4.set_ylabel("Rhythm Disruption (ISI CV)", fontweight='bold')
        ax4.legend(loc='upper right', fontsize='small')

        plt.tight_layout()
        plt.savefig(self.report_dir / 'fig_final_4panel_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    agent = UltimateReporterAgent()
    agent.execute()