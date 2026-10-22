# LiDAR and camera comparison — bench matrix and safety gates
Date: 2026-10-22 | Scope: user-owned lab equipment; Innoviz remains conditional on trade.

## Evidence status and experiment priority

| Candidate | Current state | What it could contribute | Next non-destructive test |
|---|---|---|---|
| Velarray M1600 | LIVE on AGX HDMI ROS /m1600/points | Short-range mobile baseline; known packet stream | Validate decoded XYZ vs M1600 independent driver and geometry; static plane/noise baseline |
| Hesai QT128C2X | Owned, Ethernet PHY side not yet proven | More vertical channels and comparative geometry | Correct twisted automotive pair + connector/power revision verification before power; measure actual 1000BASE-T1 link, discover packets |
| Waymo Honeycomb/other Waymo unit | Owned, exact unit(s) and firmware to verify | Alternate field of view, density, potentially different noise/coverage | Inventory hardware labels and original harness, SDK ELF architecture and rights; read-only inspection before power |
| Innoviz (exact model unknown) | Trade OFFER, not acquired | Potential alternate solid-state scan/detection pattern | If trade accepted: photograph nameplate, connector, harness and obtain exact documentation; confirm export/use terms; do not preplan pinout |
| Monochrome IMX252 | LIVE, 2048x1536 native, preview 384x288 | Camera edge/contrast and grayscale appearance for calibration | Intrinsic calibration then extrinsic checkerboard/feature target across M1600 |
| PolarSens IMX250 | Owned, not connected in this pipeline | DoLP/AoLP and specular-vs-diffuse measurements | Confirm camera/mount/SDK and polarization orientation calibration; add after geometric baseline |
| Additional cameras | Search/trade candidates, not acquired | Higher pixel resolution / color / improved dynamic range | Evaluate nonredundant experiment and resale liquidity; pixel count alone is not sufficient |

## One-at-a-time integration policy
1. Baseline M1600 and IMX252 first; do not disconnect working sensor until logs and configuration checks pass.
2. Photograph exact model labels and keyed connector front/back for each candidate. No assumed pin ordering.
3. Verify **rated power**, correct return ground, enable/interlock if any, and automotive differential-pair pinout against exact revision before applying power. Never use failed ZUP36-24.
4. Build/verify 1000BASE-T1 twisted pair (controlled impedance), PHY master/slave configuration; RJ45 link alone does not prove remote LiDAR link.
5. Start **passive bounded raw capture** before launch commands or driver experiments. Save SHA256 and network settings snapshot. Avoid active web/API changes until traffic is characterized.
6. Produce authentic PointCloud2 with traceable decoder version; check field units, frame coordinates, calibration tables and per-packet timing.
7. Compare same scene, same measurement conditions, reference planes and held-out positions; account for different FOV and return modes, not just points per second.
8. Run the same RAM/CPU/latency stability measurements with ROS subscribers attached. No multiple publishers for same raw topic.
9. Do not wire multiple automotive power systems to AGX; isolate prototype experiment from critical AGX host networking and default Wi-Fi route.

## QT128 specific stop gates
Previous tests negotiated RJ45 link with the Technica converter but saw no incoming QT128 frames. Previous 10cm **loose hookup wires** are unsuitable as a conclusive 1000BASE-T1 link test. Confirm exact Hesai QT128C2X hardware manual for the sensor's connector and voltage revision; publicly mirrored manuals disagree on allowed power ranges (e.g. 12–24 V vs 12–48 V), so a guessed shared pinout or power setting is forbidden. Previous default 192.168.1.201 and destination broadcast are reference only until real traffic proves actual configuration. No need to change working M1600 setup during documentation.

## Waymo proprietary source gate
Old local Waymo SDK archives may carry proprietary/confidential headers and/or architecture-specific libraries. These are for **private compatibility inspection**, not public upload or unrestricted redistribution. Inspect exact ELF architecture, API license, hardware connector and any ECU dependencies before driver decisions. Any reproducible public test must have an independently shareable implementation.

## Innoviz trade caveat
The Vision Engineering Mantis microscope trade is **pending**. The sensor's model is not yet known. Do not book the Innoviz as owned, infer interface, decide voltage, promise compatibility or ship parts based on an unconfirmed offer. InnovizOne and InnovizTwo are not interchangeable.

## Matched-scene evaluation protocol
- Rigid sensor poses documented with independent measurements.
- Plane targets: floor, matte painted wall, visible corners; additional glass/mirror/metals in controlled scenes.
- Capture within same range bins and compatible FOV/ROI, return mode and illumination.
- Report raw independent returns, density (pts / m^2), per-plane RMS + P95, spatial coverage, frame rate, failures, temperature, latency and CPU/GPU load.
- Separate wall **fit quality** from appearance smoothing. Show live raw and processed simultaneously with matching viewpoint and axis units.
- Hold out at least one dataset per comparison from optimization/tuning. Preserve repeated trials and failure examples.
- Test reflective material false points with IMX250 polarization only after base calibration.
- Archive raw locally. Publish sparse/anonymous sanitized example data only after review.

## Cameras: trade/acquisition screen
- Sensor and optics: exact sensor ID; **global shutter** vs rolling, Mono/Color/PolarSens, quantum efficiency, pixel pitch, SNR/dynamic range, lens projection/distortion.
- Interface: USB3 / GenICam, camera hardware trigger and PTP/clock functionality, Linux ARM64 driver support.
- Performance: demonstrated resolution at required FPS, sustainable link bandwidth and motion blur/exposure at target illumination.
- Nonredundancy: avoid adding yet another IMX252-like camera unless it adds valuable color, polarization, synchronized global shutter, significantly higher resolution/FPS or distinctive wavelength response.
- Ownership: zero discretionary budget; trades/surplus only, verify actual current price and buyer liquidity before recommending trade assets.

## Source trail
https://www.hesaitech.com/product_downloads/qt128/
https://device.report/m/78688fa21c0f1b5372b6ece39f7491c92517cb92b4d325c83b0e4bab5e5deca6
https://innoviz.tech/innoviztwo
Local path: /home/sticker/Waymo_Lidar_Capture/ros_fusion/BAG_OPERATIONS_QT128C2X_M1600.md
