@echo off
color 0B
echo ======================================================================
echo RACER-X: Extracting and Integrating AI4Bharat INCLUDE Real Dataset
echo Department of AI ^& DS, Vel Tech R^&D Institute, Chennai, India
echo ======================================================================
echo.

IF NOT EXIST "archive.zip" (
    echo [-] Error: archive.zip not found in project folder!
    echo Please make sure archive.zip is placed in this folder.
    pause
    exit /b
)

echo [+] Found archive.zip! (Size: ~2.54 GB)
echo [+] Extracting real human sign language dataset...
echo.

powershell -Command "Expand-Archive -Path 'archive.zip' -DestinationPath 'dataset\include_raw' -Force"

echo.
echo [+] Extraction finished! Running data standardization...
python process_include_dataset.py
echo.
pause
