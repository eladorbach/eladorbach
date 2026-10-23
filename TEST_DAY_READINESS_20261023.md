# M1600 → full wall → corner → monochrome IMX252: staged test-day readiness

Date: 2026-10-23 (Jerusalem). Host: owned Jetson AGX Xavier 32 GB.
Purpose: do **all possible software rehearsal NOW** using genuine existing/live M1600
data, while waiting for the user to complete a rigid portable camera+LiDAR rig.

**DO NOT represent an uncalibrated scene as a reference wall.**
The software can be ready before the physical calibration data exist.
The reviewer must distinguish source integrity, hypothesis repeatability,
calibration correctness, reconstruction fidelity, and physical accuracy.

## Current verified engineering gates

| Stage | Current result | Meaning / what remains |
| --- | --- | --- |
| AGX protected live capture | PASS | 2026-10-23, 3s user-current scene: 13,012 source-verified packets, ~4,333 packets/s, 62 frame boundaries, zero sequence discontinuities. Parallel RViz kept running. |
| One-command rehearsal | PASS | 3 independent 2s captures: 43, 42, 42 usable scans, decoded and evaluated with private reports. Gate correctly rejected uncontrolled scene. |
| LiDAR packet identity & capped writes | PASS (synthetic + live) | Verified MAC/IP/UDP 1304B identity comes from **private local evidence JSON**, never committed. Local private PCAPs have SHA-256 receipts. |
| Decoder / filter / held-out tests | PASS | Immutable recorded data, no resmoothing live cloud. Result varies with 0.05, 0.1, 0.2 degree bin width. |
| Wall hypothesis fit + all-point held-out residual | PASS (logic + real rehearsal) | Synthetic planar targets and outliers tested. Real uncontrolled field yields P95 ~2.8m, correctly **not** certified as a flat wall. |
| Full-wall *physical* measurement | BLOCKED (rig/scene) | Operator must aim at an approximately planar physical target and choose angular/range ROI. Absolute distance still requires independent reference. |
| Two-face sharp-corner mathematics | PASS (logic + exploratory scene) | Fitted two independent candidate plane ROIs and their infinite-plane intersection. The ~81deg exploratory candidate is **not** certified as a real corner. |
| Real physical corner-location error | BLOCKED (rig/target) | Requires known physical edge, deliberately selected faces, and independent edge-position reference. |
| ROS and preview throughput / host pairing | PASS (software-timing telemetry only) | 5s observer: M1600 20.70 Hz, IMX252 downsampled preview 4.99 Hz; 16,274 mean points per LiDAR frame. Nearest host stamps p50~50ms/p95~96ms in a 4s followup. NOT hardware synchronization. |
| Mono IMX252 intrinsics mathematics | PASS (synthetic only) | OpenCV 4.5.4 calibration and held-out synthetic projections. Synthetic generated checkerboard 9×6, 54 corners detected. |
| Real intrinsic calibration | BLOCKED (physical target + images) | Need user-verified checkerboard dimensions, 10–60 full-resolution diverse stills, fixed lens/focus. |
| Camera→LiDAR extrinsic mathematics | PASS (synthetic) | File-based 3D LiDAR metres → native IMX252 pixel correspondences, robust PnP and held-out reprojection fit. Real extrinsics still **BLOCKED** on rigid mount, target and measured matches. |
| Real extrinsic drift / frame alignment | BLOCKED | Requires jointly observed physical target, stable rig, verified correspondences and honest timestamps. |
| True 30 FPS mobile native acquisition & hardware synchronization | NOT YET ACCEPTED | Existing preview is intentionally 5 FPS static, 200 ms exposure at 0 dB gain. Mobile must benchmark native 30 FPS, dropped frames, shorter exposure and timing before moving. |
| Multi-view global registration / mobile SLAM | NOT TESTABLE PHYSICALLY YET | No calibrated moving scans, IMU or valid extrinsics; do not claim any successful mobile map. |

No images, raw M1600 PCAPs, sensor identity secrets, raw user scans,
personal room photos or third-party SDK source are in this publication tree.

## Files now prepared

