@echo off
echo =======================================================
echo RACER-X Phase 3: Neural Model Training Pipeline
echo (Physics-Informed, Bilateral-Attention, Frenet-Serret)
echo =======================================================
echo.
python train.py
echo.
echo =======================================================
echo Training Complete! Checkpoints saved in checkpoints\
echo =======================================================
pause
