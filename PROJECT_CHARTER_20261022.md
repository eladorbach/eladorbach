# AGX multimodal 3D reconstruction — project charter
**Version:** 2026-10-22 | **Status:** research prototype, baseline capture verified; mobile reconstruction NOT yet demonstrated

## Purpose
Build a *mobile*, metrically defensible reconstruction from real LiDAR, monochrome camera, and later polarization measurements. Show that flat walls/floors become visibly clean **because measurements agree**, not because missing or conflicting data are silently hidden. Deliver an expert-grade reproducible engineering demo with raw, registered, confidence-aware, and rendered layers.

## Central research question
Can multi-view geometry + independently calibrated camera evidence + polarization cues improve the *geometric faithfulness* and *visual smoothness* of indoor scenes, while identifying reflections/multipath and preserving real edges and uncertainty?

## Non-negotiable presentation policy
- Label **RAW / REGISTERED / FILTERED / INFERRED / RENDERED** separately.
- Replayed real data is labeled **recorded**, never *live*. No synthetic points mixed with sensor ground truth.
- Preserve hashes, raw data, timestamps, transforms, calibration inputs, software revisions, and failure results locally.
- Maintain side-by-side identical camera views and scaling across stages. Keep comparison baselines frozen.
- Never call interpolation or learned depth 'sensor super-resolution' without distinguishing inferred geometry from new independent measurements.
- A visually smooth surface is not accepted unless held-out measurements support it and real edges survive.
- Publish only shareable code and scrubbed example data; no personally identifying interior imagery by default.

## Owned hardware / verified 2026-10-22
- Jetson AGX Xavier 32 GB, Ubuntu 20.04, isolated ROS1 Noetic container.
- Velodyne Velarray M1600: **LIVE** authentic PointCloud2 on /m1600/points, approx 20-22 frames/s previously measured; needs timestamp and geometry-validation work.
- The Imaging Source monochrome IMX252: **LIVE** 2048x1536 acquisition around 30 fps, 384x288 Mono8 ~5 fps preview in /imx252/image_preview. No synchronized hardware timestamps confirmed.
- IMX250 PolarSens camera: **OWNED**, not integrated with this rig yet. A separate imaging modality to test DoLP/AoLP and reflection discrimination.
- Hesai QT128C2X: **OWNED; RAW DATA NOT YET VERIFIED**. Previous automotive-link wiring and physical 1000BASE-T1 PHY must be checked before retry.
- Waymo LiDAR(s): **OWNED; EXACT MODEL / USABLE SDK / LICENSE GATES OPEN**. Historical SDK material may be proprietary; never upload it publicly.
- Innoviz: **PROSPECTIVE ONLY**; trade offer for unused Vision Engineering Mantis microscope not yet confirmed and model not verified.
- More / higher-resolution cameras: **candidate acquisitions only**, not counted as owned until received and tested.

## Milestone gates (target acceptance criteria; NOT reported results)
| Gate | Work | Required evidence |
| --- | --- | --- |
| 0 — DONE | Verify real, live M1600 and IMX252 display | Two real sensor topics, independent timestamps, unchanged inputs, screenshot |
| 1 — NEXT | Validate M1600 packet-to-XYZ decoder | Cross-check raw packet geometry and units against independent M1600 driver/docs and measured targets |
| 2 | Static baseline: floor, walls, corners | Held-out point-to-plane RMS/P95, corner displacement, density, drop rate, stability |
| 3 | Calibrate each camera and time coupling | Intrinsics/distortion error, LiDAR-camera rigid transform, time-offset/jitter; measured not guessed |
| 4 | Controlled multi-view mobile scan + revisit | Scan-to-map overlap, trajectory drift, loop closure, failure flags; pose source explicitly documented |
| 5 | Edge-preserving metric reconstruction | Show original and fused surface; improvement on held-out geometry without corner/feature erosion |
| 6 | Add IMX250 PolarSens for reflections | Raw polarization samples; DoLP/AoLP; ablation with vs without polarization |
| 7 | Robustness and alternate-LiDAR comparison | Mirror/glass/metal trials, false geometry metrics; M1600 vs QT128 vs Waymo vs acquired Innoviz |
| 8 | Optional mesh / Gaussian render | Measured XYZ and inferred splats presented as separate layers; accuracy retained |
| 9 | Reproducible public demonstration | Sanitized source, methods, configs, statistical plots, limits, video, DOI/references if available |

