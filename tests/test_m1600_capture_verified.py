#!/usr/bin/env python3
"""Pure parsing tests; synthetic Ethernet frames never sent to a sensor."""
import importlib.util
import pathlib
import struct
import socket
import unittest

HERE=pathlib.Path(__file__).resolve().parents[1]/"src"/"m1600_capture_verified.py"
s=importlib.util.spec_from_file_location("verified_cap",HERE)
c=importlib.util.module_from_spec(s)
s.loader.exec_module(c)


FAKE={"src_mac":bytes.fromhex("020000000001"),"src_ip":socket.inet_aton("192.0.2.10"),"dst_ip":socket.inet_aton("192.0.2.20")}


def frame(seq=123,mac=None,src=None,dst=None,src_port=2368):
    p=bytearray(14+20+8+1304)
    p[6:12] = mac or FAKE["src_mac"]
    p[12:14] = b"\x08\x00"
    p[14] = 0x45
    p[14+9] = 17
    p[14+12:14+16] = src or FAKE["src_ip"]
    p[14+16:14+20] = dst or FAKE["dst_ip"]
    struct.pack_into("!HHHH",p,34,src_port,2368,1312,0)
    p[-1]=seq
    return bytes(p)


class VerifiedCaptureTest(unittest.TestCase):
    def test_valid_source(self):
        self.assertEqual(c.verify_packet(frame(seq=250),FAKE),250)
        self.assertEqual(c.verify_packet(frame(seq=0),FAKE),0)

    def test_reject_incorrect_lidar_or_packet(self):
        self.assertIsNone(c.verify_packet(frame(mac=bytes(6)),FAKE))
        self.assertIsNone(c.verify_packet(frame(src=bytes((1,2,3,4))),FAKE))
        self.assertIsNone(c.verify_packet(frame(dst=bytes((1,2,3,4))),FAKE))
        self.assertIsNone(c.verify_packet(frame(src_port=9999),FAKE))
        self.assertIsNone(c.verify_packet(frame()[:-30],FAKE))
        p=bytearray(frame());p[12:14]=bytes((0x08,0x06))
        self.assertIsNone(c.verify_packet(p,FAKE))

    def test_capture_guard_before_socket(self):
        for seconds,max_mib,scene in ((0,24,"uncontrolled"),(1,0,"uncontrolled"),
                                       (1,24,"unknown_scene"),(21,24,"uncontrolled")):
            with self.assertRaises(ValueError):
                c.bounded_capture(seconds,max_mib,scene)


if __name__=="__main__":
    unittest.main()
