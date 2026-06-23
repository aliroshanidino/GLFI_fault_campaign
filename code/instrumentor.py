# code/instrumentor.py
import re
import json
import os
from pathlib import Path
from utils import PathManager, setup_logger, load_config

# 🔴 تعریف ریشه پروژه به صورت ایمن 🔴
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class InstrumentorAgent:
    """Weaves saboteurs purely based on Exact String Block Replacement."""
    
    def __init__(self):
        self.logger = setup_logger("Instrumentor")
        
        # خواندن نام ماژول از متغیر محیطی
        env_module = os.environ.get("TOP_MODULE")
        if env_module:
            self.top_module = env_module
        else:
            self.config = load_config()
            self.top_module = self.config['project']['top_module']
            
        self.raw_netlist = PathManager.NETLIST_DIR / f"{self.top_module}_generic.v"
        self.instrumented_netlist = PathManager.INSTRUMENTED_DIR / f"{self.top_module}_instrumented.v"
        
        # 🔴 فیکس شد: استفاده از متغیر PROJECT_ROOT ایزوله 🔴
        self.targets_manifest = PROJECT_ROOT / "netlists" / "instrumented" / f"targets_{self.top_module}.json"

    def execute(self):
        self.logger.info(f"Starting Bulletproof Verilog Netlist Instrumentation for {self.top_module}...")
        
        with open(self.targets_manifest, 'r') as f:
            targets = json.load(f)
            
        with open(self.raw_netlist, 'r') as f:
            content = f.read()

        module_pattern = re.compile(rf'\bmodule\s+{self.top_module}\s*\((.*?)\)\s*;', re.DOTALL)
        match = module_pattern.search(content)
        if not match:
            self.logger.error("Module declaration not found!")
            return
            
        original_ports = match.group(1)
        new_ports = original_ports + ", fi_enable, fi_target_id, fi_value"
        content = content.replace(f"({original_ports})", f"({new_ports})", 1)

        fault_bus_declarations = "\n  // --- FAULT INJECTION BUS ---\n"
        fault_bus_declarations += "  input fi_enable;\n"
        fault_bus_declarations += "  input [31:0] fi_target_id;\n"
        fault_bus_declarations += "  input fi_value;\n"
        fault_bus_declarations += "  // ---------------------------\n"
        
        content = module_pattern.sub(rf"module {self.top_module}({new_ports});\n{fault_bus_declarations}", content, count=1)

        saboteur_logic = "\n  // === SHADOW-HOOK SABOTEURS ===\n"
        successful_weaves = 0

        for target in targets:
            old_block = target["exact_block"]
            out_pin = target["out_pin"]
            out_net = target["out_net"]
            t_id = target["id"]

            if old_block not in content:
                continue

            safe_net = re.sub(r'[^a-zA-Z0-9_]', '_', out_net)
            hook_net = f"hook_{safe_net}_{t_id}"

            # جایگزینی فقط و فقط روی همان پینی که اکستراکتور پیدا کرده بود انجام می‌شود
            pin_pattern = re.compile(r'(\.\s*' + out_pin + r'\s*\(\s*)' + re.escape(out_net) + r'(\s*\))')
            new_block = pin_pattern.sub(rf'\g<1>{hook_net}\g<2>', old_block)

            if new_block != old_block:
                content = content.replace(old_block, new_block, 1)
                
                saboteur_logic += f"  wire {hook_net};\n"
                saboteur_logic += f"  assign {out_net} = (fi_enable && fi_target_id == 32'd{t_id}) ? fi_value : {hook_net};\n"
                
                successful_weaves += 1

        saboteur_logic += "  // =============================\n"
        content = re.sub(r'\bendmodule\b', f"{saboteur_logic}\nendmodule", content)

        self.instrumented_netlist.parent.mkdir(parents=True, exist_ok=True)
        with open(self.instrumented_netlist, 'w') as f:
            f.write(content)

        self.logger.info(f"Instrumentation complete! Weaved {successful_weaves}/{len(targets)} explicit hooks.")
        
        if successful_weaves == 0:
            raise RuntimeError("CRITICAL: Failed to weave ANY hooks! Netlist format mismatch.")

if __name__ == "__main__":
    agent = InstrumentorAgent()
    agent.execute()