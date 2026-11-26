"""Fetch a fixed official axe-core release, with npm integrity verification."""
from pathlib import Path
import base64
import hashlib
import io
import json
import tarfile

VERSION = "4.10.3"
REGISTRY = f"https://registry.npmjs.org/axe-core/{VERSION}"
TARBALL = f"https://registry.npmjs.org/axe-core/-/axe-core-{VERSION}.tgz"
CACHE = Path(__file__).resolve().parent / "vendor" / VERSION


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_archive(archive, integrity):
    if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
        raise ValueError("Expected npm SHA-512 integrity metadata")
    expected = integrity.split("-", 1)[1]
    actual = base64.b64encode(hashlib.sha512(archive).digest()).decode("ascii")
    if expected != actual:
        raise ValueError("axe-core npm archive integrity mismatch")


def extract_asset(archive):
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        # Do not extract paths from the tarball onto the filesystem.
        member = tar.getmember("package/axe.min.js")
        if not member.isfile() or not 100_000 <= member.size <= 10_000_000:
            raise ValueError("Unexpected axe.min.js archive member")
        script = tar.extractfile(member).read()
        manifest = json.loads(tar.extractfile("package/package.json").read())
        if manifest.get("name") != "axe-core" or manifest.get("version") != VERSION:
            raise ValueError("Unexpected npm package or version")
        license_member = tar.extractfile("package/LICENSE")
        return script, license_member.read() if license_member else b""


def load_asset(path=None, cache=CACHE):
    if path:
        data = Path(path).read_bytes()
        if not 100_000 <= len(data) <= 10_000_000:
            raise ValueError("--axe-js must point to an official axe.min.js file")
        return data.decode("utf-8"), sha256(data), "user-supplied local asset"
    cache = Path(cache)
    script_path = cache / "axe.min.js"
    info_path = cache / "asset.json"
    if script_path.is_file() and info_path.is_file():
        data = script_path.read_bytes()
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if info.get("version") != VERSION or info.get("sha256") != sha256(data):
            raise ValueError("Cached axe-core integrity mismatch; remove vendor cache and retry")
        return data.decode("utf-8"), sha256(data), "verified local cache"
    import requests
    print(f"Downloading official axe-core {VERSION} from npm (first run only)...", flush=True)
    meta_response = requests.get(REGISTRY, timeout=(10, 30))
    meta_response.raise_for_status()
    meta = meta_response.json()
    if meta.get("version") != VERSION or meta.get("dist", {}).get("tarball") != TARBALL:
        raise ValueError("Unexpected npm metadata")
    response = requests.get(TARBALL, timeout=(10, 60))
    response.raise_for_status()
    verify_archive(response.content, meta["dist"].get("integrity"))
    script, license_data = extract_asset(response.content)
    cache.mkdir(parents=True, exist_ok=True)
    script_path.write_bytes(script)
    (cache / "LICENSE").write_bytes(license_data)
    info_path.write_text(json.dumps({"version": VERSION, "sha256": sha256(script),
                                    "npm_integrity": meta["dist"]["integrity"]}, indent=2), encoding="utf-8")
    return script.decode("utf-8"), sha256(script), "official npm release"
