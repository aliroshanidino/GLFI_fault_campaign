#!/bin/bash
echo "🚀 [STEP 3] Configuring ORFS for ASAP7 (7nm) Node (Power Optimized)..."

PROJECT_ROOT="$HOME/neuro_paper_1/Generic_GLFI_fault_campaign"
ORFS_DESIGNS="$PROJECT_ROOT/orfs/flow/designs/asap7"
SYNTH_DIR="$PROJECT_ROOT/synth"

# ساخت پوشه‌های مجزا برای هر ۴ مدل
for name in baseline homeostatic selective_tmr ultimate_tmr; do
    mkdir -p "$ORFS_DESIGNS/snn_$name"
done

# کپی کردن نت‌لیست‌های وریلاگ به پوشه‌های اختصاصی ۷ نانومتر
cp "$SYNTH_DIR/snn_core_baseline.v" "$ORFS_DESIGNS/snn_baseline/"
cp "$SYNTH_DIR/snn_core_homeostatic.v" "$ORFS_DESIGNS/snn_homeostatic/"
cp "$SYNTH_DIR/snn_core_selective_tmr.v" "$ORFS_DESIGNS/snn_selective_tmr/"
cp "$SYNTH_DIR/snn_core_ultimate_tmr.v" "$ORFS_DESIGNS/snn_ultimate_tmr/"

make_config() {
    local dir=$1
    local top_module=$2
    local v_file=$3
    local abc_area=$4
    
    cat << EOF > "$ORFS_DESIGNS/$dir/config.mk"
export PLATFORM       = asap7
export DESIGN_NAME    = $top_module
export VERILOG_FILES  = /work/designs/asap7/$dir/$v_file
export SDC_FILE       = /work/designs/asap7/$dir/constraint.sdc
export CORE_UTILIZATION = 45
export CORE_ASPECT_RATIO = 1.0
export PLACE_DENSITY  = 0.55
export ABC_AREA       = $abc_area
export ABC_SPEED      = 1
EOF
}

# اعمال کانفیگ‌ها با اسامی دقیق ماژول‌های شما و حفظ TMR (با ABC_AREA=0)
make_config "snn_baseline"      "baseline_neuron2"      "snn_core_baseline.v"      "1"
make_config "snn_homeostatic"   "homeostatic_neuron2"   "snn_core_homeostatic.v"   "1"
make_config "snn_selective_tmr" "light_tmr_neuron2"     "snn_core_selective_tmr.v" "0"
make_config "snn_ultimate_tmr"  "ultimate_tmr_neuron2"  "snn_core_ultimate_tmr.v"  "0"

# ساخت قید کلاک بهینه (4.0 نانوثانیه = 250 مگاهرتز) بر اساس پورت clk
for dir in snn_baseline snn_homeostatic snn_selective_tmr snn_ultimate_tmr; do
cat << EOF > "$ORFS_DESIGNS/$dir/constraint.sdc"
create_clock -name core_clock -period 4.0 [get_ports {clk}]
set_input_delay  -clock core_clock 0.2 [all_inputs]
set_output_delay -clock core_clock 0.2 [all_outputs]
EOF
done

echo "🎉 [STEP 3 COMPLETED] Configs and Constraints created successfully with Docker paths!"