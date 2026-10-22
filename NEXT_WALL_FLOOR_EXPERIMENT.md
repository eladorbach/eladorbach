# Next physical experiment — real wall, floor and preserved corners

**Date:** 2026-10-22 | **Milestone:** A2 controlled M1600 metrology baseline.
**Status:** Awaiting labeled physical target / controlled scene. Existing 16 MiB saved sensor PCAP already evaluated in a read-only *exploratory* run; no new sensor recordings made yet.

## Why
Our first 5 real-PCAP frames contain large plane-like clusters and 15–18 mm threshold-conditioned RMS residuals. The auto-RANSAC selection truncates errors to 40 mm and can pick different physical structures, so these are *not* qualified wall accuracies and cannot support a LinkedIn claim. We now need a known surface, fixed distance, independently checked corners and repeated trials.

## Minimal physical setup — use what's already present
1. Leave the M1600 and IMX252 live on the AGX/RViz display. Do not move or rewire powered 1000BASE-T1 cables.
2. Aim at a mostly flat **matte wall** with a visible wall/floor meeting line or right-angle corner. Prefer a quiet, stationary scene with no mirror for first baseline; note glossy portions separately.
3. Keep the unit *motionless* on a stable support, with representative target distance roughly 1.5–3 m if practical, using whatever position is safe and available. Measure sensor-to-wall distance independently with an owned tape/ruler if possible; if not, record distance UNKNOWN rather than guessing.
4. Mark one physically dimensioned feature: wall/floor corner or a simple available flat board with measured width; record actual reference dimension(s).
5. For each of **three** stationary acquisitions (bounded 5–10 s each), document light conditions, range, camera exposure, physical setup, timestamps and sensor temp if available. The camera preview has host stamps, so do not call it synchronized.
6. Use known fixed ROI after viewing first actual scan; define surface coordinates and hold-out evaluation before any tuning. Keep ROI off glass, window edges, cables, people and corners when measuring plane noise; test edge preservation separately.
7. Don't permanently save room images by default. Store LiDAR PCAP locally only under controlled retention with hash and anonymization; sensor/scene raw clips NOT publicly uploaded.

## Immediate method and evaluation
- Compute plane model on training samples; assess **held-out** target points without threshold-truncating the residual distribution.
- Report density and coverage for ROI, RMS/P50/P95 orthogonal residual, confidence limits from repeated trials; include outlier fraction using a fixed robust threshold.
- Use the same physical corner to measure edge displacement and feature preservation after filtering.
- Only then compare: raw scan, robust plane fitting, edge-aware surfel fusion and multiview registration.
- Subsequent grayscale IMX252 projection only after camera intrinsics/extrinsics are verified.
- Subsequent PolarSens reflective scene uses separate labeled trials; never infer mirror truth from polarization alone.

## Existing software evidence (read-only, not yet metrology)
Report: `../evidence/M1600_EXPLORATORY_PLANE_BASELINE_20261022.txt`
Source: `../scripts/m1600_exploratory_plane_baseline.py`
Capture SHA256: `13e4195e5690753a93dc09fcfe54bb568db6c35835692e9ac8c44412483af72e`
The exploratory unsupervised five-frame RMS range was **15.05–17.59 mm conditional on the 40 mm inlier criterion**. No source motion, units accuracy, wall identity or absolute reference is validated.
Independent software-format decoder audit: `../evidence/M1600_DECODER_AUDIT_20261022.txt` (11,752 real returns match mbiselx reference formula; not physical calibration).
No current live viewer source, ROS package, NIC or kernel settings changed by these offline tests.

## Exit criterion (not yet achieved)
An independently labeled surface, repeatable numerical plane RMS/P95, documented edge integrity and saved immutable dataset hashes. At that point we can select an improvement target and test it without contaminating held-out data.

## What follows
Milestone A3: precise IMX252 intrinsic/extrinsic alignment and clock tests.
Milestone A4: controlled mobile multiview registration.
Milestone A5: PolarSens reflection-aware confidence test.
Milestone A6: realistic Gaussian/surfel/mesh rendering and public ablation plots.

## Static-camera image-quality setting verified 2026-10-22
- GainAuto=Off and Gain=0 dB, ExposureAuto=Continuous. Native monochrome camera acquisition changed from 30 Hz to **5 Hz**, which raised automatic maximum exposure from 33.333 ms to **200 ms**.
- Real preview improved mean 27.05 → 85.39, while 13.5% of pixels still reach >=250 due to scene dynamic range; camera-to-LiDAR calibration NOT yet completed. Live M1600 undisturbed.
- These longer exposures are suitable for the current **stationary** wall experiment; for moving scans the exposure/frame-rate tradeoff must be revisited. Full private settings log is kept only on AGX.
