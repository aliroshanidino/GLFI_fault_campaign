# utils.py
import os
import logging
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class PathManager:
    """Centralized path management for the Generic Fault Campaign."""
    CONFIG_FILE = PROJECT_ROOT / "config" / "project.yaml"
    
    NETLIST_DIR = PROJECT_ROOT / "netlists" / "raw"
    INSTRUMENTED_DIR = PROJECT_ROOT / "netlists" / "instrumented"
    
    # 🌟 این خطوط دقیقاً همان‌هایی هستند که باعث ارور شدند و الان اضافه شدند 🌟
    TARGETS_MANIFEST = PROJECT_ROOT / "manifests" / "targets.json"
    RUNTIME_CONFIG = PROJECT_ROOT / "manifests" / "runtime_config.json"
    BASELINE_SUMMARY = PROJECT_ROOT / "manifests" / "baseline_summary.json"
    
    SIM_DIR = PROJECT_ROOT / "sim"
    LATEST_RUN_DIR = PROJECT_ROOT / "runs" / "latest"
    RAW_RESULTS_CSV = LATEST_RUN_DIR / "campaign_results.csv"

def setup_logger(name="GLFI_Master"):
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)-8s | %(name)-15s | %(message)s', "%H:%M:%S")
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        fh = logging.FileHandler(log_dir / "system.log", mode='a')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger

def load_config():
    if not PathManager.CONFIG_FILE.exists():
        raise FileNotFoundError(f"Missing config file at {PathManager.CONFIG_FILE}")
    with open(PathManager.CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)