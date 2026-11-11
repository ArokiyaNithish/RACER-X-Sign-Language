@echo off
color 0B
echo ======================================================================
echo RACER-X: Digital Video Sign Language Translator (MediaPipe Live)
echo Department of AI ^& DS, Vel Tech R^&D Institute, Chennai, India
echo ======================================================================
echo.

set VIDEO_INPUT=%~1
IF "%VIDEO_INPUT%"=="" (
    IF EXIST "123456.mp4" (
        echo [+] Defaulting to project video: 123456.mp4
        set VIDEO_INPUT=123456.mp4
    ) ELSE (
        set /p VIDEO_INPUT="Enter Video File Path (e.g. video.mp4 or your_clip.mp4): "
    )
)

:: Strip quotes if entered by the user
set VIDEO_CLEAN=%VIDEO_INPUT:"=%

echo.
echo Processing video: "%VIDEO_CLEAN%"
echo.
python demo_video.py --video "%VIDEO_CLEAN%"
echo.
pause
