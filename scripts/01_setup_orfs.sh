#!/bin/bash
echo "🚀 [STEP 1] Setting up OpenROAD Flow Scripts (ORFS) & Docker..."

# تنظیمات پروکسی برای عبور از تحریم‌های داکر
export HTTP_PROXY="http://127.0.0.1:8080"
export HTTPS_PROXY="http://127.0.0.1:8080"

cd ~/neuro_paper_1/Generic_GLFI_fault_campaign/

# پاک کردن پوشه ناقص قبلی (در صورت وجود)
if [ -d "orfs" ]; then
    echo "🗑️ Removing previous incomplete ORFS directory..."
    rm -rf orfs
fi

# دانلود مخزن به صورت سبک و بدون نرم‌افزارهای سنگین (بدون recursive)
echo "📥 Cloning lightweight ORFS workspace..."
git clone https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git orfs

# دریافت آخرین نسخه ایمیج داکر OpenROAD (که شامل تمام نرم‌افزارهاست)
echo "🐳 Pulling OpenROAD Docker Image..."
docker pull openroad/orfs:latest

echo "🎉 [STEP 1 COMPLETED] Infrastructure is ready!"