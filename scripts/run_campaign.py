# scripts/run_campaign.py
import sys
import os
from pathlib import Path
import subprocess
import time
import shutil
import multiprocessing

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = PROJECT_ROOT / "code"
sys.path.append(str(CODE_DIR))

from utils import setup_logger
from target_extractor import TargetExtractorAgent
from instrumentor import InstrumentorAgent

def worker_process(model_name, split_total, split_idx):
    """اجرای شبیه‌سازی در Sandbox اختصاصی برای هر ترد"""
    # نام‌گذاری فایل‌ها: اگر 1 پارت باشد نام خود مدل، اگر بیشتر باشد part اضافه می‌شود
    part_str = f"_part{split_idx + 1}" if split_total > 1 else ""
    task_name = f"{model_name}{part_str}"
    
    sandbox_dir = PROJECT_ROOT / "sim" / "workspaces" / task_name
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir)
    sandbox_dir.mkdir(parents=True)
    
    shutil.copy2(PROJECT_ROOT / "sim" / "Makefile", sandbox_dir / "Makefile")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(CODE_DIR) + ":" + env.get("PYTHONPATH", "")
    env["TOP_MODULE"] = model_name
    env["PROJ_ROOT"] = str(PROJECT_ROOT)
    
    # متغیرهای برش کار برای هسته
    env["SPLIT_TOTAL"] = str(split_total)
    env["SPLIT_INDEX"] = str(split_idx)
    env["TASK_NAME"] = task_name 
    
    # 🌟 تنظیم مسیر دقیق ذخیره‌سازی مطابق اسکرین‌شات 🌟
    archive_dir = PROJECT_ROOT / "campaign_archive" / model_name / "csv_data"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    env["CSV_RESULTS_PATH"] = str(archive_dir / f"{task_name}_results.csv")
    env["PROGRESS_FILE"] = str(sandbox_dir / "progress.txt")
    
    # اجرای Icarus در محیط ایزوله
    subprocess.run(
        ["make"], 
        cwd=sandbox_dir, 
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

class ParallelCampaignMaster:
    def __init__(self):
        self.logger = setup_logger("BatchMaster")
        # 🌟 تخصیص ۱۱ ترد بر اساس توپولوژی جدید 🌟
        # فرمت: (نام مدل، تعداد کل تردها، شناسه ترد)
        self.tasks = [
            ("baseline_neuron2", 1, 0),                                # 1 Thread
            ("homeostatic_neuron2", 2, 0), ("homeostatic_neuron2", 2, 1), # 2 Threads
            ("light_tmr_neuron2", 4, 0), ("light_tmr_neuron2", 4, 1), 
            ("light_tmr_neuron2", 4, 2), ("light_tmr_neuron2", 4, 3),      # 4 Threads
            ("ultimate_tmr_neuron2", 4, 0), ("ultimate_tmr_neuron2", 4, 1), 
            ("ultimate_tmr_neuron2", 4, 2), ("ultimate_tmr_neuron2", 4, 3) # 4 Threads
        ]
        self.models = list(dict.fromkeys([t[0] for t in self.tasks])) # حذف تکراری‌ها برای فاز آماده‌سازی

    def prepare_netlists(self):
        self.logger.info("🛠️ Phase 1-3: Smart Netlist Preparation...")
        for model in self.models:
            target_file = PROJECT_ROOT / "netlists" / "instrumented" / f"targets_{model}.json"
            instrumented_file = PROJECT_ROOT / "netlists" / "instrumented" / f"{model}_instrumented.v"
            
            # جلوگیری از بازنویسی اگر از قبل آماده است
            if target_file.exists() and instrumented_file.exists():
                self.logger.info(f"⏭️ Skipping {model}: Manifest and Instrumented netlist exist.")
                continue
                
            self.logger.info(f"⚙️ Processing netlist for: {model}")
            os.environ["TOP_MODULE"] = model
            TargetExtractorAgent().execute()
            InstrumentorAgent().execute()
            
        self.logger.info("✅ All netlists are isolated and ready!")

    def print_dashboard(self, processes, start_time):
        while any(p.is_alive() for p in processes):
            sys.stdout.write('\033[H\033[J') 
            print("="*90)
            print(" 🚀 HYPER-THREADED SNN FAULT INJECTION DASHBOARD (11 CORES) 🚀")
            print("="*90)
            
            for model, stot, sidx in self.tasks:
                part_str = f"_part{sidx + 1}" if stot > 1 else ""
                task_name = f"{model}{part_str}"
                prog_file = PROJECT_ROOT / "sim" / "workspaces" / task_name / "progress.txt"
                
                if prog_file.exists():
                    try:
                        with open(prog_file, 'r') as f:
                            data = f.read().split('|')
                        if len(data) == 4:
                            pct, count, zone, fault = data
                            bar_len = 20
                            filled = int(float(pct) / 100 * bar_len)
                            bar = "█" * filled + "-" * (bar_len - filled)
                            # تنظیم چاپ منظم در ترمینال
                            print(f" ⚙️ {task_name[:30]:<30} | [{bar}] {pct:>5}% | {zone[:13]:<13} | {fault}")
                            continue
                    except:
                        pass
                print(f" ⚙️ {task_name[:30]:<30} | [--------------------]   0.0% | Starting...")
            
            elapsed = int(time.time() - start_time)
            eta_h, remainder = divmod(elapsed, 3600)
            eta_m, eta_s = divmod(remainder, 60)
            
            print("="*90)
            print(f" ⏱️ Total Elapsed Time: {eta_h:02d}h {eta_m:02d}m {eta_s:02d}s")
            time.sleep(1.0)

    def execute(self):
        master_start_time = time.time()
        self.logger.info("🔥 STARTING MULTI-CORE CAMPAIGN (11 WORKER PROCESSES) 🔥")
        
        self.prepare_netlists()
        
        self.logger.info("\n🌩️ Igniting 11 Parallel Simulation Workers...")
        time.sleep(2) 
        
        processes = []
        for t in self.tasks:
            p = multiprocessing.Process(target=worker_process, args=t)
            processes.append(p)
            p.start()
            
        try:
            self.print_dashboard(processes, master_start_time)
        except KeyboardInterrupt:
            print("\n\n⚠️ Keyboard Interrupt! Terminating all 11 workers safely...")
            for p in processes:
                p.terminate()
                p.join()
            print("💾 Checkpoint saved. You can resume later.")
            sys.exit(0)
            
        for p in processes:
            p.join()
            
        total_time = time.time() - master_start_time
        print("\n" + "="*90)
        print(f"✅ ALL 11 PARALLEL CAMPAIGNS COMPLETED SUCCESSFULLY in {total_time:.2f} seconds!")
        print("="*90)

if __name__ == "__main__":
    master = ParallelCampaignMaster()
    master.execute()