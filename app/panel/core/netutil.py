"""网卡枚举：给 OTA 地址选一张对的网卡。

用 ctypes 调 GetAdaptersAddresses（免依赖、免 PowerShell），失败则回退 getaddrinfo。
"""

from __future__ import annotations

import ctypes
import ipaddress
import socket
from ctypes import wintypes

AF_UNSPEC = 0
GAA_FLAG_SKIP_ANYCAST = 0x0002
GAA_FLAG_SKIP_MULTICAST = 0x0004
GAA_FLAG_SKIP_DNS_SERVER = 0x0008
ERROR_BUFFER_OVERFLOW = 111
IF_OPER_STATUS_UP = 1

IF_TYPE_ETHERNET = 6
IF_TYPE_IEEE80211 = 71


class SOCKET_ADDRESS(ctypes.Structure):
    _fields_ = [("lpSockaddr", ctypes.c_void_p), ("iSockaddrLength", ctypes.c_int)]


class IP_ADAPTER_UNICAST_ADDRESS(ctypes.Structure):
    pass


IP_ADAPTER_UNICAST_ADDRESS._fields_ = [
    ("Length", wintypes.ULONG),
    ("Flags", wintypes.DWORD),
    ("Next", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),
    ("Address", SOCKET_ADDRESS),
    ("PrefixOrigin", ctypes.c_int),
    ("SuffixOrigin", ctypes.c_int),
    ("DadState", ctypes.c_int),
    ("ValidLifetime", wintypes.ULONG),
    ("PreferredLifetime", wintypes.ULONG),
    ("LeaseLifetime", wintypes.ULONG),
    ("OnLinkPrefixLength", ctypes.c_ubyte),
]


class IP_ADAPTER_ADDRESSES(ctypes.Structure):
    pass


IP_ADAPTER_ADDRESSES._fields_ = [
    ("Length", wintypes.ULONG),
    ("IfIndex", wintypes.DWORD),
    ("Next", ctypes.POINTER(IP_ADAPTER_ADDRESSES)),
    ("AdapterName", ctypes.c_char_p),
    ("FirstUnicastAddress", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),
    ("FirstAnycastAddress", ctypes.c_void_p),
    ("FirstMulticastAddress", ctypes.c_void_p),
    ("FirstDnsServerAddress", ctypes.c_void_p),
    ("DnsSuffix", ctypes.c_wchar_p),
    ("Description", ctypes.c_wchar_p),
    ("FriendlyName", ctypes.c_wchar_p),
    ("PhysicalAddress", ctypes.c_ubyte * 8),
    ("PhysicalAddressLength", wintypes.ULONG),
    ("Flags", wintypes.ULONG),
    ("Mtu", wintypes.ULONG),
    ("IfType", wintypes.ULONG),
    ("OperStatus", ctypes.c_int),
    ("Ipv6IfIndex", wintypes.ULONG),
    ("ZoneIndices", wintypes.ULONG * 16),
    ("FirstPrefix", ctypes.c_void_p),
    ("TransmitLinkSpeed", ctypes.c_ulonglong),
    ("ReceiveLinkSpeed", ctypes.c_ulonglong),
]


def _sockaddr_to_ip(addr: SOCKET_ADDRESS) -> str | None:
    if not addr.lpSockaddr or not addr.iSockaddrLength:
        return None
    raw = ctypes.string_at(addr.lpSockaddr, addr.iSockaddrLength)
    if len(raw) < 8:
        return None
    family = int.from_bytes(raw[0:2], "little")
    if family != socket.AF_INET:
        return None
    return socket.inet_ntoa(raw[4:8])


def _virtual(name: str) -> bool:
    low = (name or "").lower()
    markers = (
        "vethernet",
        "vmware",
        "virtualbox",
        "hyper-v",
        "loopback",
        "tap",
        "tun",
        "wsl",
        "docker",
        "vpn",
        "zerotier",
        "tailscale",
    )
    return any(m in low for m in markers)


def _score(if_type: int, ip: str, name: str) -> int:
    try:
        addr = ipaddress.IPv4Address(ip)
    except Exception:
        return 0
    score = 0
    if addr.is_private:
        score += 40
    if str(addr).startswith("192.168."):
        score += 25
    elif str(addr).startswith("10."):
        score += 18
    else:
        score += 8
    if if_type == IF_TYPE_IEEE80211:
        score += 30
    elif if_type == IF_TYPE_ETHERNET:
        score += 26
    if _virtual(name):
        score -= 60
    return score


def adapters() -> list[dict]:
    items: list[dict] = []
    try:
        size = wintypes.ULONG(15000)
        flags = GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST | GAA_FLAG_SKIP_DNS_SERVER
        buf = ctypes.create_string_buffer(size.value)
        ret = ctypes.windll.iphlpapi.GetAdaptersAddresses(
            AF_UNSPEC, flags, None, buf, ctypes.byref(size)
        )
        if ret == ERROR_BUFFER_OVERFLOW:
            buf = ctypes.create_string_buffer(size.value)
            ret = ctypes.windll.iphlpapi.GetAdaptersAddresses(
                AF_UNSPEC, flags, None, buf, ctypes.byref(size)
            )
        if ret != 0:
            raise OSError(ret)
        ptr = ctypes.cast(buf, ctypes.POINTER(IP_ADAPTER_ADDRESSES))
        while ptr:
            row = ptr.contents
            if row.OperStatus == IF_OPER_STATUS_UP:
                name = row.FriendlyName or row.Description or ""
                node = row.FirstUnicastAddress
                while node:
                    ip = _sockaddr_to_ip(node.contents.Address)
                    if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                        items.append(
                            {
                                "ip": ip,
                                "name": name,
                                "type": "wifi"
                                if row.IfType == IF_TYPE_IEEE80211
                                else "ethernet"
                                if row.IfType == IF_TYPE_ETHERNET
                                else "other",
                                "virtual": _virtual(name),
                                "score": _score(row.IfType, ip, name),
                            }
                        )
                    node = node.contents.Next
            ptr = row.Next
    except Exception:
        items = _fallback()

    seen = set()
    unique = []
    for item in sorted(items, key=lambda x: x.get("score", 0), reverse=True):
        if item["ip"] in seen:
            continue
        seen.add(item["ip"])
        item.pop("score", None)
        unique.append(item)
    if unique:
        unique[0]["recommended"] = True
    return unique


def _fallback() -> list[dict]:
    out = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127.") or ip.startswith("169.254."):
                continue
            out.append(
                {
                    "ip": ip,
                    "name": "本机网卡",
                    "type": "other",
                    "virtual": False,
                    "score": _score(0, ip, ""),
                }
            )
    except Exception:
        pass
    return out
