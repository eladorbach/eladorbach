#!/usr/bin/env python3
"""Read-only Velarray M1600 PCAP quality control, not calibrated metrology.

Inputs: genuine recorded packet capture only. No device, ROS, network or camera I/O.
Output: JSON descriptive statistics. No per-point geometry or images persisted.
Only NumPy is required; fixed seeds/holdout splits ensure reproducibility.
"""
import argparse
import hashlib
import json
import math
import pathlib
import struct
import time

import numpy as np

RETURN = np.dtype([("flags_vdfl", ">u2"), ("azm", ">u2"),
                   ("dist", ">u2"), ("reflect", "u1"), ("ring", "u1")])
FRAME_IDS = (15, 20, 25, 30, 35, 40)
ANGULAR_BIN_RAW = 10  # 10 centidegrees = 0.1 degree, not exact same-ray matching
CELLS_PER_RING = 6554
CELLS = 16 * CELLS_PER_RING


def load_pcap_frames(path, source_ip=None, max_records=100000):
    """Conservatively accept Ethernet/IPv4/nonfragmented/UDP port 2368/1304 B."""
    packets, frames, prev = [], [], None
    source_bytes = None if source_ip is None else __import__("socket").inet_aton(source_ip)
    with open(path, "rb") as stream:
        magic = stream.read(4)
        if magic != b"\xd4\xc3\xb2\xa1":
            raise ValueError("expected little-endian microsecond PCAP, Ethernet link type")
        meta = stream.read(20)
        if len(meta) != 20 or struct.unpack_from("<I", meta, 16)[0] != 1:
            raise ValueError("invalid PCAP header or unsupported link type")
        for _ in range(max_records):
            record = stream.read(16)
            if not record:
                break
            if len(record) != 16:
                raise ValueError("truncated PCAP record header")
            _, _, size, _ = struct.unpack("<IIII", record)
            if not 42 <= size <= 65535:
                raise ValueError("invalid or excessive PCAP record size")
            ethernet = stream.read(size)
            if len(ethernet) != size:
                raise ValueError("truncated PCAP record")
            off = 14
            if ethernet[12:14] == b"\x81\x00":
                off = 18
                if ethernet[16:18] != b"\x08\x00":
                    continue
            elif ethernet[12:14] != b"\x08\x00":
                continue
            if len(ethernet) < off + 28:
                continue
            ihl = (ethernet[off] & 15) * 4
            if (ethernet[off] >> 4) != 4 or ihl < 20 or ethernet[off+9] != 17:
                continue
            if struct.unpack_from("!H", ethernet, off+6)[0] & 0x3fff:
                continue
            if source_bytes is not None and ethernet[off+12:off+16] != source_bytes:
                continue
            udp = off + ihl
            if len(ethernet) < udp + 8:
                continue
            source, dest, length = struct.unpack_from("!HHH", ethernet, udp)
            if (source, dest, length) != (2368, 2368, 1312):
                continue
            data = ethernet[udp+8:udp+8+1304]
            if len(data) != 1304:
                continue
            seq = data[-1]
            if prev is not None and seq < prev and packets:
                frames.append(packets)
                packets = []
            prev = seq
            packets.append(data)
        else:
            raise ValueError("max_records reached; set an explicit higher safe bound")
    if packets:
        frames.append(packets)
    return frames


def decode(frame):
    """Return genuine parsed azimuth/range/ring/XYZ/intensity arrays."""
    if not frame:
        raise ValueError("empty frame")
    r = np.frombuffer(b"".join(p[20:1300] for p in frame), dtype=RETURN)
    r = r[(r["dist"] > 0) & (r["ring"] < 16)]
    az = r["azm"].astype(np.float64) * (np.pi / 18000.)
    elev = (r["ring"].astype(np.float64)*2-16)*np.pi/180. + (r["flags_vdfl"] & 0x3fff)*(np.pi/18000.)
    radial = r["dist"].astype(np.float64) * .004
    xy = radial*np.cos(elev)
    xyz = np.column_stack((xy*np.sin(az), xy*np.cos(az), radial*np.sin(elev)))
    return r, xyz


