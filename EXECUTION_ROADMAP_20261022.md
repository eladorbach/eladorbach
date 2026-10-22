# Operator-ready roadmap: controlled proof of geometric reconstruction
Date: 2026-10-22 | Constraints: no purchases, no large downloads, keep AGX/HDMI/RViz live.
Research basis: [Feb–Oct 2026 survey](RESEARCH_20260222_TO_20261022.md).
Statuses must be explicitly measured PASS / FAIL / NOT STARTED / BLOCKED.

## Objective (publishable scientific claim, not guaranteed result)
Demonstrate that uncertainty-aware, multi-view, edge-preserving metric reconstruction of a real indoor scene delivers **smoother flat walls/floors** than raw M1600 returns while maintaining held-out geometric agreement and sharp physical corners; polarization and cross-modal consistency may reduce mirror/glass multipath false surfaces. Prove or falsify through ablations, uncertainty bands, and dataset hashes.

## Phase A — before changing any active service [NEXT; safest]
A0. Snapshot live inputs and code hashes, process tree, memory/CPU, ROS topic types, packet drop counters, NIC settings, temp, software rendering status. No reboots.
A1. Validate M1600 decoding as software implementation (first pass DONE for 80 real packets/11,752 valid returns) and repeat on different range/return patterns; compare against known dimension/plane targets before interpreting absolute XYZ metrology.
A2. Obtain static sample from room corner, wall and floor. Minimum 3 independent repeats at each pose, keep input sizes capped. Label possible reflective objects, moving people, and unknown geometry; user reviews private-image handling. No 'clean' filtering for baseline.
A3. Create reproducible read-only analysis: estimate RANSAC/robust plane on *training* subset, evaluate independent *held-out* points at same target; record RMS/P50/P95, normals, plane thickness and outlier fraction. Freeze sampling seed and ROI definitions in JSON before algorithm tuning.
A4. Bench ROI/frame time, ROS inter-arrival, CPU, GPU load and RAM. Keep one publisher per raw topic; do not infer physical sensor latency solely from ROS host stamps.

**A-gate success**: matching PCAP hashes, validated coordinate-unit behavior on measured physical target, 3+ repeatable static trials, reproducible CSV and plots, unchanged live viewer. No target error-improvement numbers invented before baselines.

## Phase B — calibration and physically honest fusion
B1. Determine owned camera lens model, exact image format, distortion, response/exposure/lighting; use physically dimensioned ChArUco/checkerboard if already available. Avoid buying a target until alternatives assessed.
B2. Determine rigid M1600->IMX252 optical transform from several diverse viewpoints with enough target geometry. Save full intrinsics/extrinsics, covariance and independent reprojection P50/P95.
B3. Establish acquisition-clock offset/jitter. If no hardware sync available, start STATIC scene calibration with cautious uncertainty, not mobile color projection. A stationary shared visible moving target can assist offset estimation, but not replace true hardware timestamps.
B4. Overlay **genuine measured** M1600 geometry onto actual grayscale IMX252 frames. Handle occlusion, depth sign/FOV and invalidate out-of-frame projections. Hold out validation frames.
**B-gate success**: well-constrained residuals on unseen frames, unchanged raw data and clear 'unfused/uncalibrated' labels until verified.

## Phase C — controlled mobile scanning; SLAM selection
C1. Rigid mobile mount, logged camera/LiDAR relative pose, cable strain relief and stable power; no sensor held by loose automotive Ethernet wires.
C2. Identify an actual IMU with timestamped data if iG-LIO is to be used. Do NOT fabricate an IMU topic or trajectory. If no IMU, compare LiDAR-only scan-to-map ICP/GICP baseline in controlled slow motion; robust failures and drift quantified.
C3. Repeat trajectory with 2–3 revisits/loop closures; log pose confidence, overlap, drift and relocalization failures. Separate mapping computation FPS and RViz rendering FPS.
C4. Incremental voxel/surfel map: 1) raw measurements; 2) registered independent views; 3) confidence-gated tangent/plane surfels; 4) inferred/synthesized areas as separate visualization.
**C-gate success**: registered planes grow denser in *observed coverage* without wall thickness inflation, corner loss or inconsistent loop closure; repeated independent trial reproduces metrics.

## Phase D — controlled reflection/polarization ablation
D1. Integrate already-owned IMX250 PolarSens, measure four micro-polarizer channels (orientation must be verified), estimate/calibrate Stokes S0/S1/S2, DoLP/AoLP with illumination-angle/dark/flat field controls.
D2. Place safe passive specular scenes: painted wall, mirror, glass, glossy metal; label physical reflective surface geometry and LiDAR phantom/no-return zones. Avoid laser optical modifications.
D3. A/B/C/D:
    A = M1600 only (raw),
    B = M1600 + multiview geometric consistency,
    C = B + calibrated monochrome camera edges,
    D = C + physically calibrated polarization confidence cues.
D4. Measure false accepted phantom clusters, false rejected real walls, edge displacement, time penalties, illumination sensitivity and range dependence. Low-light camera disagreement alone must not delete genuine points.
**D-gate success**: statistically meaningful improvement over simpler baselines on held-out scenes, or document falsification.

## Phase E — render / alternative sensors / publication
E1. Compare deterministic mesh/surfel vs 2026 LiDAR-GS-SLAM and SurfFill concepts in offline bounded resource profiles. Full 3DGS training only on compatible hardware; Xavier hardware/CUDA version are a hard gate.
E2. Compare M1600 vs QT128 vs Waymo vs Innoviz only after sensor-specific safe bring-up and same-target measurement. Confirm Innoviz trade first; do not claim acquisition prematurely.
E3. Archive reproducibility metadata and hashes; review legal/proprietary licenses; produce small privacy-safe GitHub demo files, separate from real internal raw captures. Publish README/experiment scripts/status before measured claims, but never imply calibration has already passed.
E4. LinkedIn reveal after at least one *quantified result* verified twice. Video storyboard and chart from [publication plan](PUBLICATION_PLAN_20261022.md).

## Reliability and observer load policy
- AGX is the protected host, not a crash target. Never change kernel, CUDA, ROS host packages, power or Ethernet default routes to chase a paper's dependencies.
- Existing ROS1 viewer remains working until an isolated replacement passes comparison; production is ONE ROS stack, not ROS1 + ROS2 for aesthetics.
- Every agent/watcher has a fixed queue, deadline and file output contract. No uncontrolled recursive worker spawning.
- Captures bounded by duration and storage; immutable raw hashes; original private video stays locally protected and cleaned up on explicit retention policy.
- Workers may propose code on Git branches; tests and real measurements gate deployment. Any independent Claude/Meta model needs real authorized access and privacy approval; do not pretend those API calls happened.

## Actual acceptance-report template (fill from real trials)
- Dataset ID/sha256, sensor model, temperatures, camera calibration, exposure, distances, scene material, date & time, user privacy signoff.
- Software commit hashes, decoder version, inputs/outputs, ROS/JetPack, clock domains.
- Source FPS, drop rate, acquisition timestamp offset and uncertainty.
- Plane RMS/P50/P95 and confidence interval, edge displacement, coverage gain, held-out geometry agreement.
- Completion 'hallucination' rate, phantom rejection and legitimate-point false rejection.
- CPU/GPU/RAM/latency statistics on AGX and any offline compute separately.
- Failure cases and visualizations using the same projection and point size.
