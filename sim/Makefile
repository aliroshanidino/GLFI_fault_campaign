# sim/Makefile (Parallel Sandbox Optimized)

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

TOPLEVEL = $(TOP_MODULE)
MODULE = cocotb_orchestrator

VERILOG_SOURCES += $(PROJ_ROOT)/sim/tb_top.v
VERILOG_SOURCES += $(PROJ_ROOT)/netlists/instrumented/$(TOP_MODULE)_instrumented.v

include $(shell cocotb-config --makefiles)/Makefile.sim

clean_all:
	rm -rf sim_build results.xml waveform.vcd