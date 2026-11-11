@echo off
echo =======================================================
echo RACER-X Source 2 Benchmark Generation Pipeline
echo =======================================================
echo.
echo Target: 6,000 Standard Benchmark Continuous Samples
echo (Combining with ~5,000 ISH News = ~11,000 Sweet Spot Dataset)
echo.
python collect_source2_benchmarks.py 6000
echo.
echo =======================================================
echo Source 2 Benchmark Generation Complete!
echo =======================================================
pause
