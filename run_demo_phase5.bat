@echo off
color 0B
echo ======================================================================
echo RACER-X Phase 5: Real-Time Interactive Sign-to-Speech Communication
echo Department of AI ^& DS, Vel Tech R^&D Institute, Chennai, India
echo ======================================================================
echo.
echo Launching camera pipeline and neural inference engine...
echo.
echo Controls in Live Window:
echo   [q / ESC] : Quit
echo   [c]       : Clear Subtitle
echo   [s]       : Speak Sentence Out Loud
echo   [m]       : Toggle Auto-Speech Mute/Unmute
echo.
python demo_live.py
echo.
echo ======================================================================
echo Demo finished.
echo ======================================================================
pause
