#!/bin/bash
echo -e "\n📊 ================= IEEE PPA RESULTS (7nm ASAP7) ================= 📊\n"

cd "$HOME/neuro_paper_1/Generic_GLFI_fault_campaign/orfs/flow"
ENTITIES=("baseline_neuron2" "homeostatic_neuron2" "light_tmr_neuron2" "ultimate_tmr_neuron2")

for entity in "${ENTITIES[@]}"; do
    echo "========================================================="
    echo "✅ Analyzing Model: $entity"

    # 1. استخراج مساحت و تعداد سلول‌ها از لاگ رسمی جانمایی (Placement Log)
    PLACE_LOG="logs/asap7/$entity/base/3_5_place_dp.log"
    if [ -f "$PLACE_LOG" ]; then
        AREA=$(grep "Instances area:" "$PLACE_LOG" | awk -F'Instances area: ' '{print $2}' | awk '{print $1}')
        CELLS=$(grep "Total cells:" "$PLACE_LOG" | tail -n 1 | awk '{print $3}')
        echo "   -> Core Area (um^2):       $AREA"
        echo "   -> Total Standard Cells:   $CELLS"
    else
        echo "   ❌ ERROR: Placement log not found."
    fi

    # 2. اسکریپت TCL برای توان و تاخیر
    TCL_SCRIPT="extract_ppa_${entity}.tcl"
    cat << EOF > "$TCL_SCRIPT"
source /OpenROAD-flow-scripts/flow/platforms/asap7/liberty_suppressions.tcl
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /work/results/asap7/$entity/base/3_place.odb
read_sdc /work/results/asap7/$entity/base/3_place.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
puts "MY_WNS: [sta::worst_slack -max]"
report_power
exit
EOF

    # اجرای داکر
    ./util/docker_shell openroad "/work/$TCL_SCRIPT" > "ppa_report_${entity}.txt" 2>&1

    # 3. پارس کردن تاخیر بحرانی و محاسبه فرکانس
    WNS=$(grep "MY_WNS:" "ppa_report_${entity}.txt" | awk '{print $2}')
    if [ ! -z "$WNS" ]; then
        DELAY=$(echo "4.0 - $WNS" | bc -l | awk '{printf "%.3f", $0}')
        FMAX=$(echo "1000 / $DELAY" | bc -l | awk '{printf "%.2f", $0}')
        echo "   -> Critical Path Delay:    $DELAY ns"
        echo "   -> Max Frequency Fmax:     $FMAX MHz"
    fi

    # 4. پارس کردن توان
    POWER_LINE=$(grep "^Total" "ppa_report_${entity}.txt" | tail -n 1)
    if [ ! -z "$POWER_LINE" ]; then
        INT_MW=$(echo "$POWER_LINE" | awk '{printf "%.4f", $2 * 1000}')
        SW_MW=$(echo "$POWER_LINE" | awk '{printf "%.4f", $3 * 1000}')
        LEAK_NW=$(echo "$POWER_LINE" | awk '{printf "%.2f", $4 * 1000000000}')
        TOT_MW=$(echo "$POWER_LINE" | awk '{printf "%.4f", $5 * 1000}')
        echo "   -> Internal Power:         $INT_MW mW"
        echo "   -> Switching Power:        $SW_MW mW"
        echo "   -> Leakage Power:          $LEAK_NW nW"
        echo "   -> Total Core Power:       $TOT_MW mW"
    fi
done
echo "========================================================="
EOF