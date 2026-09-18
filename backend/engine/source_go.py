"""Tree-sitter-based Go crypto usage detector.

Phase 7: Deterministic AST pattern matching over Go standard library crypto packages:
crypto/rsa, crypto/ecdsa, crypto/ed25519, crypto/aes, crypto/des, crypto/md5,
crypto/sha1, crypto/sha256, crypto/sha512, golang.org/x/crypto/sha3, crypto/hmac.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tree_sitter
import tree_sitter_go

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection

_QUERY_PATH = Path(__file__).parent / "queries" / "go_crypto.scm"

_LANGUAGE = tree_sitter.Language(tree_sitter_go.language())
_PARSER = tree_sitter.Parser(_LANGUAGE)
_QUERY = tree_sitter.Query(_LANGUAGE, _QUERY_PATH.read_text())

_HASH_PACKAGES: dict[str, Family] = {
    "md5": Family.MD5,
    "sha1": Family.SHA_1,
    "sha224": Family.SHA_2,
    "sha256": Family.SHA_2,
    "sha384": Family.SHA_2,
    "sha512": Family.SHA_2,
    "sha3": Family.SHA_3,
}


def _text(node: tree_sitter.Node) -> str:
    return node.text.decode("utf-8") if node.text else ""


def _positional_args(args_node: tree_sitter.Node) -> list[tree_sitter.Node]:
    return [c for c in args_node.named_children]


def detect_file(path: Path) -> list[Detection]:
    try:
        source = path.read_bytes()
    except OSError:
        return []
    return detect_code(source, str(path))


def detect_code(source: bytes, path: str = "<source>") -> list[Detection]:
    tree = _PARSER.parse(source)
    matches = tree_sitter.QueryCursor(_QUERY).matches(tree.root_node)
    detections: list[Detection] = []
    for _pattern_index, captures in matches:
        detection = _classify(path, captures)
        if detection is not None:
            detections.append(detection)
    return detections


def _classify(path: str, captures: dict[str, list[tree_sitter.Node]]) -> Detection | None:
    call_nodes = captures.get("call.node")
    args_nodes = captures.get("call.args")
    pkg_nodes = captures.get("call.pkg")
    fn_nodes = captures.get("call.fn")

    if not call_nodes or not args_nodes or not pkg_nodes or not fn_nodes:
        return None

    call_node, args_node = call_nodes[0], args_nodes[0]
    pkg, fn = _text(pkg_nodes[0]), _text(fn_nodes[0])
    line = call_node.start_point[0] + 1
    snippet = _text(call_node)[:200]
    common: dict[str, Any] = dict(path=path, line=line, snippet=snippet, source=FindingSource.AST)

    if pkg in _HASH_PACKAGES and fn in ("New", "Sum", "Sum256", "Sum512", "New256", "New512"):
        family = _HASH_PACKAGES[pkg]
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=f"{pkg}.{fn} digest", function=CryptoFunction.DIGEST,
            symbol=f"{pkg}.{fn}", confidence=0.92, **common,
        )

    if pkg == "rsa" and fn == "GenerateKey":
        args = _positional_args(args_node)
        key_size = None
        if len(args) >= 2:
            bits_txt = _text(args[1])
            if bits_txt.isdigit():
                key_size = int(bits_txt)
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.RSA,
            display_name="RSA key generation", function=CryptoFunction.KEYGEN,
            symbol="rsa.GenerateKey", confidence=0.95, key_size=key_size, **common,
        )

    if pkg == "ecdsa" and fn == "GenerateKey":
        args = _positional_args(args_node)
        curve = None
        if len(args) >= 1:
            curve_txt = _text(args[0])
            curve = curve_txt.replace("elliptic.", "").replace("()", "")
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.ECDSA,
            display_name="ECDSA key generation", function=CryptoFunction.KEYGEN,
            symbol="ecdsa.GenerateKey", confidence=0.92, curve=curve, **common,
        )

    if pkg == "ed25519" and fn == "GenerateKey":
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.ED25519,
            display_name="Ed25519 key generation", function=CryptoFunction.KEYGEN,
            symbol="ed25519.GenerateKey", confidence=0.95, **common,
        )

    if pkg == "aes" and fn == "NewCipher":
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.AES,
            display_name="AES block cipher", function=CryptoFunction.ENCRYPT,
            symbol="aes.NewCipher", confidence=0.92, **common,
        )

    if pkg == "des":
        if fn == "NewTripleDESCipher":
            return Detection(
                kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.THREE_DES,
                display_name="3DES cipher", function=CryptoFunction.ENCRYPT,
                symbol="des.NewTripleDESCipher", confidence=0.95, **common,
            )
        if fn == "NewCipher":
            return Detection(
                kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.DES,
                display_name="DES cipher", function=CryptoFunction.ENCRYPT,
                symbol="des.NewCipher", confidence=0.95, **common,
            )

    if pkg == "hmac" and fn == "New":
        args = _positional_args(args_node)
        underlying = None
        if len(args) >= 1:
            h_arg = _text(args[0])
            for h_pkg, fam in _HASH_PACKAGES.items():
                if h_pkg in h_arg:
                    underlying = fam
                    break
        return Detection(
            kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=Family.HMAC,
            display_name="hmac.New message authentication", function=CryptoFunction.TAG,
            symbol="hmac.New", confidence=0.90, underlying_hash_family=underlying, **common,
        )

    return None
