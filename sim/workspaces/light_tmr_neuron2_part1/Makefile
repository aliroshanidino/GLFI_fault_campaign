# sim/Makefile (Parallel Sandbox Optimized)

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# این متغیرها مستقیماً توسط اسکریپت run_campaign.py به محیط تزریق می‌شوند
TOPLEVEL = $(TOP_MODULE)
MODULE = cocotb_orchestrator

# استفاده از مسیر مطلق برای جلوگیری از گم شدن فایل‌ها در Sandbox
VERILOG_SOURCES += $(PROJ_ROOT)/sim/tb_top.v
VERILOG_SOURCES += $(PROJ_ROOT)/netlists/instrumented/$(TOP_MODULE)_instrumented.v

include $(shell cocotb-config --makefiles)/Makefile.sim

clean_all:
	rm -rf sim_build results.xml waveform.vcd