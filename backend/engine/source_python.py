"""Tree-sitter-based Python crypto usage detector.

Deterministic AST pattern matching (no ML) over a fixed set of high-value
patterns: hashlib digests, hmac.new, cryptography-lib RSA/EC keygen, and
symmetric cipher construction. See engine/queries/python_crypto.scm for the
structural query and docs/decisions/backend/010-risk-factor-derivation.md for
the family/vulnerability mapping applied downstream.

Known limitation (Phase 1 scope): only single-level `module.attr(...)`
calls are recognized (e.g. `rsa.generate_private_key(...)`), not deeper
attribute chains (e.g. `x.y.z.generate_private_key(...)`) or usage via a
renamed/aliased import. Tracked as a Phase 7-style follow-up.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import tree_sitter
import tree_sitter_python

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection, Span

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

_KEY_PARAM_TYPE_FAMILY: tuple[tuple[str, Family], ...] = (
    ("RSAPrivateKey", Family.RSA),
    ("RSAPublicKey", Family.RSA),
    ("EllipticCurvePrivateKey", Family.ECDSA),
    ("EllipticCurvePublicKey", Family.ECDSA),
    ("Ed25519PrivateKey", Family.ED25519),
    ("Ed25519PublicKey", Family.ED25519),
    ("DSAPrivateKey", Family.DSA),
    ("DSAPublicKey", Family.DSA),
    ("DHPrivateKey", Family.DH),
    ("DHPublicKey", Family.DH),
    ("X25519PrivateKey", Family.X25519),
    ("X25519PublicKey", Family.X25519),
)


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


def detect(path: str, source: bytes, artifact_hash: str | None = None) -> list[Detection]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()
    tree = _PARSER.parse(source)
    matches = tree_sitter.QueryCursor(_QUERY).matches(tree.root_node)
    detections: list[Detection] = []
    for _pattern_index, captures in matches:
        detection = _classify(path, captures, artifact_hash)
        if detection is not None:
            detections.append(detection)
    return detections


def _classify(
    path: str, captures: dict[str, list[tree_sitter.Node]], artifact_hash: str
) -> Detection | None:
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
            span = Span(
                artifact_hash=artifact_hash,
                kind="ast",
                start=attr_node.start_byte,
                end=attr_node.end_byte,
                producing_rule="python_ast.hashlib_reference",
                coarse=False,
            )
            return Detection(
                kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=_HASHLIB_DIGEST_FAMILY[attr],
                display_name=f"hashlib.{attr} reference", function=CryptoFunction.DIGEST,
                symbol=f"hashlib.{attr}", confidence=0.85, spans=[span], **attr_common,
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
        return _classify_hashlib(attr, args_node, call_node, artifact_hash, common)
    if obj == "hmac" and attr == "new":
        return _classify_hmac(args_node, call_node, artifact_hash, common)
    if obj == "rsa" and attr == "generate_private_key":
        return _classify_rsa_keygen(args_node, call_node, artifact_hash, common)
    if obj == "ec" and attr == "generate_private_key":
        return _classify_ec_keygen(args_node, call_node, artifact_hash, common)
    if obj == "algorithms" and attr in _CIPHER_FAMILY:
        return _classify_cipher(attr, call_node, artifact_hash, common)
    if attr in ("sign", "verify"):
        return _classify_key_method_call(obj, attr, call_node, artifact_hash, common)
    return None


def _classify_hashlib(
    attr: str,
    args_node: tree_sitter.Node,
    call_node: tree_sitter.Node,
    artifact_hash: str,
    common: dict[str, Any],
) -> Detection | None:
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule=f"python_ast.hashlib_{attr}",
        coarse=False,
    )
    if attr in _HASHLIB_DIGEST_FAMILY:
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=_HASHLIB_DIGEST_FAMILY[attr],
            display_name=f"hashlib.{attr} digest", function=CryptoFunction.DIGEST,
            symbol=f"hashlib.{attr}", confidence=0.9, spans=[span], **common,
        )
    if attr == "new":
        arg = _first_positional(args_node)
        algo = arg.strip("'\"").lower() if arg else None
        family = _HASHLIB_DIGEST_FAMILY.get(algo) if algo else None
        if family is not None:
            return Detection(
                kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
                display_name=f"hashlib.new({algo!r}) digest", function=CryptoFunction.DIGEST,
                symbol="hashlib.new", confidence=0.85, spans=[span], **common,
            )
    return None


def _classify_hmac(
    args_node: tree_sitter.Node,
    call_node: tree_sitter.Node,
    artifact_hash: str,
    common: dict[str, Any],
) -> Detection | None:
    pos_args = _positional_args(args_node)
    hash_arg = _text(pos_args[2]) if len(pos_args) >= 3 else _kwarg(args_node, "digestmod")
    underlying = None
    if hash_arg and hash_arg.startswith("hashlib."):
        underlying = _HASHLIB_DIGEST_FAMILY.get(hash_arg.split(".", 1)[1])
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule="python_ast.hmac_new",
        coarse=False,
    )
    return Detection(
        kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=Family.HMAC,
        display_name="hmac.new message authentication", function=CryptoFunction.TAG,
        symbol="hmac.new", confidence=0.85, underlying_hash_family=underlying,
        spans=[span], **common,
    )


def _classify_rsa_keygen(
    args_node: tree_sitter.Node,
    call_node: tree_sitter.Node,
    artifact_hash: str,
    common: dict[str, Any],
) -> Detection:
    key_size_str = _kwarg(args_node, "key_size")
    key_size = int(key_size_str) if key_size_str and key_size_str.isdigit() else None
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule="python_ast.rsa_generate_private_key",
        coarse=False,
    )
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.RSA,
        display_name="RSA key generation", function=CryptoFunction.KEYGEN,
        symbol="rsa.generate_private_key", confidence=0.92, key_size=key_size,
        spans=[span], **common,
    )


def _classify_ec_keygen(
    args_node: tree_sitter.Node,
    call_node: tree_sitter.Node,
    artifact_hash: str,
    common: dict[str, Any],
) -> Detection:
    curve_arg = _first_positional(args_node)
    curve = None
    if curve_arg and curve_arg.startswith("ec."):
        curve = curve_arg.split(".", 1)[1].split("(")[0]
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule="python_ast.ec_generate_private_key",
        coarse=False,
    )
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.ECDSA,
        display_name="EC key generation", function=CryptoFunction.KEYGEN,
        symbol="ec.generate_private_key", confidence=0.85, curve=curve,
        spans=[span], **common,
    )


def _classify_key_method_call(
    obj: str,
    attr: str,
    call_node: tree_sitter.Node,
    artifact_hash: str,
    common: dict[str, Any],
) -> Detection | None:
    family = _resolve_param_type_family(call_node, obj)
    if family is None:
        return None
    function = CryptoFunction.SIGN if attr == "sign" else CryptoFunction.VERIFY
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule=f"python_ast.key_method_{attr}",
        coarse=False,
    )
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
        display_name=f"{obj}.{attr}(...) ({family.value} key, from parameter type annotation)",
        function=function, symbol=f"{obj}.{attr}", confidence=0.82,
        spans=[span], **common,
    )


def _classify_cipher(
    attr: str,
    call_node: tree_sitter.Node,
    artifact_hash: str,
    common: dict[str, Any],
) -> Detection:
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule=f"python_ast.cipher_{attr.lower()}",
        coarse=False,
    )
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=_CIPHER_FAMILY[attr],
        display_name=f"{attr} cipher", function=CryptoFunction.ENCRYPT,
        symbol=f"algorithms.{attr}", confidence=0.85, spans=[span], **common,
    )
