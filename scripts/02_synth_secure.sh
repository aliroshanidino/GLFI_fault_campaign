#!/bin/bash
echo "🚀 [STEP 2] Secure VHDL-to-Verilog Synthesis..."

source ../../dse_venv/bin/activate
cd ../synth

# معرفی مسیر قطعی و دقیقِ پلاگینی که همین الان کامپایل کردیم
PLUGIN_PATH="/home/libftizh/ghdl-yosys-plugin/ghdl.so"

echo "🛠️ Synthesizing Baseline..."
yosys -p "plugin -i $PLUGIN_PATH; ghdl --ieee=synopsys ../rtl/mark2_baseline.vhd -e baseline_neuron2; hierarchy -check -top baseline_neuron2; prep -top baseline_neuron2; write_verilog -noattr snn_core_baseline.v"

echo "🛠️ Synthesizing Homeostatic..."
yosys -p "plugin -i $PLUGIN_PATH; ghdl --ieee=synopsys ../rtl/mark2_homeostatic.vhd -e homeostatic_neuron2; hierarchy -check -top homeostatic_neuron2; prep -top homeostatic_neuron2; write_verilog -noattr snn_core_homeostatic.v"

echo "🛡️ Synthesizing Selective TMR (Protected)..."
yosys -p "plugin -i $PLUGIN_PATH; ghdl --ieee=synopsys ../rtl/mark2_light_tmr.vhd -e light_tmr_neuron2; hierarchy -check -top light_tmr_neuron2; prep -top light_tmr_neuron2; write_verilog snn_core_selective_tmr.v"

echo "🛡️ Synthesizing Ultimate TMR (Protected)..."
yosys -p "plugin -i $PLUGIN_PATH; ghdl --ieee=synopsys ../rtl/mark2_ultimate_tmr.vhd -e ultimate_tmr_neuron2; hierarchy -check -top ultimate_tmr_neuron2; prep -top ultimate_tmr_neuron2; write_verilog snn_core_ultimate_tmr.v"

echo "🎉 [STEP 2 COMPLETED] 4 Verilog netlists generated successfully!"