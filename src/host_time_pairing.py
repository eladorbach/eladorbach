#!/usr/bin/env python3
"""Pure nearest software-host timestamp diagnostics; NOT sensor synchronization."""
def host_stamp_pairing(lidar, camera):
    """Diagnostic nearest host-stamp pairing, never hardware synchronization."""
    import numpy as np
    if len(lidar)<2 or len(camera)<2:
        return {"lidar_scans_compared":0,"reason":"not_enough_messages"}
    ls=np.sort(np.asarray([row[1] for row in lidar],dtype=float))
    cs=np.sort(np.asarray([row[1] for row in camera],dtype=float))
    overlap=ls[(ls>=cs[0])&(ls<=cs[-1])]
    if len(overlap)==0:
        return {"lidar_scans_compared":0,"reason":"no_host_time_overlap"}
    pos=np.searchsorted(cs,overlap)
    left=cs[np.clip(pos-1,0,len(cs)-1)]-overlap
    right=cs[np.clip(pos,0,len(cs)-1)]-overlap
    nearest=np.where(np.abs(left)<=np.abs(right),left,right)
    absolute=np.abs(nearest)*1000
    return {"lidar_scans_compared":len(overlap),
        "lidar_scans_outside_preview_time_range":int(len(ls)-len(overlap)),
        "nearest_camera_stamp_absolute_ms_p50":round(float(np.percentile(absolute,50)),2),
        "nearest_camera_stamp_absolute_ms_p95":round(float(np.percentile(absolute,95)),2),
        "nearest_camera_minus_lidar_stamp_signed_ms_median":round(float(np.median(nearest)*1000),2),
        "meaning":"host software-stamp proximity only; NOT sensor exposure/pulse synchronization"}
