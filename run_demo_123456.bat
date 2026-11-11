@echo off
color 0B
echo ======================================================================
echo RACER-X: MediaPipe Sign Language Live Video Translator
echo Project Video: 123456.mp4
echo Department of AI ^& DS, Vel Tech R^&D Institute, Chennai, India
echo ======================================================================
echo.

IF NOT EXIST "123456.mp4" (
    echo [-] Error: 123456.mp4 not found in the project directory!
    echo.
    pause
    exit /b 1
)

echo [+] Launching MediaPipe Live Sign Detection on 123456.mp4...
echo [+] Screen HUD: Active | Output Video: output_123456.mp4
echo.
python demo_video.py --video 123456.mp4 --output output_123456.mp4

echo.
echo ======================================================================
echo Execution complete. Output video saved to: output_123456.mp4
echo ======================================================================
echo.
pause