def angular_grid(r, bin_raw=ANGULAR_BIN_RAW):
    """Average range in each scanner channel and coarse azimuth bin.

    This is *not* an exact ray correspondence and can mix depth boundaries.
    """
    if not 1 <= bin_raw <= 100:
        raise ValueError("bin_raw must be 1..100 centidegrees")
    per_ring = (65536 + bin_raw - 1)//bin_raw
    cells = 16*per_ring
    idx = r["ring"].astype(np.int32) * per_ring + r["azm"].astype(np.int32)//bin_raw
    counts = np.bincount(idx, minlength=cells)
    sum_range = np.bincount(idx, weights=r["dist"].astype(np.float64)*.004, minlength=cells)
    out = np.full(cells, np.nan, dtype=np.float64)
    np.divide(sum_range, counts, out=out, where=counts>0)
    return out, counts


def boundary_risk_from_training_grid(grid,bin_raw,depth_jump_m=0.10):
    """Heuristic depth edge risk from ONE training scan only, not a truth mask.

    No cross-channel adjacency, no interpolation of missing cells. A 0.10 m
    neighboring range jump suggests a possible physical depth discontinuity.
    """
    per_ring=(65536+bin_raw-1)//bin_raw
    cells=np.asarray(grid).reshape((16,per_ring))
    left=cells[:,:-1]
    right=cells[:,1:]
    valid=np.isfinite(left)&np.isfinite(right)
    diff=np.zeros_like(left)
    np.subtract(right,left,out=diff,where=valid)
    jump=valid&(np.abs(diff)>depth_jump_m)
    risk=np.zeros(cells.shape,dtype=bool)
    risk[:,:-1]|=jump
    risk[:,1:]|=jump
    return risk.ravel()


def percentile_dict(arr):
    if len(arr) == 0:
        return {"count": 0}
    values = np.percentile(arr, [50, 90, 95, 99])
    return {"count": int(len(arr)), "p50_mm": round(float(values[0]*1000), 3),
            "p90_mm": round(float(values[1]*1000), 3),
            "p95_mm": round(float(values[2]*1000), 3),
            "p99_mm": round(float(values[3]*1000), 3)}


