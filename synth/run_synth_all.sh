#!/bin/bash
# ==============================================================================
# Native Yosys Script (.ys) Generator & Automation for Fault-Tolerant Neurons
# ==============================================================================

echo "🧹 Cleaning old netlists and graphs..."
rm -rf ../netlists/raw/*
rm -rf ../netlists/graphs/*
mkdir -p ../netlists/raw
mkdir -p ../netlists/graphs

# مسیر مطلق پلاگین
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
    # ساخت فایل .ys به صورت خودکار برای همین ماژول
    # --------------------------------------------------------------------------
    cat <<EOF > temp_synth.ys
# 1. بارگذاری مستقیم پلاگین از مسیر مطلق
plugin -i $GHDL_PLUGIN_PATH

# 2. خواندن کد VHDL
ghdl --std=08 $VHDL_FILE -e $TOP_MODULE

# 3. بررسی سلسله مراتب
hierarchy -check -top $TOP_MODULE

# 4. تبدیل پروسس‌ها به گیت
proc

# 5. بهینه‌سازی امن (بدون دستور opt_merge برای حفظ TMR)
opt_expr
opt_clean

# 6. استخراج حافظه‌ها
fsm
memory

# 7. نگاشت به گیت‌های استاندارد جنریک (فقط AND, OR, XOR, MUX, DFF)
techmap
abc -g AND,OR,XOR,MUX

# 8. پاکسازی
clean

# 9. خروجی گرافیک شماتیک
#show -format dot -prefix ../netlists/graphs/${TOP_MODULE}_schematic -colors 2 -width

# 10. خروجی نت‌لیست‌های نهایی
write_verilog -noattr -noexpr ../netlists/raw/${TOP_MODULE}_generic.v
write_json ../netlists/raw/${TOP_MODULE}_generic.json

# 11. گزارش مساحت
stat
EOF

    # --------------------------------------------------------------------------
    # اجرای Yosys با فایل .ys که همین الان ساختیم
    # --------------------------------------------------------------------------
    yosys temp_synth.ys | tee ../netlists/raw/${TOP_MODULE}_synth.log
    
    # --------------------------------------------------------------------------
    # تبدیل عکس گراف
    # --------------------------------------------------------------------------
    if [ -f ../netlists/graphs/${TOP_MODULE}_schematic.dot ]; then
        echo "🎨 Rendering schematic image for $TOP_MODULE..."
        dot -Tsvg ../netlists/graphs/${TOP_MODULE}_schematic.dot -o ../netlists/graphs/${TOP_MODULE}_schematic.svg
        echo "🖼️ Schematic saved successfully!"
    fi

done

# پاک کردن فایل موقت
rm temp_synth.ys

echo -e "\n🎯 ALL DONE! Bulletproof Generic Synthesis with native .ys files is Complete!"