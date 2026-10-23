#!/usr/bin/env python3
"""Read-only live ROS1 subscriber rate/shape probe, no camera image storage.

Use inside existing isolated ROS Noetic container. Subscribes 4-10 seconds.
Message stamps are ROS/host time, NOT synchronized sensor hardware stamps.
"""
import argparse
import json
import threading
import time

import rospy
from sensor_msgs.msg import Image, PointCloud2


def stats(entries):
    if not entries:
        return {"messages":0}
    import numpy as np
    arrival = np.asarray([x[0] for x in entries], dtype=float)
    source = np.asarray([x[1] for x in entries], dtype=float)
    count = np.asarray([x[2] for x in entries], dtype=float)
    result = {"messages":len(entries),
              "observed_avg_frame_payload_items":round(float(np.mean(count)),2)}
    if len(arrival)>1:
        d=np.diff(arrival)
        good=d[d>0]
        if len(good):
            result.update({"interarrival_median_ms":round(float(np.median(good)*1000),2),
                           "interarrival_p95_ms":round(float(np.percentile(good,95)*1000),2),
                           "arrival_rate_hz":round(float((len(arrival)-1)/(arrival[-1]-arrival[0])),2)})
    # ROS header stamp uses host time; do not interpret difference as hardware latency.
    result["ros_host_stamp_minus_arrival_median_ms"]=round(float(np.median((source-arrival)*1000)),2)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--duration",type=float,default=5.)
    a=p.parse_args()
    if not 2<=a.duration<=15:
        raise ValueError("bounded live probe duration 2..15 seconds")
    rospy.init_node("readonly_m1600_imx252_rate_probe",anonymous=True,disable_signals=True)
    mutex=threading.Lock()
    lidar=[]
    camera=[]
    def on_lidar(msg):
        with mutex:
            lidar.append((time.time(),msg.header.stamp.to_sec(),msg.width*msg.height))
    def on_cam(msg):
        with mutex:
            # Do not view or store image pixels; only metadata.
            camera.append((time.time(),msg.header.stamp.to_sec(),msg.width*msg.height))
    subscribers=[
        rospy.Subscriber("/m1600/points",PointCloud2,on_lidar,queue_size=1,buff_size=2*1024*1024),
        rospy.Subscriber("/imx252/image_preview",Image,on_cam,queue_size=1,buff_size=1024*1024)]
    start=time.monotonic()
    try:
        while time.monotonic()-start<a.duration:
            if rospy.is_shutdown():break
            time.sleep(.05)
    finally:
        for s in subscribers:s.unregister()
    with mutex:
        result={"status":"LIVE_ROS1_HOST_TIMING_PROBE_NOT_HARDWARE_SYNC",
                "duration_target_seconds":a.duration,
                "lidar":stats(lidar),"monochrome_preview":stats(camera),
                "limitations":["No image pixels saved, no raw packet captures saved",
                    "ROS header timestamps are host/source software stamps, not sensor time.",
                    "Arrival intervals are affected by ROS/container scheduling and subscriber jitter.",
                    "Camera preview FPS is not native acquisition FPS; downsampling must be identified separately."]}
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
