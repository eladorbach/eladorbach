# AGX multimodal mobile 3D reconstruction — publication workspace
**Public-release candidate only. Nothing here is a claim of completed mapping or fusion.**

Our engineering challenge is to produce smooth, accurate, inspectable indoor 3D surfaces from independently verified measurements, while preserving actual edges, detecting reflective/multipath artifacts, and transparently separating measured from inferred geometry.

- [Eight-month 2026 research survey](RESEARCH_20260222_TO_20261022.md)
- [Operator-ready execution and measurement roadmap](EXECUTION_ROADMAP_20261022.md)
- [Next experiment: measured wall, floor and corner](NEXT_WALL_FLOOR_EXPERIMENT.md)
- [Research goals / validity criteria](PROJECT_CHARTER_20261022.md)
- [Side-by-side sensor evaluation and safe bring-up](SENSOR_BENCH_MATRIX_20261022.md)
- [LinkedIn story, figures, measurement tables, and GitHub release gates](PUBLICATION_PLAN_20261022.md)

**Verified baseline:** authentic live M1600 PointCloud2 plus monochrome IMX252 preview on one AGX HDMI RViz session; native IMX250 PolarSens and other LiDARs not yet fused. M1600 packet decoder structure/software math has been cross-checked against 11,752 returns from an immutable real capture. Physical metrological accuracy remains unverified.

**Not built:** calibrated camera-LiDAR fusion, synchronized IMU odometry, mobile SLAM, optical polarization fusion, denser mapped surfaces, Gaussian splatting.

**License/privacy:** This staging folder contains original project planning text only. Never automatically add full source folders, raw PCAPs, camera imagery, passwords, MAC identifiers, private Waymo SDKs or third-party code without confirming publication rights.

**Publication:** This branch is a documentation-only research staging area inside the existing eladorbach/eladorbach repository; it is intentionally separate from the deployed main branch. It does **not** announce a completed fusion system.
