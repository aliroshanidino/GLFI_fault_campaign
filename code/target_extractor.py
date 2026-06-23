# code/target_extractor.py
import json
import re
import os
from pathlib import Path
from utils import PathManager, setup_logger, load_config

# 🔴 تعریف ریشه پروژه به صورت ایمن (جایگزین PathManager.PROJECT_ROOT) 🔴
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TargetExtractorAgent:
    """Reads Verilog directly, finds Exact String Blocks, and applies Heuristic Zoning."""
    
    def __init__(self):
        self.logger = setup_logger("TargetExtractor")
        
        # خواندن نام ماژول از متغیر محیطی (تزریق شده توسط داشبورد)
        env_module = os.environ.get("TOP_MODULE")
        if env_module:
            self.top_module = env_module
        else:
            self.config = load_config()
            self.top_module = self.config['project']['top_module']
            
        self.raw_netlist = PathManager.NETLIST_DIR / f"{self.top_module}_generic.v"
        
        # 🔴 فیکس شد: استفاده از متغیر PROJECT_ROOT ایزوله 🔴
        self.targets_file = PROJECT_ROOT / "netlists" / "instrumented" / f"targets_{self.top_module}.json"

    def get_zone(self, cell_type, out_net, inst_name):
        """Heuristic biological zoning based on net naming conventions."""
        if "dff" in cell_type.lower():
            return "STATE_MEMORY"
            
        combined_name = (out_net + "_" + inst_name).lower()
        
        if any(k in combined_name for k in ['theta', 'beta', 'f_', 'vmax', 'vmin', 'umax', 'umin', 'fb', 'spk', 'voted']):
            return "CONTROL_PLANE"
        if any(k in combined_name for k in ['v_', 'u_', 'pwl', 'sum', 'diff', 'dv', 'du', 'term']):
            return "DATAPATH"
            
        return "COMB_CLOUD"

    def execute(self):
        self.logger.info(f"Extracting targets DIRECTLY from Verilog for: {self.top_module}")
        
        if not self.raw_netlist.exists():
            self.logger.error(f"Verilog netlist not found at {self.raw_netlist}")
            return
            
        with open(self.raw_netlist, 'r') as f:
            content = f.read()

        # رگکس اصلاح‌شده: کاراکتر \ را که Yosys اضافه می‌کند با \\? شناسایی می‌کند
        pattern = re.compile(r'^[ \t]*(\\?\$_[A-Za-z0-9_]+_)\s+([^ \t\n\(]+).*?\((.*?)\);', re.MULTILINE | re.DOTALL)
        matches = pattern.finditer(content)

        targets = []
        target_id = 0
        zone_stats = {"STATE_MEMORY": 0, "CONTROL_PLANE": 0, "DATAPATH": 0, "COMB_CLOUD": 0}

        for match in matches:
            exact_block = match.group(0)     
            cell_type = match.group(1)       
            inst_name = match.group(2).strip() 
            ports_block = match.group(3)

            # استخراج پین Y یا Q
            out_match = re.search(r'\.\s*([YQ])\s*\(\s*([^)]+?)\s*\)', ports_block)
            if not out_match:
                continue

            out_pin = out_match.group(1)
            out_net = out_match.group(2).strip()

            zone = self.get_zone(cell_type, out_net, inst_name)

            targets.append({
                "id": target_id,
                "cell_type": cell_type,
                "inst_name": inst_name,
                "out_pin": out_pin,
                "out_net": out_net,
                "zone": zone,
                "exact_block": exact_block 
            })

            zone_stats[zone] += 1
            target_id += 1

        self.targets_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.targets_file, 'w') as f:
            json.dump(targets, f, indent=4)

        self.logger.info("==================================================")
        self.logger.info("🎯 TARGET EXTRACTION COMPLETE (VERILOG NATIVE)")
        self.logger.info(f"Total Injectable Gates Found: {len(targets)}")
        for z, c in zone_stats.items():
            if c > 0:
                self.logger.info(f"  ➤ {z:<15}: {c} gates")
        self.logger.info("==================================================")

if __name__ == "__main__":
    agent = TargetExtractorAgent()
    agent.execute()