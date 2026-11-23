#!/usr/bin/env python3
"""Terbitkan Simple Guide TA dalam satu perintah.

Alur: build Hugo ke docs/ -> bandingkan hash semua file yang layak push
dengan manifest terakhir (.publish/manifest.json) -> push hanya yang
berubah via ghpat -> simpan manifest baru.

Pakai:
  python3 scripts/publish.py "pesan commit"
  python3 scripts/publish.py --init     # snapshot keadaan sekarang tanpa push

Catatan: file yang DIHAPUS tidak ikut terhapus di repo (ghpat push hanya
menambah/menimpa). Hapus manual lewat web GitHub bila perlu.
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUGO = os.path.expanduser("~/workspace/tools/hugo/hugo")
GHPAT = os.path.expanduser("~/workspace/custom-connectors/custom.github-pat/bin/ghpat")
STATE = os.path.join(ROOT, ".publish")
MANIFEST = os.path.join(STATE, "manifest.json")
SKIP_DIRS = {".publish", "resources", "public", ".git"}


def scan():
    out = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            h = hashlib.sha256()
            with open(full, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            out[rel] = h.hexdigest()
    return out


def main():
    args = sys.argv[1:]
    if "--init" in args:
        os.makedirs(STATE, exist_ok=True)
        json.dump(scan(), open(MANIFEST, "w"), indent=1, sort_keys=True)
        print("Manifest awal disimpan. Tidak ada push.")
        return

    msg = args[0] if args else "Update Simple Guide TA"
    subprocess.run([HUGO, "--gc", "--minify", "-d", "docs"], cwd=ROOT, check=True)

    cur = scan()
    old = {}
    if os.path.exists(MANIFEST):
        old = json.load(open(MANIFEST))
    changed = sorted(p for p, h in cur.items() if old.get(p) != h)
    if not changed:
        print("Tidak ada perubahan. Tidak ada push.")
        return

    paths_file = os.path.join(STATE, "paths.bin")
    os.makedirs(STATE, exist_ok=True)
    with open(paths_file, "wb") as f:
        for p in changed:
            f.write(p.encode() + b"\0")
    print(f"{len(changed)} file berubah, push...")
    subprocess.run(
        [GHPAT, "push", "--owner", "chospace", "--repo", "simple-guide-ta",
         "--message", msg, "--source-dir", ROOT, "--paths-file", paths_file],
        check=True,
    )
    json.dump(cur, open(MANIFEST, "w"), indent=1, sort_keys=True)
    print("Selesai. Manifest diperbarui.")


if __name__ == "__main__":
    main()
