@echo off
chcp 65001 >nul
title রায়পুর স্মার্ট ভূমি ও নাগরিক পোর্টাল - ক্লাউড ডেপ্লয়মেন্ট
color 0B

echo ======================================================================
echo    রায়পুর স্মার্ট ভূমি, নাগরিক ও দলিল রেজিস্ট্রি ওয়ান-স্টপ পোর্টাল
echo    এক-ক্লিকে ক্লাউডফ্লেয়ার সার্ভারলেস ডিপ্লয়মেন্ট (Cloud Deploy)
echo ======================================================================
echo.

set SCRIPT_DIR=%~dp0

cd /d "%SCRIPT_DIR%"

echo [INFO] ক্লাউড ডিপ্লয়মেন্ট শুরু হচ্ছে...
echo.

python "%SCRIPT_DIR%deploy_to_cloudflare.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] ক্লাউড ডেপ্লয়মেন্ট সম্পন্ন করা যায়নি! অনুগ্রহ করে এরর মেসেজটি চেক করুন।
    echo.
) else (
    echo.
    echo [INFO] ব্রাউজারে লাইভ পোর্টাল ওপেন করতে যেকোনো কী চাপুন...
    pause >nul
    start https://raipur-land-portal.raipur-land.workers.dev
)

pause

