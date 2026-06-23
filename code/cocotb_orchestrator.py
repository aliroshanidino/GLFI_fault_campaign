# code/cocotb_orchestrator.py
import os
import csv
import time
import json
import math
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from pathlib import Path
from utils import setup_logger

TOP_MODULE = os.environ.get("TOP_MODULE", "baseline_neuron2")
TASK_NAME = os.environ.get("TASK_NAME", TOP_MODULE)
CSV_RESULTS_PATH = os.environ.get("CSV_RESULTS_PATH", "results.csv")
PROGRESS_FILE = os.environ.get("PROGRESS_FILE", "progress.txt")
PROJ_ROOT = Path(os.environ.get("PROJ_ROOT", "../../.."))

# متغیرهای تقسیم کار
SPLIT_TOTAL = int(os.environ.get("SPLIT_TOTAL", "1"))
SPLIT_INDEX = int(os.environ.get("SPLIT_INDEX", "0"))

logger = setup_logger(f"Orch_{TASK_NAME}")

TOTAL_CYCLES = 10000
INJECTION_DELAY_CYCLES = 2000

class BaselineManager:
    def __init__(self, dut):
        self.dut = dut
        self.golden_spikes = []
        if "baseline" in TOP_MODULE: self.i_syn_val = 650000
        elif "homeostatic" in TOP_MODULE: self.i_syn_val = 820000
        elif "light_tmr" in TOP_MODULE: self.i_syn_val = 820000
        else: self.i_syn_val = 850000

    async def reset_and_warmup(self):
        self.dut.Reset.value = 1
        self.dut.Enable.value = 0
        self.dut.I_syn.value = 0
        self.dut.fi_enable.value = 0
        self.dut.fi_target_id.value = 0
        self.dut.fi_value.value = 0
        for _ in range(20): await RisingEdge(self.dut.Clk)
        self.dut.Reset.value = 0
        self.dut.Enable.value = 1
        self.dut.I_syn.value = self.i_syn_val 
        for _ in range(10): await RisingEdge(self.dut.Clk)

    async def run_determinism_check(self):
        logger.info(f"Running Determinism Check for {TASK_NAME}...")
        runs_spikes = []
        for run_idx in range(3):
            await self.reset_and_warmup()
            spikes, prev_s = [], 0
            for cyc in range(TOTAL_CYCLES):
                await RisingEdge(self.dut.Clk)
                cur_s = int(self.dut.Spike.value) if self.dut.Spike.value.is_resolvable else 0
                if prev_s == 0 and cur_s == 1: spikes.append(cyc)
                prev_s = cur_s
            runs_spikes.append(spikes)
            
        if runs_spikes[0] != runs_spikes[1] or runs_spikes[1] != runs_spikes[2]:
            logger.error("❌ Determinism Check FAILED!")
        self.golden_spikes = runs_spikes[0]

class CampaignOrchestrator:
    def __init__(self, dut, baseline_mgr):
        self.dut = dut
        self.base_mgr = baseline_mgr
        self.csv_path = Path(CSV_RESULTS_PATH)
        self.completed_tasks = set()
        self._init_checkpointing()

    def _init_checkpointing(self):
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        headers = ["target_id", "net_name", "domain", "zone", "fault_val", "gld_spikes", "flt_spikes", "gld_times", "flt_times"]
        
        if self.csv_path.exists():
            with open(self.csv_path, 'r') as f:
                reader = csv.reader(f)
                next(reader, None) # پرش از هدر
                for row in reader:
                    if len(row) > 4:
                        # فرمت امضا: آدرس_نوع‌خطا (مثلاً 1599_SA1)
                        signature = f"{row[0]}_{row[4]}"
                        self.completed_tasks.add(signature)
        else:
            with open(self.csv_path, 'w', newline='') as f:
                csv.writer(f).writerow(headers)

    def log_result(self, row_data):
        with open(self.csv_path, 'a', newline='') as f:
            csv.writer(f).writerow(row_data)

    def write_progress(self, current, total, zone, fault_str):
        pct = (current / total) * 100 if total > 0 else 0
        try:
            with open(PROGRESS_FILE, 'w') as f:
                f.write(f"{pct:.1f}|{current}|{zone}|{fault_str}")
        except: pass

    async def run_campaign(self):
        manifest_path = PROJ_ROOT / "netlists" / "instrumented" / f"targets_{TOP_MODULE}.json"
        with open(manifest_path, 'r') as f:
            all_targets = json.load(f)
            
        # 🌟 ریاضیات دقیق برای جداسازی سهمیه‌ی این هسته 🌟
        chunk_size = math.ceil(len(all_targets) / SPLIT_TOTAL)
        start_idx = SPLIT_INDEX * chunk_size
        end_idx = min(start_idx + chunk_size, len(all_targets))
        my_targets = all_targets[start_idx:end_idx]
        
        # 🌟 فیلتر کردن دقیق خطاهای انجام‌شده از روی CSV 🌟
        tasks_to_run = []
        for target in my_targets:
            t_id = target["id"]
            for f_val in [0, 1]:
                signature = f"{t_id}_SA{f_val}"
                if signature not in self.completed_tasks:
                    tasks_to_run.append((target, f_val))
                    
        total_chunk_runs = len(my_targets) * 2
        already_done = total_chunk_runs - len(tasks_to_run)
        
        self.write_progress(already_done, total_chunk_runs, "INIT", "Resuming...")

        completed_this_session = 0
        
        for target, f_val in tasks_to_run:
            t_id = target["id"]
            t_name = target.get("out_net", f"node_{t_id}")
            t_zone = target.get("zone", "UNKNOWN")
            t_domain = "SEQ" if t_zone == "STATE_MEMORY" else "COMB"
            
            await self.base_mgr.reset_and_warmup()
            flt_times, prev_s = [], 0
            
            for cyc in range(TOTAL_CYCLES):
                if cyc == INJECTION_DELAY_CYCLES:
                    self.dut.fi_enable.value, self.dut.fi_target_id.value, self.dut.fi_value.value = 1, t_id, f_val

                await RisingEdge(self.dut.Clk)
                cur_s = int(self.dut.Spike.value) if self.dut.Spike.value.is_resolvable else 0
                if prev_s == 0 and cur_s == 1: flt_times.append(cyc)
                prev_s = cur_s
                
            self.dut.fi_enable.value = 0
            
            self.log_result([
                t_id, t_name, t_domain, t_zone, f"SA{f_val}",
                len(self.base_mgr.golden_spikes), len(flt_times),
                str(self.base_mgr.golden_spikes), str(flt_times)
            ])
            
            completed_this_session += 1
            current_progress = already_done + completed_this_session
            
            # آپدیت داشبورد هر 5 ران
            if completed_this_session % 5 == 0 or current_progress == total_chunk_runs:
                self.write_progress(current_progress, total_chunk_runs, t_zone, f"SA{f_val} @ {t_name}")
                
        self.write_progress(total_chunk_runs, total_chunk_runs, "DONE", "Completed")

@cocotb.test()
async def dynamic_shadow_hook_test(dut):
    cocotb.start_soon(Clock(dut.Clk, 10, unit="ns").start())
    base_mgr = BaselineManager(dut)
    await base_mgr.run_determinism_check()
    orchestrator = CampaignOrchestrator(dut, base_mgr)
    await orchestrator.run_campaign()