def planar_candidate(points, seed, threshold=0.04, iterations=130):
    """Fit a *candidate* planar patch with 40mm truncation, never truth."""
    rng = np.random.RandomState(seed)
    n = min(len(points), 6000)
    if n < 300:
        return None
    sample = points[rng.choice(len(points), n, replace=False)]
    best = -1
    support = None
    for _ in range(iterations):
        a,b,c = sample[rng.choice(n,3,replace=False)]
        normal = np.cross(b-a,c-a)
        length = np.linalg.norm(normal)
        if length < 1e-8:
            continue
        normal /= length
        good = np.abs((sample-a).dot(normal)) < threshold
        count = np.count_nonzero(good)
        if count > best:
            best = count
            support = sample[good]
    if support is None or len(support) < 200:
        return None
    center = np.mean(support, axis=0)
    _, _, vh = np.linalg.svd(support-center, full_matrices=False)
    normal = vh[-1]
    if normal[0] < 0:
        normal = -normal
    signed = (points-center).dot(normal)
    mask = np.abs(signed) < threshold
    abs_resid = np.abs(signed[mask])
    return {"normal": normal, "signed": signed, "mask": mask,
            "support_pct": round(float(100*mask.mean()), 2),
            "thresholded_rms_mm": round(float(np.sqrt(np.mean(abs_resid**2))*1000),2),
            "thresholded_p95_mm": round(float(np.percentile(abs_resid,95)*1000),2)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pcap", required=True, help="private local 1304-byte M1600 PCAP")
    cli.add_argument("--source-ip", default=None, help="optional capture source selection, not included in report")
    cli.add_argument("--output", default=None, help="private JSON report path")
    cli.add_argument("--bin-centidegrees",type=int,choices=(5,10,20),default=10,
                     help="angular cell width; evaluate 0.05, 0.1, 0.2 deg sensitivity")
    args = cli.parse_args()
    started = time.monotonic()
    p = pathlib.Path(args.pcap)
    sha = hashlib.sha256()
    with open(p, "rb") as f:
        for part in iter(lambda:f.read(1024*1024), b""):
            sha.update(part)
    frames = load_pcap_frames(p, source_ip=args.source_ip)
    if len(frames) < 42:
        raise ValueError("at least 42 complete or partial recorded frames required")
    result = {
        "type": "REAL_PCAP_EXPLORATORY_NOT_GROUND_TRUTH",
        "pcap_sha256": sha.hexdigest(), "source_frames": len(frames),
        "source_packets": sum(map(len,frames)),
        "angular_bin_deg": args.bin_centidegrees*0.01,
        "lidar_range_quantization_mm": 4,
        "sample_frame_ids": list(FRAME_IDS),
        "limitations": [
            "Angular bins do not identify the same physical laser ray or guarantee static scenery.",
            "Independent ground truth, measured surface ROI, extrinsic calibration and clock synchronization unavailable.",
            "Planar candidate selection is conditional on 40mm threshold; NOT wall flatness or sensor accuracy.",
            "Temporal medians are cross-frame prediction candidates, NOT a correction to be published as true geometry.",
            "No raw LiDAR data, photos, or private IPs are emitted."
        ]
    }
    scans = []
    plains = []
    ring_stats = []
    for ix in FRAME_IDS:
        returns,xyz = decode(frames[ix])
        grid,counts = angular_grid(returns,args.bin_centidegrees)
        scans.append(grid)
        model = planar_candidate(xyz,seed=42+ix)
        if model is not None:
            plane = {"frame": ix,"points": len(xyz),
                     "candidate_support_pct": model["support_pct"],
                     "thresholded_rms_mm": model["thresholded_rms_mm"],
                     "thresholded_p95_mm": model["thresholded_p95_mm"],
                     "normal_xyz": np.round(model["normal"], 6).tolist()}
            med = []
            for ch in range(16):
                vals = model["signed"][model["mask"] & (returns["ring"]==ch)]
                med.append(float(np.median(vals)*1000) if len(vals)>=30 else float("nan"))
            ring_stats.append(med)
            plains.append(plane)
    result["plane_candidates"] = plains
    signatures = np.asarray(ring_stats,dtype=float)
    if len(signatures)>1:
        result["ring_median_residual_correlations"] = [
            {"frame_a":plains[i]["frame"],"frame_b":plains[j]["frame"],
             "corr":round(float(np.corrcoef(signatures[i],signatures[j])[0,1]),4)}
            for i in range(len(plains)) for j in range(i+1,len(plains))]
        result["median_ring_residual_mm_by_frame"] = [
            {"frame": plains[i]["frame"],"medians":np.round(signatures[i],2).tolist()}
            for i in range(len(plains))]
    grids = np.asarray(scans)
    # Evaluate consistent angular cells over independent frames; no residual-based inlier filtering.
    complete = np.isfinite(grids).all(axis=0)
    common = grids[:,complete]
    result["all_frames_common_angular_bins"] = int(complete.sum())
    if len(common.T):
        spread = np.std(common, axis=0, ddof=1)
        result["per_cell_temporal_range_std"] = percentile_dict(spread)
        # No tuning on the holdout: first three form predictor; last three evaluate prediction.
        raw = common[0]
        pred = np.median(common[:3],axis=0)
        holdout = np.median(common[3:],axis=0)
        result["heldout_raw_single_frame_absolute_error"] = percentile_dict(np.abs(raw-holdout))
        result["heldout_three_frame_temporal_median_absolute_error"] = percentile_dict(np.abs(pred-holdout))
        edge_flags=boundary_risk_from_training_grid(grids[0],args.bin_centidegrees)[complete]
        result["train_frame_boundary_risk_10cm"]={
            "heuristic":"100mm adjacent angular-cell difference in first training frame; unvalidated depth-edge detector",
            "flagged_cells":int(np.count_nonzero(edge_flags)),
            "other_cells":int(np.count_nonzero(~edge_flags)),
            "flagged_raw_abs_error":percentile_dict(np.abs(raw[edge_flags]-holdout[edge_flags])),
            "flagged_temporal_median_abs_error":percentile_dict(np.abs(pred[edge_flags]-holdout[edge_flags])),
            "other_raw_abs_error":percentile_dict(np.abs(raw[~edge_flags]-holdout[~edge_flags])),
            "other_temporal_median_abs_error":percentile_dict(np.abs(pred[~edge_flags]-holdout[~edge_flags]))}
        result["heldout_diagnostic"] = ("Errors compare observed range by 0.1-degree angular bin "
            "across separate real scans. Lower errors indicate repeatability, not geometric truth. "
            "Boundary mixtures, sample changes, motion, and temporal drift can dominate.")
    result["elapsed_s"] = round(time.monotonic()-started,3)
    report = json.dumps(result,indent=2,allow_nan=False)
    if args.output:
        pathlib.Path(args.output).write_text(report+"\n")
    print(report)


if __name__ == "__main__":
    main()
