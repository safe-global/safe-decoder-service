import hashlib
import json


def get_md5_abi_hash(abi: list[dict] | dict) -> bytes:
    json_str = json.dumps(abi, sort_keys=True)
    md5_hash = hashlib.md5(json_str.encode("utf-8")).hexdigest()
    abi_hash = md5_hash[-8:]
    return bytes.fromhex(abi_hash)
