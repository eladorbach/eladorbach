# Public story and GitHub release gates — NOT YET PUBLISHED
Updated 2026-10-22 | Project: AGX multimodal 3D reconstruction.

## Positioning for serious robotics / perception audiences
Core question: "**Can we make LiDAR maps cleaner without hiding the measurement errors—and can polarization tell us when seemingly clean geometry is actually false?**"
Demonstrate the answer with the user-owned Jetson AGX Xavier, Velarray M1600, global-shutter monochrome IMX252, and IMX250 PolarSens, followed by fair comparison against other verified sensors.

## LinkedIn demonstration storyboard (capture footage from real experiments, not renders of predicted results)
1. Cold open, 3–5 seconds: **unchanged raw** M1600 cloud. Clearly label every 3D return measured.
2. Same camera/viewpoint, 3–5 seconds: multiview registered cloud. Overprint number of independently measured viewpoints and pose source, not made-up 'resolution increase'.
3. Split raw-versus-reconstruction: fitted wall/floor thickness P95 and held-out plane RMS, alongside visible corner/edge fidelity; use actual measured numbers.
4. Move rig around the scene, revisit initial viewpoint: live incremental map growth and loop closure error overlay.
5. Controlled reflective-surface test: glass/mirror with raw LiDAR artifacts; adjacent monochrome image and PolarSens AoLP/DoLP, then a confidence heatmap, with false-positive and false-negative counts.
6. Optional final Gaussian/mesh render: explicitly label **geometry-derived / learned/inferred** surfaces and retain raw XYZ toggle.
7. Final slide: exact tested sensor models, rates, AGX Xavier CPU/GPU/memory, dataset sizes and code link.
Avoid before/after changes in camera viewpoint, zoom, distance clipping, point size or colormap.

## Public scientific scorecard
- Point-to-plane residuals: RMSE, median absolute, 95th percentile.
- Edge preservation: corner displacement vs baseline/independent marker.
- Map completeness and density from independent observations and distinct viewpoints.
- Frame and packet drops, clock jitter, track consistency, pose drift and loop closures.
- Real processing and rendering latency, CPU/GPU/RAM peak, end-to-end rate.
- Glass/mirror trial: phantom-object rate, missed-real-surface rate, false rejected valid points.
- Polarization ablation: LiDAR alone vs +mono vs +polarization, with repeat trials and held-out scenes.
- Uncertainty: mark interpolated/inferred regions and unresolved/missing geometry.

## GitHub repository structure for eventual publication
README.md                      # research question, verified status, demo and limitations
LICENSE                        # only code we own and are permitted to release
docs/EXPERIMENT_PROTOCOL.md    # camera/lidar setup, precision, reproducibility
docs/CALIBRATION.md            # coordinate frames, camera matrices, timestamps
docs/REPRODUCTION.md           # supported dependencies, pinned versions, exact commands
benchmarks/                    # anonymized CSV, scripts, held-out raw-to-processed metrics
src/                           # audited shareable capture/fusion code; no vendor SDK copies
assets/                        # sanitized small videos/screenshots with rights/privacy checked
references.md                  # bibliographic links / original paper citations only
Do NOT upload private PCAPs, room photos or video with private content, MAC addresses/serials, or old Waymo/Innoviz proprietary SDK binaries. Third-party sources must be cited, not silently re-licensed.

## GitHub release stages
G0: Local documents and reproducibility manifest prepared. No remote publication.
G1: Source code reviewed for IP/privacy/credentials; license and provenance checks.
G2: Independent smoke + regression test, pinned dependencies, AGX/ROS version, no hidden model assets.
G3: Measurements repeatable in >1 run and visual labels accurate. Raw vs processed data traceable.
G4: Curated small sample public dataset scrubbed; full raw archives remain local.
G5: Publish public repository and LinkedIn post once claims are experimentally supported.

## Avoid premature claims
DO NOT claim: 'sub-mm walls', 'working SLAM', 'super-resolution LiDAR', 'merged camera-LiDAR texture', 'PolarSens mirror detection', 'running ROS2 iG-LIO', 'Gaussian splatting', 'all sensors supported', unless that exact artifact exists and is independently checked.
CAN claim today: M1600 authentic live 3D cloud in ROS1 RViz; monochrome IMX252 real preview on same HDMI monitor; USB/GenICam and LiDAR packet capture working; basic FPS/CPU benchmarks; data remains unfused and uncalibrated.

## Suggested visual presentation
Same scene, same projection, synchronized side-by-side video:
**RAW → REGISTERED → CONFIDENCE-GATED → OPTIONAL RENDERED**
Add small overlaid numbers for plane RMS, P95, retained edges, coverage and point counts. Put a red outline around inferred or discarded points so mistakes are transparent.
Extra novelty: polarization-guided reflection stress test + comparative M1600/QT128/Waymo/(confirmed Innoviz) at matched range/FOV if equipment is legally usable.

## Publishing status
As of original draft: local only. AGX Git authenticated fetch and push --dry-run have since been verified against eladorbach/eladorbach. The documentation-only research branch is the intended temporary staging destination; it must not modify the deployed main branch. A dedicated standalone project repository remains a future release option. LinkedIn publication remains gated on measured results.
