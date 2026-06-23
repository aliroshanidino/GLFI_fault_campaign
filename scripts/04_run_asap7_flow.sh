#!/bin/bash
echo "🚀 [STEP 4] Full RTL-to-GDSII Execution on Docker (7nm ASAP7 Node)..."

cd "$HOME/neuro_paper_1/Generic_GLFI_fault_campaign/orfs/flow"

# معرفی مسیر کانفیگ‌ها بر اساس ساختار سیستم‌فایل داخلی داکر (/work)
designs=(
    "/work/designs/asap7/snn_baseline/config.mk"
    "/work/designs/asap7/snn_homeostatic/config.mk"
    "/work/designs/asap7/snn_selective_tmr/config.mk"
    "/work/designs/asap7/snn_ultimate_tmr/config.mk"
)

for config in "${designs[@]}"; do
    echo "========================================================="
    echo "⚡ Processing Full Flow for: $config"
    echo "========================================================="
    
    # اجرای کامل فلو جهت استخراج تمام پارامترهای جدول ژورنال
    ./util/docker_shell make DESIGN_CONFIG=$config
    
    echo "✅ Flow finished for $config"
done

echo "🎉 [STEP 4 COMPLETED] All processes are done. Check logs to extract PPA values!"