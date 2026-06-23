# manifest_builder.py
import json
from utils import PathManager, setup_logger, load_config

class ManifestBuilderAgent:
    """Layer A: Freezes configuration and generates runtime manifests for Cocotb."""
    def __init__(self):
        self.logger = setup_logger("ManifestBuilder")
        self.config = load_config()
        self.targets_path = PathManager.TARGETS_MANIFEST
        self.runtime_cfg_path = PathManager.RUNTIME_CONFIG

    def execute(self):
        self.logger.info("Building Runtime Manifest for Cocotb execution...")
        if not self.targets_path.exists():
            self.logger.error("targets.json not found! Cannot build runtime configuration.")
            return False

        with open(self.targets_path, 'r') as f:
            targets = json.load(f)

        runtime_payload = {
            "project_name": self.config['project']['name'],
            "top_module": self.config['project']['top_module'],
            "netlist_type": "Yosys_Generic", # 🌟 مشخص‌کننده نوع نت‌لیست
            "total_targets": len(targets),
            "simulation_settings": self.config['simulation'],
            "fault_model": self.config['fault_model']
        }

        self.runtime_cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.runtime_cfg_path, 'w') as f:
            json.dump(runtime_payload, f, indent=4)

        self.logger.info("==================================================")
        self.logger.info("📦 MANIFEST BUILD COMPLETE")
        self.logger.info(f"Target Module : {runtime_payload['top_module']}")
        self.logger.info(f"Total Targets : {runtime_payload['total_targets']} nodes")
        self.logger.info(f"Sim Cycles    : {runtime_payload['simulation_settings']['observation_cycles']}")
        self.logger.info(f"Injection at  : {runtime_payload['simulation_settings']['injection_delay']} cycles")
        self.logger.info(f"Runtime config frozen and saved to: {self.runtime_cfg_path.name}")
        self.logger.info("==================================================")
        return True

if __name__ == "__main__":
    agent = ManifestBuilderAgent()
    agent.execute()