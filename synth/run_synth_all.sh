#!/bin/bash
# ==============================================================================
# Native Yosys Script (.ys) Generator & Automation for Fault-Tolerant Neurons
# ==============================================================================

echo "🧹 Cleaning old netlists and graphs..."
rm -rf ../netlists/raw/*
rm -rf ../netlists/graphs/*
mkdir -p ../netlists/raw
mkdir -p ../netlists/graphs

GHDL_PLUGIN_PATH="/home/libftizh/ghdl-yosys-plugin/ghdl.so"

declare -a models=(
    "../rtl/mark2_baseline.vhd baseline_neuron2"
    "../rtl/mark2_homeostatic.vhd homeostatic_neuron2"
    "../rtl/mark2_light_tmr.vhd light_tmr_neuron2"
    "../rtl/mark2_ultimate_tmr.vhd ultimate_tmr_neuron2"
)

for model in "${models[@]}"; do
    set -- $model
    VHDL_FILE=$1
    TOP_MODULE=$2
    
    echo -e "\n=================================================================="
    echo "🔥 Generating Native .ys script and Processing: $TOP_MODULE"
    echo "=================================================================="
    
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    cat <<EOF > temp_synth.ys
plugin -i $GHDL_PLUGIN_PATH

ghdl --std=08 $VHDL_FILE -e $TOP_MODULE

hierarchy -check -top $TOP_MODULE

proc

opt_expr
opt_clean

fsm
memory

techmap
abc -g AND,OR,XOR,MUX

clean

#show -format dot -prefix ../netlists/graphs/${TOP_MODULE}_schematic -colors 2 -width

write_verilog -noattr -noexpr ../netlists/raw/${TOP_MODULE}_generic.v
write_json ../netlists/raw/${TOP_MODULE}_generic.json

stat
EOF

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    yosys temp_synth.ys | tee ../netlists/raw/${TOP_MODULE}_synth.log
    
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    if [ -f ../netlists/graphs/${TOP_MODULE}_schematic.dot ]; then
        echo "🎨 Rendering schematic image for $TOP_MODULE..."
        dot -Tsvg ../netlists/graphs/${TOP_MODULE}_schematic.dot -o ../netlists/graphs/${TOP_MODULE}_schematic.svg
        echo "🖼️ Schematic saved successfully!"
    fi

done

rm temp_synth.ys

echo -e "\n🎯 ALL DONE! Bulletproof Generic Synthesis with native .ys files is Complete!"