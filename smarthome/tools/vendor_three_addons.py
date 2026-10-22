#!/usr/bin/env python3
"""Tải addon three.js r170 (jsDelivr), duyệt đồ thị import, ghi phẳng vào vendor/.

Chạy lại được: python3 vendor_three_addons.py
"""
import posixpath
import re
import urllib.request
from pathlib import Path

BASE = "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
OUT = Path("/config/www/smarthome/3d/vendor")
ROOTS = ["loaders/GLTFLoader.js", "environments/RoomEnvironment.js",
         "postprocessing/EffectComposer.js", "postprocessing/RenderPass.js",
         "postprocessing/GTAOPass.js", "postprocessing/OutputPass.js"]
IMP = re.compile(r"""(from\s*)(['"])([^'"]+)\2""")


def fetch(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.read().decode()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    seen, todo = set(), list(ROOTS)
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        src = fetch(path)

        def rewrite(m):
            spec = m.group(3)
            if spec == "three":
                new = "./three.module.min.js"
            elif spec.startswith("."):
                target = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
                todo.append(target)
                new = "./" + posixpath.basename(target)
            else:
                return m.group(0)
            return f"{m.group(1)}{m.group(2)}{new}{m.group(2)}"

        (OUT / posixpath.basename(path)).write_text(IMP.sub(rewrite, src))
        print("vendor", path)
    names = [posixpath.basename(p) for p in seen]
    assert len(names) == len(set(names)), "trùng tên file khi làm phẳng"


if __name__ == "__main__":
    main()
