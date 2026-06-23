# classifier.py
import csv
import ast
import math
import numpy as np
from utils import PathManager, setup_logger

class BioClassifierAgent:
    """
    Layer C: Hybrid Firing-Rate & Rhythm Classifier
    Evaluates Adaptive Homeostasis using expanded biological bounds (Surfing concept).
    """
    
    def __init__(self):
        self.logger = setup_logger("BioClassifier")
        self.raw_csv = PathManager.RAW_RESULTS_CSV
        self.classified_csv = PathManager.LATEST_RUN_DIR / "classified_results.csv"
        
        self.BOUND_DEAD = 0
        self.BOUND_UNDERACTIVE_MAX = 14
        self.BOUND_OPTIMAL_MIN = 15
        self.BOUND_OPTIMAL_MAX = 85
        self.BOUND_SURFING_MAX = 400  
        
        self.TIMING_TOLERANCE = 3
        self.MAX_ISI_CV = 0.5

    def compute_isi_stats(self, spike_times):
        if len(spike_times) < 3:
            return 0.0, 0.0, 0.0
            
        isi_list = [spike_times[i] - spike_times[i-1] for i in range(1, len(spike_times))]
        mean_isi = sum(isi_list) / len(isi_list)
        variance = sum((x - mean_isi) ** 2 for x in isi_list) / len(isi_list)
        std_isi = math.sqrt(variance)
        cv_isi = std_isi / mean_isi if mean_isi > 0 else 0.0
        
        return mean_isi, std_isi, cv_isi

    def is_perfect_match(self, gld_times, flt_times):
        if len(gld_times) != len(flt_times): return False
        return all(abs(g - f) <= self.TIMING_TOLERANCE for g, f in zip(gld_times, flt_times))

    def classify_fault(self, gld_times, flt_times):
        num_spikes = len(flt_times)
        
        # 1. Masked (TMR filtered it completely)
        if self.is_perfect_match(gld_times, flt_times):
            return "Masked (Perfect)"
            
        # 2. Dead / Silent (Failed to recover from SA0)
        if num_spikes == self.BOUND_DEAD:
            return "Silent (Fatal)"
            
        # 3. Damped Underactivity (Homeostasis fought SA0, kept it barely alive)
        if num_spikes <= self.BOUND_UNDERACTIVE_MAX:
            return "Damped Underactivity"
            
        # 4. Optimal Recovery (The Sweet Spot)
        if num_spikes <= self.BOUND_OPTIMAL_MAX:
            _, _, cv_isi = self.compute_isi_stats(flt_times)
            if cv_isi <= self.MAX_ISI_CV:
                return "Optimal Recovery"
            else:
                return "Rhythm Corrupted"
                
        # 5. Damped Overactivity / Surfing (Homeostasis fought SA1, prevented full saturation)
        if num_spikes <= self.BOUND_SURFING_MAX:
            return "Damped Overactivity (Surfing)"
            
        # 6. Saturated (Uncontrollable fatal excitation)
        return "Saturated (Fatal)"

    def execute(self):
        self.logger.info("Starting Adaptive Homeostasis Classification (Surfing Logic)...")
        if not self.raw_csv.exists():
            self.logger.error("Raw CSV not found! Run the Cocotb simulation first.")
            return

        stats = {
            "Masked (Perfect)": 0, 
            "Silent (Fatal)": 0, 
            "Damped Underactivity": 0,
            "Optimal Recovery": 0, 
            "Rhythm Corrupted": 0,
            "Damped Overactivity (Surfing)": 0,
            "Saturated (Fatal)": 0
        }
        total_faults = 0

        self.classified_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(self.raw_csv, 'r') as fin, open(self.classified_csv, 'w', newline='') as fout:
            reader = csv.DictReader(fin)
            fieldnames = reader.fieldnames + ["Fault_Class"] if "Fault_Class" not in reader.fieldnames else reader.fieldnames
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                gld_times = ast.literal_eval(row["gld_times"])
                flt_times = ast.literal_eval(row["flt_times"])
                
                f_class = self.classify_fault(gld_times, flt_times)
                row["Fault_Class"] = f_class
                writer.writerow(row)
                stats[f_class] += 1
                total_faults += 1

        self.logger.info("================================================================")
        self.logger.info("📊 FINAL CLASSIFICATION REPORT (Homeostatic Efficacy)")
        self.logger.info("================================================================")
        self.logger.info(f"Total Faults Analyzed: {total_faults}")
        for k, v in stats.items():
            pct = (v / total_faults) * 100 if total_faults > 0 else 0
            self.logger.info(f"  ➤ {k:<32}: {v:<5} ({pct:.1f}%)")
        self.logger.info("================================================================")

if __name__ == "__main__":
    agent = BioClassifierAgent()
    agent.execute()
