import hashlib, pathlib, sys

OLD = pathlib.Path(r"D:\AI\xiaozhi-server-dsh\xiaozhi-oneclick\xiaozhi-esp32-server-0.9.8\xiaozhi-esp32-server-0.9.8")
NEW = pathlib.Path(r"D:\AI\xiaozhi-server-dsh\xiaozhi-oneclick\runtime")

def digest(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("data/") or "__pycache__" in rel:
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def main():
    for name, old_dir, new_dir in (
        ("xiaozhi-server", OLD / "xiaozhi-server", NEW / "server098"),
        ("xiaozhi-mqtt-gateway", OLD / "xiaozhi-mqtt-gateway", NEW / "mqtt-gateway"),
    ):
        a = digest(old_dir); b = digest(new_dir)
        only_a = sorted(set(a) - set(b)); only_b = sorted(set(b) - set(a))
        diff = [k for k in a if k in b and a[k] != b[k]]
        print(f"== {name}: 原版 {len(a)} 文件, 包内 {len(b)} 文件")
        print("  仅原版:", only_a[:10], "..." if len(only_a) > 10 else "")
        print("  仅包内:", only_b[:10], "..." if len(only_b) > 10 else "")
        print("  内容不同:", diff[:10], "..." if len(diff) > 10 else "")
    return 0

if __name__ == "__main__":
    sys.exit(main())
