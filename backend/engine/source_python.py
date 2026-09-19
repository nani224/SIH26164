"""Tree-sitter-based Python crypto usage detector.

Deterministic AST pattern matching (no ML) over a fixed set of high-value
patterns: hashlib digests, hmac.new, cryptography-lib RSA/EC keygen, and
symmetric cipher construction. See engine/queries/python_crypto.scm for the
structural query and docs/decisions/backend/002-phase1-risk-factors.md for
the family/vulnerability mapping applied downstream.

Known limitation (Phase 1 scope): only single-level `module.attr(...)`
calls are recognized (e.g. `rsa.generate_private_key(...)`), not deeper
attribute chains (e.g. `x.y.z.generate_private_key(...)`) or usage via a
renamed/aliased import. Tracked as a Phase 7-style follow-up.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tree_sitter
import tree_sitter_python

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection

_QUERY_PATH = Path(__file__).parent / "queries" / "python_crypto.scm"

_LANGUAGE = tree_sitter.Language(tree_sitter_python.language())
_PARSER = tree_sitter.Parser(_LANGUAGE)
_QUERY = tree_sitter.Query(_LANGUAGE, _QUERY_PATH.read_text())

_HASHLIB_DIGEST_FAMILY: dict[str, Family] = {
    "md5": Family.MD5,
    "sha1": Family.SHA_1,
    "sha224": Family.SHA_2,
    "sha256": Family.SHA_2,
    "sha384": Family.SHA_2,
    "sha512": Family.SHA_2,
    "sha3_224": Family.SHA_3,
    "sha3_256": Family.SHA_3,
    "sha3_384": Family.SHA_3,
    "sha3_512": Family.SHA_3,
}

_CIPHER_FAMILY: dict[str, Family] = {
    "AES": Family.AES,
    "TripleDES": Family.THREE_DES,
    "ChaCha20": Family.CHACHA20,
    "ARC4": Family.RC4,
    "Blowfish": Family.BLOWFISH,
}

# Substrings of a parameter's type annotation -> Family, for resolving
# `key.sign(...)`/`key.verify(...)` where `key`'s concrete type is a
# `cryptography`-library key class named in the enclosing function's
# signature (e.g. `def sign(self, msg: bytes, key: RSAPrivateKey) -> bytes`).
# Real, stable public class names from the `cryptography` package, not
# project-specific type aliases (a type alias like pyjwt's own
# `AllowedECKeys = Union[EllipticCurvePrivateKey, EllipticCurvePublicKey]`
# is a real, documented, honest miss -- resolving it would mean reading
# pyjwt's own source to learn its alias, which is tuning on this specific
# HOLD file, not a generalizable rule).
_KEY_PARAM_TYPE_FAMILY: list[tuple[str, Family]] = [
    ("RSA", Family.RSA),
    ("EllipticCurve", Family.ECDSA),
    ("Ed25519", Family.ED25519),
]


def _text(node: tree_sitter.Node) -> str:
    return node.text.decode("utf-8") if node.text else ""


def _kwarg(args_node: tree_sitter.Node, name: str) -> str | None:
    for child in args_node.named_children:
        if child.type == "keyword_argument":
            key = child.child_by_field_name("name")
            value = child.child_by_field_name("value")
            if key is not None and value is not None and _text(key) == name:
                return _text(value)
    return None


def _first_positional(args_node: tree_sitter.Node) -> str | None:
    for child in args_node.named_children:
        if child.type != "keyword_argument":
            return _text(child)
    return None


def _positional_args(args_node: tree_sitter.Node) -> list[tree_sitter.Node]:
    return [c for c in args_node.named_children if c.type != "keyword_argument"]


def _find_enclosing_function(node: tree_sitter.Node) -> tree_sitter.Node | None:
    ancestor = node.parent
    while ancestor is not None:
        if ancestor.type == "function_definition":
            return ancestor
        ancestor = ancestor.parent
    return None


def _resolve_param_type_family(call_node: tree_sitter.Node, receiver_name: str) -> Family | None:
    """`key.sign(...)`/`key.verify(...)` -- resolve `key`'s family from
    its type annotation on the enclosing function's own signature (a
    real, static, syntactic fact, not a guess or cross-file dataflow)."""
    func = _find_enclosing_function(call_node)
    if func is None:
        return None
    params = func.child_by_field_name("parameters")
    if params is None:
        return None
    for param in params.named_children:
        if param.type != "typed_parameter" or not param.named_children:
            continue
        if _text(param.named_children[0]) != receiver_name:
            continue
        type_node = param.child_by_field_name("type")
        if type_node is None:
            return None
        type_text = _text(type_node)
        for substring, family in _KEY_PARAM_TYPE_FAMILY:
            if substring in type_text:
                return family
        return None
    return None


def detect(path: str, source: bytes) -> list[Detection]:
    tree = _PARSER.parse(source)
    matches = tree_sitter.QueryCursor(_QUERY).matches(tree.root_node)
    detections: list[Detection] = []
    for _pattern_index, captures in matches:
        detection = _classify(path, captures)
        if detection is not None:
            detections.append(detection)
    return detections


def _classify(path: str, captures: dict[str, list[tree_sitter.Node]]) -> Detection | None:
    attr_node_list = captures.get("attr.node")
    if attr_node_list:
        attr_node = attr_node_list[0]
        parent = attr_node.parent
        if parent is not None and parent.type == "call" and parent.child_by_field_name("function") == attr_node:
            return None
        # If enclosed within an hmac.new call, hmac already captures the underlying hash
        ancestor = attr_node.parent
        while ancestor is not None and ancestor.type != "module":
            if ancestor.type == "call":
                fn_node = ancestor.child_by_field_name("function")
                if fn_node and _text(fn_node).startswith("hmac."):
                    return None
            ancestor = ancestor.parent
        obj_nodes = captures.get("attr.object")
        attr_name_nodes = captures.get("attr.name")
        if not obj_nodes or not attr_name_nodes:
            return None
        obj, attr = _text(obj_nodes[0]), _text(attr_name_nodes[0])
        if obj == "hashlib" and attr in _HASHLIB_DIGEST_FAMILY:
            line = attr_node.start_point[0] + 1
            snippet = _text(attr_node)[:200]
            attr_common: dict[str, Any] = dict(path=path, line=line, snippet=snippet, source=FindingSource.AST)
            return Detection(
                kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=_HASHLIB_DIGEST_FAMILY[attr],
                display_name=f"hashlib.{attr} reference", function=CryptoFunction.DIGEST,
                symbol=f"hashlib.{attr}", confidence=0.85, **attr_common,
            )
        return None

    call_nodes = captures.get("call.node")
    args_nodes = captures.get("call.args")
    if not call_nodes or not args_nodes:
        return None
    call_node, args_node = call_nodes[0], args_nodes[0]
    line = call_node.start_point[0] + 1
    snippet = _text(call_node)[:200]

    obj_nodes = captures.get("call.object")
    attr_nodes = captures.get("call.attr")
    if obj_nodes and attr_nodes:
        obj, attr = _text(obj_nodes[0]), _text(attr_nodes[0])
    else:
        return None  # bare-identifier calls aren't matched by any rule yet

    common: dict[str, Any] = dict(path=path, line=line, snippet=snippet, source=FindingSource.AST)

    if obj == "hashlib":
        return _classify_hashlib(attr, args_node, common)
    if obj == "hmac" and attr == "new":
        return _classify_hmac(args_node, common)
    if obj == "rsa" and attr == "generate_private_key":
        return _classify_rsa_keygen(args_node, common)
    if obj == "ec" and attr == "generate_private_key":
        return _classify_ec_keygen(args_node, common)
    if obj == "algorithms" and attr in _CIPHER_FAMILY:
        return _classify_cipher(attr, common)
    if attr in ("sign", "verify"):
        return _classify_key_method_call(obj, attr, call_node, common)
    return None


def _classify_hashlib(attr: str, args_node: tree_sitter.Node, common: dict[str, Any]) -> Detection | None:
    if attr in _HASHLIB_DIGEST_FAMILY:
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=_HASHLIB_DIGEST_FAMILY[attr],
            display_name=f"hashlib.{attr} digest", function=CryptoFunction.DIGEST,
            symbol=f"hashlib.{attr}", confidence=0.9, **common,
        )
    if attr == "new":
        arg = _first_positional(args_node)
        algo = arg.strip("'\"").lower() if arg else None
        family = _HASHLIB_DIGEST_FAMILY.get(algo) if algo else None
        if family is not None:
            return Detection(
                kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
                display_name=f"hashlib.new({algo!r}) digest", function=CryptoFunction.DIGEST,
                symbol="hashlib.new", confidence=0.85, **common,
            )
    return None


def _classify_hmac(args_node: tree_sitter.Node, common: dict[str, Any]) -> Detection | None:
    pos_args = _positional_args(args_node)
    hash_arg = _text(pos_args[2]) if len(pos_args) >= 3 else _kwarg(args_node, "digestmod")
    underlying = None
    if hash_arg and hash_arg.startswith("hashlib."):
        underlying = _HASHLIB_DIGEST_FAMILY.get(hash_arg.split(".", 1)[1])
    return Detection(
        kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=Family.HMAC,
        display_name="hmac.new message authentication", function=CryptoFunction.TAG,
        symbol="hmac.new", confidence=0.85, underlying_hash_family=underlying, **common,
    )


def _classify_rsa_keygen(args_node: tree_sitter.Node, common: dict[str, Any]) -> Detection:
    key_size_str = _kwarg(args_node, "key_size")
    key_size = int(key_size_str) if key_size_str and key_size_str.isdigit() else None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.RSA,
        display_name="RSA key generation", function=CryptoFunction.KEYGEN,
        symbol="rsa.generate_private_key", confidence=0.92, key_size=key_size, **common,
    )


def _classify_ec_keygen(args_node: tree_sitter.Node, common: dict[str, Any]) -> Detection:
    curve_arg = _first_positional(args_node)
    curve = None
    if curve_arg and curve_arg.startswith("ec."):
        curve = curve_arg.split(".", 1)[1].split("(")[0]
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.ECDSA,
        display_name="EC key generation", function=CryptoFunction.KEYGEN,
        symbol="ec.generate_private_key", confidence=0.85, curve=curve, **common,
    )


def _classify_key_method_call(
    obj: str, attr: str, call_node: tree_sitter.Node, common: dict[str, Any]
) -> Detection | None:
    family = _resolve_param_type_family(call_node, obj)
    if family is None:
        return None
    function = CryptoFunction.SIGN if attr == "sign" else CryptoFunction.VERIFY
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
        display_name=f"{obj}.{attr}(...) ({family.value} key, from parameter type annotation)",
        function=function, symbol=f"{obj}.{attr}", confidence=0.82, **common,
    )


def _classify_cipher(attr: str, common: dict[str, Any]) -> Detection:
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=_CIPHER_FAMILY[attr],
        display_name=f"{attr} cipher", function=CryptoFunction.ENCRYPT,
        symbol=f"algorithms.{attr}", confidence=0.85, **common,
    )