- `src/m1600_capture_verified.py`: passive source-verified private capture from dedicated AGX eth0. Read-only PF_PACKET, socket-scoped promiscuity, bounded seconds/bytes, source identity from **local-only** `../evidence/M1600_SENSOR_IDENTITY_LOCAL.json` and hashed PCAP receipt. Existing viewer and networking are not changed.
- `src/m1600_test_session.py`: one-command preflight/replay/live 1–3 trial orchestration. Local hashed independent captures → ROI benchmark → objective acceptance JSON. Separate exploratory cross-trial plane-normal/offset repeatability diagnostics.
- `src/full_wall_benchmark.py`: operator ROI selected **before analysis**, robust candidate fit on training scans, evaluation on separate scans **without truncating held-out residuals**. The ROI must exclude other physical surfaces.
- `src/m1600_session_gate.py`: predetermined acceptance checks and honest incomplete status. A pass is NOT instrument absolute range-accuracy certification.
- `src/corner_benchmark.py`: two independently annotated face ROIs, two held-out plane tests and theoretical plane-line intersection. No observed physical edge accuracy yet.
- `src/m1600_offline_qc.py`: 16-channel residual signatures, temporal range repeatability, independent holdout, and conservative depth-edge risk exploration; scanner output unchanged.
- `src/imx252_calibration_offline.py`: OpenCV checkerboard intrinsic fit and held-out corner reprojection on **user-reviewed still images only**, not extrinsic.
- `src/live_ros_rate_probe.py` and `src/host_time_pairing.py`: bounded host-time arrival-rate and nearest stamp pairing observations without image storage. Never infer hardware synchronization.
- `src/camera_lidar_extrinsics_offline.py`: **future** offline 3D LiDAR to native camera 2D matched-point robust PnP candidate solver with disjoint *spatial* train/holdout. Real physical matching, depth/clock truth and extrinsic verification remain blocked. `examples/camera_lidar_correspondence_TEMPLATE.json` has intentionally **zero invented measurements**.
- `tests/test_*.py`: source-free synthetic mathematical and parser fixtures; honest about which checks used real sensor data.
- `examples/full_wall_roi_TEMPLATE.json`: placeholder **NOT operator-verified** until the real wall and correct angular boundaries are established.

## Prepare the first physical wall test

1. Keep the portable camera+LiDAR assembly mechanically rigid. Document
   position, sensor orientation, power/USB/Ethernet routing, any cable strain,
   safety and unambiguous stable sensor identities. Do **not** assume any
   unverified automotive/Technica power/connector pinout or trigger line.
   Keep AGX default Wi-Fi route and portrait HDMI unchanged.
2. Aim the M1600 at a large, matte, largely unobstructed flat wall from a
   safe fixed position. Keep the rig stationary. A known corner can remain
   visible elsewhere, but **exclude it from the plane measurement ROI**.
3. Copy `examples/full_wall_roi_TEMPLATE.json` to a **private** JSON
   inside `../evidence`. Measure/identify azimuth/elevation/range limits
   and edit all ROI bounds so the selected points are from that wall only.
   Set `operator_has_verified_surface: true` only when personally confirmed.
   Put the actual tape-measured geometry, viewpoint and target descriptors
   in an independent hand-written session note; never invent measurement.
4. Run preflight, then exactly three bounded stationary captures. Use existing
   authorized AGX operator account capable of passive eth0 AF_PACKET; do not
   open an extra data network or install a service.

    # From /home/sticker/Waymo_Lidar_Capture/ros_fusion/publication:
    python3 src/m1600_test_session.py preflight \
      --scene wall_operator_labeled \
      --roi-json ../evidence/full_wall_operator_YYYYMMDD.json

    # With the same validated, real selected ROI and authorized capture:
    python3 src/m1600_test_session.py capture \
      --scene wall_operator_labeled \
      --roi-json ../evidence/full_wall_operator_YYYYMMDD.json \
      --seconds 3 --trials 3 --max-mib 24

5. Read private `M1600_SESSION_*_SUMMARY.json` and each geometry/acceptance
   receipt. Note the SHA-256, packet discontinuities, frame completeness,
   ROI support fraction, **untruncated** held-out P50/P90/P95/P99/RMS,
   and pairwise trial plane-normal and offset drift. Don't replace this
   with visually pleasing interpolation in RViz.
6. Predetermined gates: >=1500 validated packets, >=10 frame boundaries,
   no observed sequence discontinuities, no cap hit, expected 180–240 packets
   per complete frame in current 210-packet mode, matching capture hash,
   ROI physically operator-identified as bare wall, at least 5 training
   and 5 held-out scans, >=80% 40mm candidate-plane support in ROI,
   held-out candidate plane P95 <=40mm, both 5th–95th percentile
   in-plane extents >=0.5m. These thresholds are experimental sanity
   checks, not vendor accuracy specifications.
