"""Tree-sitter-based Java crypto usage detector.

M1 (Track CC): Deterministic AST pattern matching over the JCA/JCE API
surface (javax.crypto.Cipher, java.security.KeyPairGenerator/KeyGenerator/
MessageDigest/Signature/KeyAgreement/KeyStore, javax.crypto.Mac,
javax.crypto.spec.SecretKeySpec, javax.net.ssl.SSLContext) plus a handful
of direct BouncyCastle lightweight-API class usages (`new SHA256Digest()`,
`new AESEngine()`, etc.) -- BC usage via a JCA `Provider` argument
(`Cipher.getInstance("AES/GCM/NoPadding", "BC")`) is already covered by
the JCA transformation-string path since the provider arg doesn't change
the shape of the `getInstance` call.

M7 (Track CC): also `javax.crypto.SecretKeyFactory.getInstance("PBKDF2With...")`
-- found while sourcing a real HOLD candidate (Spring Security's
Pbkdf2PasswordEncoder). Reported as Family.HMAC/KEYDERIVE since PBKDF2 is
itself an HMAC-based KDF, not a distinct Family enum value.

Two things the query alone can't express, handled here in Python:
  - Transformation-string parsing (`"AES/GCM/NoPadding"`, `"SHA256withRSA"`,
    `"HmacSHA256"`) -- same string, three different JCA classes, three
    different parse rules.
  - Linking `KeyPairGenerator`/`KeyGenerator` instantiation to a *later*
    `var.initialize(n)` / `var.init(n)` call on the same variable, to
    recover key size / curve the way `Signature` or `Cipher` get theirs
    directly from the transformation string. This is real intra-method
    dataflow, not just pattern matching -- deliberately kept to the single
    simplest case (same variable, same method body, textual order) rather
    than a general dataflow analysis.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import tree_sitter
import tree_sitter_java

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection, Span

_QUERY_PATH = Path(__file__).parent / "queries" / "java_crypto.scm"

_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
_PARSER = tree_sitter.Parser(_LANGUAGE)
_QUERY = tree_sitter.Query(_LANGUAGE, _QUERY_PATH.read_text())

# Classes whose `.getInstance(name, ...)` static factory is a crypto usage.
_GET_INSTANCE_CLASSES = {
    "Cipher", "KeyPairGenerator", "KeyGenerator", "MessageDigest",
    "Signature", "KeyAgreement", "Mac", "SSLContext", "KeyStore",
    "SecretKeyFactory",
}
# For these classes, a later `var.initialize(...)`/`var.init(...)` call on
# the assigned variable carries key size / curve info worth linking back.
_LINKABLE_CLASSES = {"KeyPairGenerator", "KeyGenerator"}
_LINK_METHODS = {"initialize", "init"}

_CIPHER_ALGO_FAMILY: dict[str, Family] = {
    "AES": Family.AES,
    "DES": Family.DES,
    "DESede": Family.THREE_DES,
    "TripleDES": Family.THREE_DES,
    "Blowfish": Family.BLOWFISH,
    "RC4": Family.RC4,
    "ARCFOUR": Family.RC4,
    "ChaCha20": Family.CHACHA20,
    "RSA": Family.RSA,
}

_DIGEST_FAMILY: dict[str, Family] = {
    "MD5": Family.MD5,
    "SHA-1": Family.SHA_1, "SHA1": Family.SHA_1,
    "SHA-224": Family.SHA_2, "SHA224": Family.SHA_2,
    "SHA-256": Family.SHA_2, "SHA256": Family.SHA_2,
    "SHA-384": Family.SHA_2, "SHA384": Family.SHA_2,
    "SHA-512": Family.SHA_2, "SHA512": Family.SHA_2,
    "SHA3-224": Family.SHA_3, "SHA-3-224": Family.SHA_3,
    "SHA3-256": Family.SHA_3, "SHA-3-256": Family.SHA_3,
    "SHA3-384": Family.SHA_3, "SHA-3-384": Family.SHA_3,
    "SHA3-512": Family.SHA_3, "SHA-3-512": Family.SHA_3,
}

_SIGNATURE_FAMILY: dict[str, Family] = {
    "RSA": Family.RSA,
    "DSA": Family.DSA,
    "ECDSA": Family.ECDSA,
    "Ed25519": Family.ED25519,
    # Ed448, RSASSA-PSS-with-no-hash-prefix etc. intentionally unmapped --
    # no matching Family enum value exists; better to miss than mislabel.
}

_KEYAGREEMENT_FAMILY: dict[str, Family] = {
    "ECDH": Family.ECDH,
    "DH": Family.DH,
    "X25519": Family.X25519,
}

# Direct BouncyCastle lightweight-API class -> (family, function, display).
_BC_CLASS_MAP: dict[str, tuple[Family, CryptoFunction, str]] = {
    "SHA256Digest": (Family.SHA_2, CryptoFunction.DIGEST, "BouncyCastle SHA-256 digest"),
    "SHA1Digest": (Family.SHA_1, CryptoFunction.DIGEST, "BouncyCastle SHA-1 digest"),
    "MD5Digest": (Family.MD5, CryptoFunction.DIGEST, "BouncyCastle MD5 digest"),
    "AESEngine": (Family.AES, CryptoFunction.ENCRYPT, "BouncyCastle AES block cipher engine"),
    "AESFastEngine": (Family.AES, CryptoFunction.ENCRYPT, "BouncyCastle AES block cipher engine"),
    "DESEngine": (Family.DES, CryptoFunction.ENCRYPT, "BouncyCastle DES block cipher engine"),
    "RSAEngine": (Family.RSA, CryptoFunction.ENCRYPT, "BouncyCastle RSA cipher engine"),
    "RSAKeyPairGenerator": (Family.RSA, CryptoFunction.KEYGEN, "BouncyCastle RSA key pair generation"),
    "Ed25519KeyPairGenerator": (Family.ED25519, CryptoFunction.KEYGEN, "BouncyCastle Ed25519 key pair generation"),
    "ECKeyPairGenerator": (Family.ECDSA, CryptoFunction.KEYGEN, "BouncyCastle EC key pair generation"),
    "HMac": (Family.HMAC, CryptoFunction.TAG, "BouncyCastle HMAC"),
}


def _text(node: tree_sitter.Node) -> str:
    return node.text.decode("utf-8") if node.text else ""


def _first_string_literal_text(node: tree_sitter.Node | None) -> str | None:
    if node is None:
        return None
    if node.type == "string_literal":
        for child in node.children:
            if child.type == "string_fragment":
                return _text(child)
        return ""
    for child in node.children:
        found = _first_string_literal_text(child)
        if found is not None:
            return found
    return None


def _first_int_literal(node: tree_sitter.Node | None) -> int | None:
    if node is None:
        return None
    if node.type == "decimal_integer_literal":
        txt = _text(node).rstrip("lL")
        return int(txt) if txt.isdigit() else None
    for child in node.children:
        found = _first_int_literal(child)
        if found is not None:
            return found
    return None


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
    ordered = sorted(matches, key=lambda m: _match_start(m[1]))

    detections: list[Detection] = []
    pending: dict[str, Detection] = {}

    for _pattern_index, captures in ordered:
        if captures.get("call.node"):
            _handle_call(path, captures, pending, detections, artifact_hash)
        elif captures.get("new.node"):
            detection = _classify_new(path, captures, artifact_hash)
            if detection is not None:
                detections.append(detection)

    detections.extend(pending.values())
    return detections


def _match_start(captures: dict[str, list[tree_sitter.Node]]) -> int:
    for nodes in captures.values():
        if nodes:
            return nodes[0].start_byte
    return 0


def _handle_call(
    path: str,
    captures: dict[str, list[tree_sitter.Node]],
    pending: dict[str, Detection],
    detections: list[Detection],
    artifact_hash: str,
) -> None:
    call_node = captures["call.node"][0]
    obj_node = captures["call.object"][0]
    name_node = captures["call.name"][0]
    args_node = captures["call.args"][0]
    obj, method = _text(obj_node), _text(name_node)

    if method == "getInstance" and obj in _GET_INSTANCE_CLASSES:
        detection = _classify_get_instance(path, obj, args_node, call_node, artifact_hash)
        if detection is None:
            return
        if obj in _LINKABLE_CLASSES:
            var_name = _assigned_variable_name(call_node)
            if var_name is not None:
                pending[var_name] = detection
                return
        detections.append(detection)
        return

    if method in _LINK_METHODS and obj in pending:
        detection = pending.pop(obj)
        key_size = _first_int_literal(args_node)
        if key_size is not None:
            detection.key_size = key_size
        curve = _first_string_literal_text(args_node)
        if curve is not None and detection.family in (Family.ECDSA, Family.ECDH):
            detection.curve = curve
        detections.append(detection)


def _assigned_variable_name(call_node: tree_sitter.Node) -> str | None:
    parent = call_node.parent
    if parent is not None and parent.type == "variable_declarator":
        name_node = parent.child_by_field_name("name")
        if name_node is not None:
            return _text(name_node)
    return None


def _classify_get_instance(
    path: str, class_name: str, args_node: tree_sitter.Node, call_node: tree_sitter.Node, artifact_hash: str
) -> Detection | None:
    transformation = _first_string_literal_text(args_node)
    if transformation is None:
        return None
    line = call_node.start_point[0] + 1
    snippet = _text(call_node)[:200]
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=call_node.start_byte,
        end=call_node.end_byte,
        producing_rule=f"java_ast.{class_name}.getInstance",
    )
    common: dict[str, Any] = dict(path=path, line=line, snippet=snippet, source=FindingSource.AST, spans=[span])
    symbol = f"{class_name}.getInstance"

    if class_name == "Cipher":
        algo = transformation.split("/")[0]
        family = _CIPHER_ALGO_FAMILY.get(algo)
        if family is None:
            return None
        mode = transformation.split("/")[1] if transformation.count("/") >= 1 else None
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=f"Cipher.getInstance(\"{transformation}\")",
            function=CryptoFunction.ENCRYPT, symbol=symbol, confidence=0.92,
            mode=mode, **common,
        )

    if class_name in ("KeyPairGenerator", "KeyGenerator"):
        family = _CIPHER_ALGO_FAMILY.get(transformation) or _SIGNATURE_FAMILY.get(transformation)
        if transformation == "EC":
            family = Family.ECDSA
        if family is None:
            return None
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=f"{class_name}.getInstance(\"{transformation}\") key generation",
            function=CryptoFunction.KEYGEN, symbol=symbol, confidence=0.93, **common,
        )

    if class_name == "MessageDigest":
        family = _DIGEST_FAMILY.get(transformation)
        if family is None:
            return None
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=f"MessageDigest.getInstance(\"{transformation}\")",
            function=CryptoFunction.DIGEST, symbol=symbol, confidence=0.92, **common,
        )

    if class_name == "Signature":
        if "with" in transformation:
            hash_part, _, family_part = transformation.partition("with")
        else:
            hash_part, family_part = "", transformation
        family = _SIGNATURE_FAMILY.get(family_part)
        if family is None:
            return None
        underlying = _DIGEST_FAMILY.get(hash_part) if hash_part and hash_part != "NONE" else None
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=f"Signature.getInstance(\"{transformation}\")",
            function=CryptoFunction.SIGN, symbol=symbol, confidence=0.9,
            underlying_hash_family=underlying, **common,
        )

    if class_name == "KeyAgreement":
        family = _KEYAGREEMENT_FAMILY.get(transformation)
        if family is None:
            return None
        return Detection(
            kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=family,
            display_name=f"KeyAgreement.getInstance(\"{transformation}\")",
            function=CryptoFunction.KEYDERIVE, symbol=symbol, confidence=0.9, **common,
        )

    if class_name == "Mac":
        if not transformation.startswith("Hmac"):
            return None
        underlying = _DIGEST_FAMILY.get(transformation[len("Hmac"):])
        return Detection(
            kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=Family.HMAC,
            display_name=f"Mac.getInstance(\"{transformation}\")",
            function=CryptoFunction.TAG, symbol=symbol, confidence=0.9,
            underlying_hash_family=underlying, **common,
        )

    if class_name == "SSLContext":
        return Detection(
            kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=None,
            display_name=f"SSLContext.getInstance(\"{transformation}\") TLS context",
            function=CryptoFunction.UNKNOWN, symbol=symbol, confidence=0.85, **common,
        )

    if class_name == "SecretKeyFactory":
        if not transformation.startswith("PBKDF2"):
            return None  # PBEWith... legacy names intentionally unmapped -- see ADR
        underlying = _DIGEST_FAMILY.get(transformation.split("WithHmac", 1)[1]) \
            if "WithHmac" in transformation else None
        return Detection(
            kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=Family.HMAC,
            display_name=f"SecretKeyFactory.getInstance(\"{transformation}\") PBKDF2 key derivation",
            function=CryptoFunction.KEYDERIVE, symbol=symbol, confidence=0.88,
            underlying_hash_family=underlying, **common,
        )

    if class_name == "KeyStore":
        return Detection(
            kind=FindingKind.KEY, surface=Surface.SOURCE, family=None,
            display_name=f"KeyStore.getInstance(\"{transformation}\") container",
            function=CryptoFunction.UNKNOWN, symbol=symbol, confidence=0.8, **common,
        )

    return None


def _classify_new(path: str, captures: dict[str, list[tree_sitter.Node]], artifact_hash: str) -> Detection | None:
    new_node = captures["new.node"][0]
    type_node = captures["new.type"][0]
    args_node = captures["new.args"][0]
    type_name = _text(type_node)
    line = new_node.start_point[0] + 1
    snippet = _text(new_node)[:200]
    span = Span(
        artifact_hash=artifact_hash,
        kind="ast",
        start=new_node.start_byte,
        end=new_node.end_byte,
        producing_rule=f"java_ast.new_{type_name}",
    )
    common: dict[str, Any] = dict(path=path, line=line, snippet=snippet, source=FindingSource.AST, spans=[span])

    if type_name == "SecretKeySpec":
        args = [c for c in args_node.named_children]
        algo = _text(args[1]).strip('"') if len(args) >= 2 and args[1].type == "string_literal" else None
        family = _CIPHER_ALGO_FAMILY.get(algo) if algo else None
        if family is None:
            return None
        return Detection(
            kind=FindingKind.KEY, surface=Surface.SOURCE, family=family,
            display_name=f"SecretKeySpec(\"{algo}\") key material",
            function=CryptoFunction.UNKNOWN, symbol="new SecretKeySpec", confidence=0.85, **common,
        )

    bc_entry = _BC_CLASS_MAP.get(type_name)
    if bc_entry is not None:
        family, function, display = bc_entry
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=display, function=function,
            symbol=f"new {type_name}", confidence=0.88, **common,
        )

    return None
