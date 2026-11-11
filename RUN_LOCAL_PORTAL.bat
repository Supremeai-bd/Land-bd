@echo off
chcp 65001 >nul
title রায়পুর স্মার্ট ভূমি ও নাগরিক পোর্টাল (Localhost)
color 0A

echo ======================================================================
echo    রায়পুর স্মার্ট ভূমি, নাগরিক ও দলিল রেজিস্ট্রি ওয়ান-স্টপ পোর্টাল
echo    লোকাল হোস্ট রানটাইম (Localhost Server Port 8080)
echo ======================================================================
echo.

set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%01_LIVE_SMART_PORTAL_APP

:: ১. ফাইল অস্তিত্ব যাচাই
if not exist "%APP_DIR%\Land_Intelligence_Hub.html" (
    echo [ERROR] মূল পোর্টাল ফাইল পাওয়া যায়নি: %APP_DIR%\Land_Intelligence_Hub.html
    pause
    exit /b 1
)

:: ২. কোনো বিল্ড প্রয়োজন নেই (Zero-Build Runtime Architecture)
echo [STATUS] প্রজেক্ট আর্কিটেকচার: Zero-Build Instant Execution
echo [STATUS] জাভাস্ক্রিপ্ট ও ডেটাবেস ইঞ্জিন সরাসরি রেডি রয়েছে।
echo.

cd /d "%APP_DIR%"

:: ৩. ব্রাউজারে স্বয়ংক্রিয়ভাবে ওপেন করা
echo [INFO] ব্রাউজারে লোকাল পোর্টাল ওপেন করা হচ্ছে...
start http://localhost:8080/Land_Intelligence_Hub.html

:: ৪. পাইথন লোকাল এইচটিটিপি সার্ভার চালু
echo [INFO] পাইথন লোকাল এইচটিটিপি সার্ভার সক্রিয় (Port 8080)...
echo [INFO] সার্ভার বন্ধ করতে এই উইন্ডোতে Ctrl + C চাপুন।
echo ----------------------------------------------------------------------
echo.

python -m http.server 8080

pause