7. If failing, keep all original packets and failures, identify exact
   failed gate. Do **not** tune fitting thresholds against the holdout.
   Fix physical ROI/scene or update the protocol in a new version.

## Subsequent corner test (same rig, after wall)

Manually annotate the two **different visible faces** of a physical corner
in separate private JSON files `corner_a` and `corner_b`, same polar ROI
schema. Capture static genuine packets using the existing bounded passive
script with `--scene corner_operator_labeled`. Then:

    python3 src/corner_benchmark.py --pcap ../evidence/RECORDED.pcap \
      --face-a ../evidence/CORNER_A.json \
      --face-b ../evidence/CORNER_B.json \
      --output ../evidence/CORNER_REPORT.json

The output gives independent face-plane held-out errors and the mathematical
intersection. It cannot certify physical corner position without a measured
physical edge or an independently registered camera/reference.

## Camera later: *after* successful LiDAR-only wall trial

- Keep the monochrome IMX252, its real imaging mode, lens/focus,
  checkerboard true inner-corner count and measured square spacing documented.
  Capture user-reviewed diverse **full-resolution** checkerboard images
  separately from the present 384×288 live RViz preview. Use 10–60 frames,
  avoid blurry/saturated images, vary orientations and image positions.
- Run `src/imx252_calibration_offline.py --images PRIVATE_DIRECTORY
  --inner-cols N --inner-rows N --square-mm MEASURED --output PRIVATE_JSON`.
  It measures intrinsics and held-out reprojection consistency and retains
  only hashes/calibration values; the original image privacy/deletion policy
  remains user-controlled.
- Once real intrinsics and a rigid, stationary shared target are available,
  manually create and *verify* 16+ matched 3D LiDAR XYZ metres/native image
  pixel coordinates using the empty correspondence template. Only then run:

    python3 src/camera_lidar_extrinsics_offline.py \
      --intrinsics ../evidence/CAMERA_INTRINSICS_REAL.json \
      --pairs ../evidence/MEASURED_LIDAR_CAMERA_PAIRS.json \
      --output ../evidence/EXTRINSIC_CANDIDATE.json

  This candidate PnP transform is **not** independent physical truth.
  The current synthetic projection, solve, CLI serialization and held-out
  pixel reprojection were rehearsed and must remain labeled synthetic.
- Do not assert camera-LiDAR extrinsics, time alignment, synchronized
  fusion or mobile results from intrinsic-only or synthetic calibration.
- When motion begins, benchmark native 2048×1536/30 FPS acquisition,
  exposure <=33.3ms (often shorter), fixed 0dB gain where light allows,
  and dropped frames. The current static 5 FPS/200ms setting is **not**
  a valid motion-acquisition setting.
- The present software-stamped ROS topics cannot establish hardware
  time sync or one-to-one sensor correspondences.

## Tests and safe replay (no hardware manipulation)

Run all synthetic regression fixtures locally:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
      python3 -m unittest discover -v -s tests -p 'test_*.py'

To analyze an existing genuine PCAP, start with the private
`uncontrolled_candidate` ROI and the read-only replay mode. Replay deliberately
**does not** claim authenticated new live capture just from a readable PCAP.

    python3 src/m1600_test_session.py replay --scene uncontrolled \
      --pcap ../evidence/EXISTING.pcap \
      --roi-json ../evidence/UNCONTROLLED_ROI.json

A successful real-world rehearsal is **capture → verified packets → sealed
receipt → offline decode → train/holdout numerical report → truthful gate**
without RViz failure or AGX instability. The full-wall target and physical
reference cannot be replaced by simulated data.

## Safety, rollback and publication

- No package installs, kernel/driver changes, clocks, ROS network changes,
  image downloads or large ROS bags required.
- New captures use **eth0 only** and bounded storage. Original recordings
  and previously working scripts remain untouched. RViz remains in its
  existing isolated ROS1 container. New test scripts do not smooth the
  displayed cloud by default.
- Scene identity, PCAPs, live capture receipts, sensor identity JSON, raw
  images and scans **stay private** under the AGX evidence directory, never
  stage or push them to public Git.
- Restore before/after sensor exposure changes by querying the camera
  first; today's camera is at 0dB gain, 5FPS with automatic exposure.
  Nothing here changes that configuration.
- Rollback is simply to stop invoking the new offline scripts; they do
  not install daemons or alter the old live pipeline. Never delete
  independent captures without deliberate user instruction.
- Clearly separate synthetic test passes from full-wall measured passes
  in any LinkedIn/GitHub publication.
