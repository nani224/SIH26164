"""Tree-sitter-based Go crypto usage detector.

Phase 7: Deterministic AST pattern matching over Go standard library crypto packages:
crypto/rsa, crypto/ecdsa, crypto/ed25519, crypto/aes, crypto/des, crypto/md5,
crypto/sha1, crypto/sha256, crypto/sha512, golang.org/x/crypto/sha3, crypto/hmac.

M6 (Track CC): also detects a `pkg.Func` reference passed as a bare
*value* rather than called -- Go's registry/callback idiom, e.g.
`hashFunc: sha256.New,` (struct field) or `s.BlockFunc(aes.NewCipher)`
(function argument). The referenced function's own role is the usage's
role (same principle as calling it), so bare references share the exact
same pkg/fn -> family/function table as real calls via `_resolve_pkg_fn`;
they just can't also report argument-derived extras (key_size, curve,
underlying hash) since there's no call to read arguments from.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import tree_sitter
import tree_sitter_go

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection, Span

_QUERY_PATH = Path(__file__).parent / "queries" / "go_crypto.scm"

_LANGUAGE = tree_sitter.Language(tree_sitter_go.language())
_PARSER = tree_sitter.Parser(_LANGUAGE)
_QUERY = tree_sitter.Query(_LANGUAGE, _QUERY_PATH.read_text())

# Pkg/fn pairs whose underlying cryptographic family is a hash -- used
# both to map calls directly and to identify the hash constructor passed
# to hmac.New(hashFunc, key).
_HASH_PACKAGES: dict[str, Family] = {
    "md5": Family.MD5,
    "sha1": Family.SHA_1,
    "sha256": Family.SHA_2,
    "sha512": Family.SHA_2,
    "sha3": Family.SHA_3,
}


def _resolve_pkg_fn(
    pkg: str, fn: str
) -> tuple[FindingKind, Family, CryptoFunction, str, str, float] | None:
    if pkg in _HASH_PACKAGES and fn == "New":
        family = _HASH_PACKAGES[pkg]
        return (
            FindingKind.ALGORITHM, family, CryptoFunction.DIGEST,
            f"{pkg}.New digest", f"{pkg}.New", 0.9,
        )
    if pkg == "md5" and fn == "Sum":
        return (
            FindingKind.ALGORITHM, Family.MD5, CryptoFunction.DIGEST,
            "md5.Sum digest", "md5.Sum", 0.9,
        )
    if pkg == "sha1" and fn == "Sum":
        return (
            FindingKind.ALGORITHM, Family.SHA_1, CryptoFunction.DIGEST,
            "sha1.Sum digest", "sha1.Sum", 0.9,
        )
    if pkg == "sha256" and fn in ("Sum256", "Sum224"):
        return (
            FindingKind.ALGORITHM, Family.SHA_2, CryptoFunction.DIGEST,
            f"sha256.{fn} digest", f"sha256.{fn}", 0.9,
        )
    if pkg == "sha512" and fn in ("Sum512", "Sum384", "Sum512_224", "Sum512_256"):
        return (
            FindingKind.ALGORITHM, Family.SHA_2, CryptoFunction.DIGEST,
            f"sha512.{fn} digest", f"sha512.{fn}", 0.9,
        )
    if pkg == "rsa" and fn == "GenerateKey":
        return (
            FindingKind.ALGORITHM, Family.RSA, CryptoFunction.KEYGEN,
            "RSA key generation", "rsa.GenerateKey", 0.92,
        )
    if pkg == "rsa" and fn in ("SignPKCS1v15", "SignPSS"):
        return (
            FindingKind.ALGORITHM, Family.RSA, CryptoFunction.SIGN,
            "RSA signing", f"rsa.{fn}", 0.9,
        )
    if pkg == "rsa" and fn in ("VerifyPKCS1v15", "VerifyPSS"):
        return (
            FindingKind.ALGORITHM, Family.RSA, CryptoFunction.VERIFY,
            "RSA signature verification", f"rsa.{fn}", 0.9,
        )
    if pkg == "rsa" and fn in ("EncryptOAEP", "EncryptPKCS1v15"):
        return (
            FindingKind.ALGORITHM, Family.RSA, CryptoFunction.ENCRYPT,
            "RSA encryption", f"rsa.{fn}", 0.9,
        )
    if pkg == "rsa" and fn in ("DecryptOAEP", "DecryptPKCS1v15"):
        return (
            FindingKind.ALGORITHM, Family.RSA, CryptoFunction.DECRYPT,
            "RSA decryption", f"rsa.{fn}", 0.9,
        )
    if pkg == "ecdsa" and fn == "GenerateKey":
        return (
            FindingKind.ALGORITHM, Family.ECDSA, CryptoFunction.KEYGEN,
            "ECDSA key generation", "ecdsa.GenerateKey", 0.9,
        )
    if pkg == "ecdsa" and fn in ("Sign", "SignASN1"):
        return (
            FindingKind.ALGORITHM, Family.ECDSA, CryptoFunction.SIGN,
            "ECDSA signing", f"ecdsa.{fn}", 0.9,
        )
    if pkg == "ecdsa" and fn in ("Verify", "VerifyASN1"):
        return (
            FindingKind.ALGORITHM, Family.ECDSA, CryptoFunction.VERIFY,
            "ECDSA signature verification", f"ecdsa.{fn}", 0.9,
        )
    if pkg == "ed25519" and fn == "GenerateKey":
        return (
            FindingKind.ALGORITHM, Family.ED25519, CryptoFunction.KEYGEN,
            "Ed25519 key generation", "ed25519.GenerateKey", 0.95,
        )
    if pkg == "ed25519" and fn == "Sign":
        return (
            FindingKind.ALGORITHM, Family.ED25519, CryptoFunction.SIGN,
            "Ed25519 signing", "ed25519.Sign", 0.92,
        )
    if pkg == "ed25519" and fn == "Verify":
        return (
            FindingKind.ALGORITHM, Family.ED25519, CryptoFunction.VERIFY,
            "Ed25519 signature verification", "ed25519.Verify", 0.92,
        )
    if pkg == "dsa" and fn == "Sign":
        return (
            FindingKind.ALGORITHM, Family.DSA, CryptoFunction.SIGN,
            "DSA signing", "dsa.Sign", 0.9,
        )
    if pkg == "dsa" and fn == "Verify":
        return (
            FindingKind.ALGORITHM, Family.DSA, CryptoFunction.VERIFY,
            "DSA signature verification", "dsa.Verify", 0.9,
        )
    if pkg == "aes" and fn == "NewCipher":
        return (
            FindingKind.ALGORITHM, Family.AES, CryptoFunction.ENCRYPT,
            "AES block cipher", "aes.NewCipher", 0.92,
        )
    if pkg == "des" and fn == "NewTripleDESCipher":
        return (
            FindingKind.ALGORITHM, Family.THREE_DES, CryptoFunction.ENCRYPT,
            "3DES cipher", "des.NewTripleDESCipher", 0.95,
        )
    if pkg == "des" and fn == "NewCipher":
        return (
            FindingKind.ALGORITHM, Family.DES, CryptoFunction.ENCRYPT,
            "DES cipher", "des.NewCipher", 0.95,
        )
    if pkg == "hmac" and fn == "New":
        return (
            FindingKind.PROTOCOL, Family.HMAC, CryptoFunction.TAG,
            "hmac.New message authentication", "hmac.New", 0.90,
        )
    return None


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


def detect_code(source: bytes, path: str = "<source>", artifact_hash: str | None = None) -> list[Detection]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()
    tree = _PARSER.parse(source)
    matches = tree_sitter.QueryCursor(_QUERY).matches(tree.root_node)
    detections: list[Detection] = []
    for _pattern_index, captures in matches:
        if captures.get("call.node"):
            detection = _classify_call(path, captures, artifact_hash)
        elif captures.get("attr.node"):
            detection = _classify_bare_reference(path, captures, artifact_hash)
        else:
            detection = None
        if detection is not None:
            detections.append(detection)
    return detections


def _classify_call(
    path: str, captures: dict[str, list[tree_sitter.Node]], artifact_hash: str
) -> Detection | None:
    call_nodes = captures.get("call.node")
    args_nodes = captures.get("call.args")
    pkg_nodes = captures.get("call.pkg")
    fn_nodes = captures.get("call.fn")

    if not call_nodes or not args_nodes or not pkg_nodes or not fn_nodes:
        return None

    call_node, args_node = call_nodes[0], args_nodes[0]
    pkg, fn = _text(pkg_nodes[0]), _text(fn_nodes[0])
    resolved = _resolve_pkg_fn(pkg, fn)
    if resolved is None:
        return None
    kind, family, function, display_name, symbol, confidence = resolved

    line = call_node.start_point[0] + 1
    snippet = _text(call_node)[:200]
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule=f"go_ast.{symbol}",
        coarse=False,
    )
    detection = Detection(
        kind=kind, surface=Surface.SOURCE, family=family, function=function,
        display_name=display_name, symbol=symbol, confidence=confidence,
        path=path, line=line, snippet=snippet, source=FindingSource.AST,
        spans=[span],
    )

    if pkg == "rsa" and fn == "GenerateKey":
        args = _positional_args(args_node)
        if len(args) >= 2 and _text(args[1]).isdigit():
            detection.key_size = int(_text(args[1]))
    elif pkg == "ecdsa" and fn == "GenerateKey":
        args = _positional_args(args_node)
        if len(args) >= 1:
            detection.curve = _text(args[0]).replace("elliptic.", "").replace("()", "")
    elif pkg == "hmac" and fn == "New":
        args = _positional_args(args_node)
        if len(args) >= 1:
            h_arg = _text(args[0])
            for h_pkg, fam in _HASH_PACKAGES.items():
                if h_pkg in h_arg:
                    detection.underlying_hash_family = fam
                    break

    return detection


def _is_hmac_new_hash_argument(node: tree_sitter.Node) -> bool:
    """True when `node` is the first (hash-constructor) argument of an
    `hmac.New(hashFunc, key)` call -- already reported as that
    detection's `underlying_hash_family`, so reporting it a second time
    as a standalone digest reference would be a redundant duplicate
    finding on the same line, not a distinct fact."""
    parent = node.parent
    if parent is None or parent.type != "argument_list":
        return False
    call = parent.parent
    if call is None or call.type != "call_expression":
        return False
    fn_node = call.child_by_field_name("function")
    if fn_node is None or fn_node.type != "selector_expression":
        return False
    pkg_node = fn_node.child_by_field_name("operand")
    field_node = fn_node.child_by_field_name("field")
    if pkg_node is None or field_node is None:
        return False
    if _text(pkg_node) != "hmac" or _text(field_node) != "New":
        return False
    positional = _positional_args(parent)
    return bool(positional) and positional[0] == node


def _classify_bare_reference(
    path: str, captures: dict[str, list[tree_sitter.Node]], artifact_hash: str
) -> Detection | None:
    attr_nodes = captures.get("attr.node")
    pkg_nodes = captures.get("attr.pkg")
    fn_nodes = captures.get("attr.fn")
    if not attr_nodes or not pkg_nodes or not fn_nodes:
        return None

    attr_node = attr_nodes[0]
    parent = attr_node.parent
    if (
        parent is not None
        and parent.type == "call_expression"
        and parent.child_by_field_name("function") == attr_node
    ):
        return None  # actually called -- already handled by _classify_call

    if _is_hmac_new_hash_argument(attr_node):
        return None  # already captured as the HMAC detection's underlying_hash_family

    pkg, fn = _text(pkg_nodes[0]), _text(fn_nodes[0])
    resolved = _resolve_pkg_fn(pkg, fn)
    if resolved is None:
        return None
    kind, family, function, display_name, symbol, confidence = resolved

    line = attr_node.start_point[0] + 1
    snippet = _text(attr_node)[:200]
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=attr_node.start_byte,
        end=attr_node.end_byte,
        producing_rule=f"go_ast.{symbol}_ref",
        coarse=False,
    )
    return Detection(
        kind=kind, surface=Surface.SOURCE, family=family, function=function,
        display_name=f"{display_name} (reference)", symbol=symbol,
        confidence=round(confidence - 0.05, 2),
        path=path, line=line, snippet=snippet, source=FindingSource.AST,
        spans=[span],
    )
