#!/usr/bin/env python3
"""Short, bounded and strictly passive M1600 packet capture; separate from RViz.

Creates one source-filtered PCAP plus JSON receipt in the private AGX evidence
directory. No LiDAR commands, host NIC configuration, image capture, or replay.
Only the dedicated eth0 interface is opened. AF_PACKET PROMISC is socket-scoped.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import pathlib
import socket
import struct
import time

ROOT = pathlib.Path("/home/sticker/Waymo_Lidar_Capture/ros_fusion/evidence")
DEFAULT_IDENTITY_JSON = ROOT/"M1600_SENSOR_IDENTITY_LOCAL.json"
RAW_PACKET_BYTES = 1304
PCAP_HDR = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)


def load_identity(path=DEFAULT_IDENTITY_JSON):
    """Load local-only physical sensor identifiers (never embed them in public source)."""
    identity=json.loads(pathlib.Path(path).read_text())
    mac=bytes.fromhex(identity["source_mac"].replace(":","").replace("-",""))
    if len(mac)!=6:raise ValueError("source MAC must be 6 bytes")
    return {"src_mac":mac, "src_ip":socket.inet_aton(identity["source_ip"]),
            "dst_ip":socket.inet_aton(identity["destination_ip"])}


def verify_packet(ethernet, identity):
    """Return validated sequence number or None. No side effects."""
    if len(ethernet) < 14+20+8+RAW_PACKET_BYTES:
        return None
    if ethernet[6:12] != identity["src_mac"]:
        return None
    if ethernet[12:14] == b"\x08\x00":
        ip = 14
    elif ethernet[12:14] == b"\x81\x00" and ethernet[16:18] == b"\x08\x00":
        ip = 18
    else:
        return None
    if ethernet[ip] >> 4 != 4:
        return None
    ihl = (ethernet[ip] & 0x0f)*4
    if ihl < 20 or len(ethernet) < ip+ihl+8+RAW_PACKET_BYTES:
        return None
    if ethernet[ip+9] != 17 or struct.unpack_from("!H",ethernet,ip+6)[0] & 0x3fff:
        return None
    if ethernet[ip+12:ip+16] != identity["src_ip"] or ethernet[ip+16:ip+20] != identity["dst_ip"]:
        return None
    udp = ip+ihl
    if struct.unpack_from("!HHH",ethernet,udp) != (2368,2368,1312):
        return None
    if len(ethernet) < udp+8+RAW_PACKET_BYTES:
        return None
    return ethernet[udp+8+RAW_PACKET_BYTES-1]


def bounded_capture(seconds, max_mib, scene_label, interface="eth0", output_root=ROOT,
                    identity_path=DEFAULT_IDENTITY_JSON):
    """Return receipt; file write is capped and new files are exclusive."""
    if interface != "eth0":
        raise ValueError("Only dedicated LiDAR eth0 permitted")
    if not (1 <= seconds <= 20 and 4 <= max_mib <= 64):
        raise ValueError("Seconds 1..20, max MiB 4..64")
    if scene_label not in ("uncontrolled", "wall_operator_labeled", "corner_operator_labeled"):
        raise ValueError("scene must be explicitly labeled; no automatic wall certification")
    if output_root.resolve() != ROOT.resolve() or output_root.is_symlink():
        raise ValueError("private evidence path must remain unchanged")
    identity_path=pathlib.Path(identity_path)
    if identity_path.resolve() != DEFAULT_IDENTITY_JSON.resolve() or identity_path.is_symlink():
        raise ValueError("identity must be the local-only verified sensor identity")
    identity=load_identity(identity_path)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"M1600_BOUNDED_{scene_label}_{stamp}"
    pcap = output_root/(name+".pcap")
    receipt_path = output_root/(name+".json")
    os.umask(0o077)
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    try:
        s.bind((interface,0))
        s.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b"eth0\0")
        idx = socket.if_nametoindex(interface)
        member = struct.pack("IHH8s", idx, 1, 0, b"\0"*8)
        s.setsockopt(263,1,member) # SOL_PACKET/PACKET_ADD_MEMBERSHIP, MR_PROMISC, socket-scoped
        s.settimeout(0.25)
        totals = collections.Counter()
        nbytes = len(PCAP_HDR)
        previous = None
        frame_packets = 0
        frame_packet_counts = []
        first_timestamp = None
        last_timestamp = None
        start = time.monotonic()
        cap = max_mib*1024*1024
        sha = hashlib.sha256()
        fd = os.open(str(pcap),os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,"wb",buffering=1024*1024) as stream:
                stream.write(PCAP_HDR)
                sha.update(PCAP_HDR)
                while time.monotonic()-start < seconds:
                    try:
                        data,addr=s.recvfrom(65535)
                    except socket.timeout:
                        continue
                    if addr[0]!=interface:
                        continue
                    seq=verify_packet(data,identity)
                    if seq is None:
                        totals["filtered_other"]+=1
                        continue
                    if nbytes+len(data)+16>cap:
                        totals["size_limit_hit"]+=1
                        break
                    if previous is not None and seq < previous:
                        frame_packet_counts.append(frame_packets)
                        frame_packets=0
                    elif previous is not None and seq != previous+1:
                        totals["sequence_discontinuities"]+=1
                    if seq==previous:
                        totals["duplicate_adjacent_sequences"]+=1
                    previous=seq
                    frame_packets+=1
                    now_ns=time.time_ns()
                    first_timestamp=now_ns if first_timestamp is None else first_timestamp
                    last_timestamp=now_ns
                    ts_sec=now_ns//10**9
                    ts_us=(now_ns%10**9)//1000
                    record=struct.pack("<IIII",ts_sec,ts_us,len(data),len(data))+data
                    stream.write(record)
                    sha.update(record)
                    totals["verified_packets"]+=1
                    nbytes+=len(record)
            if frame_packets:
                frame_packet_counts.append(frame_packets)
        except Exception:
            # Preserve partial evidence on failure for forensic inspection, never overwrite.
            raise
        elapsed=time.monotonic()-start
    finally:
        s.close()
    if totals["verified_packets"]==0:
        raise RuntimeError("no verified M1600 packets: incomplete PCAP retained privately for inspection")
    complete = frame_packet_counts[1:-1]
    report={
        "schema":"m1600-passive-session/1",
        "capture_utc":stamp,
        "scene_operator_label":scene_label,
        "physical_truth_verified":False,
        "scanner_interface":"eth0",
        "captured_source":"verified_private_identity_UDP_2368_1304byte",
        "identity_config_sha256":hashlib.sha256(identity_path.read_bytes()).hexdigest(),
        "duration_elapsed_s":round(elapsed,4),
        "requested_duration_s":seconds,
        "pcap_path_local_only":str(pcap),
        "pcap_size_bytes":nbytes,
        "pcap_sha256":sha.hexdigest(),
        "verified_packets":totals["verified_packets"],
        "verified_packet_rate_hz":round(totals["verified_packets"]/max(elapsed,1e-5),1),
        "frame_boundaries_observed":max(0,len(frame_packet_counts)-1),
        "complete_interior_frame_packet_count_min":min(complete) if complete else None,
        "complete_interior_frame_packet_count_max":max(complete) if complete else None,
        "complete_interior_frame_packet_count_median":float(sorted(complete)[len(complete)//2]) if complete else None,
        "sequence_discontinuities":totals["sequence_discontinuities"],
        "duplicate_adjacent_sequences":totals["duplicate_adjacent_sequences"],
        "size_limit_hit":bool(totals["size_limit_hit"]),
        "timestamp_first_host_unix_ns":first_timestamp,
        "timestamp_last_host_unix_ns":last_timestamp,
        "timestamp_warning":"host reception time only, not PTP/GPS sensor timestamp",
        "visibility":"PRIVATE",
        "note":"Parallel receive preserves existing RViz source; no full-wall geometry claim."
    }
    fd=os.open(str(receipt_path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"w") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    if os.geteuid()==0:
        os.chown(str(pcap),1000,1000)
        os.chown(str(receipt_path),1000,1000)
    return report


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--seconds",type=int,default=3)
    cli.add_argument("--max-mib",type=int,default=24)
    cli.add_argument("--scene",choices=("uncontrolled","wall_operator_labeled","corner_operator_labeled"),default="uncontrolled")
    a=cli.parse_args()
    r=bounded_capture(a.seconds,a.max_mib,a.scene)
    print(json.dumps(r,indent=2))


if __name__=="__main__":
    main()