## Evidence-first quality scorecard
1. **Wall/floor flatness**: RMS, median, and P95 orthogonal distance to a fit plane, using held-out points; compare RAW vs REGISTERED vs FILTERED.
2. **Corner integrity**: displacements of physical edges/corners and small targets before/after smoothing. A prettier wall with erased edges is a FAIL.
3. **Actual coverage**: surface cells independently observed from >=2 distinct viewpoints, map completeness, and overlap. Repeated points alone do not imply better sensor resolution.
4. **Geometry consistency**: plane normals and landmark positions across revisits; evaluate loop-closure drift.
5. **Reflection and occlusion**: measure false-positive phantom surfaces, missing geometry, and false rejection of legitimate returns.
6. **Calibration**: reprojection residual distributions and uncertainty; independent validation target, lens and viewing geometry recorded.
7. **Timing**: camera/LiDAR acquisition time domains, age of data, jitter, packet drop, processing FPS and end-to-end display latency independently measured.
8. **Compute**: CPU/GPU utilization, sustained performance, peak RAM and temperature, power constraints and number of simultaneously running publishers.
Targets for numeric *improvement* must be frozen after Gate 2; do NOT invent sub-millimeter precision or undocumented ground truth.

## Prototype processing chain
RAW sensor packets / original mono images -> decode verification -> calibrated clock/frames ->
LiDAR(-IMU when available) pose tracking -> multiview registration / loop closures ->
confidence-aware surfels or planar reconstruction -> camera edge/contrast checks ->
polarization constraints / reflection consistency -> optional render layer.
Keep ALL original data as immutable experiment provenance, but store personal raw video and private archives locally rather than on GitHub.

## Polarization experimental hypothesis
Use owned IMX250 PolarSens to collect simultaneous polarization-angle intensities. Derive AoLP/DoLP with controlled illumination and rotation; compare whether reflective glass/mirrors/painted walls can be separated from trustworthy diffuse surfaces. Polarization changes with viewing angle, material, and light; it is not a binary ground-truth mirror classifier. Run controlled ablations with camera only / LiDAR only / camera+LiDAR / +polarization and report errors including false positives. Explore ICCV 2025 PolGS and CVPR 2026 PolarGuide-GSDR **as research references, not installed dependencies**.

## Current limitations
- M1600 decoding includes assumptions which MUST be independently verified before reporting precision.
- No published camera intrinsic/extrinsic calibration yet; no verified hardware sync; no mobile SLAM, iG-LIO, or Gaussian pipeline running.
- Image preview is downsampled and monochrome, not real RGB texturing.
- ROS1 Noetic is existing working runtime; do not add a second ROS install just for its own sake.
- Security and privacy: Waymo third-party SDK may be nonredistributable. Do not publish private logs, camera views, full raw captures, serials, embedded addresses, or proprietary vendor data by default.

## Primary source links
- iG-LIO M1600 ROS2 port: https://arxiv.org/html/2607.09947v1
- Hesai official QT128 resources: https://www.hesaitech.com/product_downloads/qt128/
- ICCV 2025 Polarimetric Gaussian Splatting: https://doi.org/10.1109/ICCV51701.2025.02606
- CVPR 2026 PolarGuide-GSDR: https://openaccess.thecvf.com/content/CVPR2026/html/Shan_PolarGuide-GSDR_3D_Gaussian_Splatting_Driven_by_Polarization_Priors_and_Deferred_CVPR_2026_paper.html
- USENIX 2026 user-supplied manuscript, "Seeing is Deceiving": local user-uploaded reference; NOT redistributed in repository.

**Project scope safety:** No purchase assumed, no sensor rewiring powered, no AGX reboot/host OS replacement, no default route change, no domain redirect, and no bulk downloads.

## 2026-10-22 decoder-audit update
- PASS (software correspondence only): 80 real M1600 packets, 11,752 valid returns, 0 XYZ differences above 0.02 mm vs mbiselx published BigEndianStructure and coordinate equations.
- Report: ../evidence/M1600_DECODER_AUDIT_20261022.txt; script ../scripts/m1600_decoder_reference_audit.py; underlying PCAP unchanged.
- Real-world wall/ground distance accuracy, calibration and timestamps remain UNVERIFIED. Do not elevate software agreement into physical precision.
