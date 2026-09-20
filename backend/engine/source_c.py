"""Tree-sitter-based C/C++ crypto usage detector.

M2 (Track CC): Deterministic AST pattern matching over three widely used
C crypto libraries, all free-function APIs (no method-call syntax, unlike
Java's JCA), so one bare-call query (`engine/queries/c_crypto.scm`)
covers all three -- semantic matching happens in Python, same approach as
the Go/Python/Java detectors:

- **OpenSSL 3.x modern API**: `EVP_CIPHER_fetch(ctx, "AES-256-GCM", propq)`
  / `EVP_MD_fetch(ctx, "SHA256", propq)` -- algorithm-name-string parsing,
  same idea as Java's `Cipher`/`Signature` transformation strings.
  `EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, bits)` /
  `EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_...)` for keygen
  parameters. Also covers the still-extremely-common pre-3.0 zero-arg
  algorithm getters (`EVP_aes_256_gcm()`, `EVP_sha256()`, ...) since
  real-world OpenSSL code overwhelmingly still uses these, not just
  `*_fetch` -- excluding them would badly hurt real-world recall for a
  detector whose whole point is finding real usages.

  **Cipher-context linkage (M3 fix, see ADR 015)**: a fetched/gotten
  cipher handle by itself is not an operation -- real-world HOLD testing
  against OpenSSL's own `demos/cipher/aesgcm.c` caught this as a real
  precision-floor violation (0.89 < 0.95): `EVP_CIPHER_fetch` was firing
  as ENCRYPT unconditionally, even when the fetched handle was later used
  for `EVP_DecryptInit_ex2`, and even the encrypt-path fetch was a
  duplicate of the *real* operation at `EVP_EncryptUpdate`. Cipher
  handles (from `EVP_CIPHER_fetch` or a zero-arg getter) are now tracked
  through `EVP_{Encrypt,Decrypt}Init{_ex,_ex2}` -> bound to the `ctx`
  variable -> resolved at the real transformation call
  (`EVP_{Encrypt,Decrypt}Update` with a non-NULL output, i.e. not just
  AAD) or, for AEAD modes (GCM/CCM), at the tag-retrieval
  (`EVP_CIPHER_CTX_get_params`, encrypt side) / tag-verify
  (`EVP_DecryptFinal_ex`, decrypt side) call. A cipher handle or ctx
  binding that's never consumed by one of those (e.g. the whole flow
  isn't visible in a small snippet) still gets reported once, at the
  point it was last seen -- a detector that requires a specific follow-up
  call to ever fire at all would be a stealth recall regression, same
  principle as the Java `KeyPairGenerator`/`initialize` linkage.
- **mbedTLS**: `mbedtls_<algo>_setkey_enc/dec`, `mbedtls_<algo>_starts`
  digest init, `mbedtls_rsa_gen_key`, `mbedtls_ecdsa_genkey`,
  `mbedtls_gcm_setkey`.
- **wolfSSL**: `wc_AesSetKey`, `wc_Des3_SetKey`, `wc_MakeRsaKey`,
  `wc_ecc_make_key`, `wc_<Algo>Hash` one-shot digests, `wc_HmacSetKey`.

Binary detection (`engine/scanner.py`'s AES S-box constant check) is
independent of this module and untouched by it.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tree_sitter
import tree_sitter_c

from api.models import CryptoFunction, Family, FindingKind, FindingSource, Surface
from engine.models import Detection, Span

_QUERY_PATH = Path(__file__).parent / "queries" / "c_crypto.scm"

_LANGUAGE = tree_sitter.Language(tree_sitter_c.language())
_PARSER = tree_sitter.Parser(_LANGUAGE)
_QUERY = tree_sitter.Query(_LANGUAGE, _QUERY_PATH.read_text())

_DIGEST_NAME_FAMILY: dict[str, Family] = {
    "MD5": Family.MD5,
    "SHA1": Family.SHA_1, "SHA": Family.SHA_1,
    "SHA224": Family.SHA_2, "SHA256": Family.SHA_2,
    "SHA384": Family.SHA_2, "SHA512": Family.SHA_2,
    "SHA3-224": Family.SHA_3, "SHA3-256": Family.SHA_3,
    "SHA3-384": Family.SHA_3, "SHA3-512": Family.SHA_3,
}

_OPENSSL_CIPHER_RE = re.compile(r"^(AES)-(\d+)-([A-Z0-9]+)$")
_AEAD_MODES = {"GCM", "CCM"}


@dataclass
class _CipherInfo:
    family: Family
    key_size: int | None
    mode: str | None


@dataclass
class _CipherVarBinding:
    info: _CipherInfo
    consumed: bool
    common: dict[str, Any]


@dataclass
class _CtxBinding:
    info: _CipherInfo
    direction: str  # "encrypt" or "decrypt"
    consumed: bool
    common: dict[str, Any]
    fn: str


def _text(node: tree_sitter.Node) -> str:
    return node.text.decode("utf-8") if node.text else ""


def _positional_args(args_node: tree_sitter.Node) -> list[tree_sitter.Node]:
    return list(args_node.named_children)


def _string_literal_text(node: tree_sitter.Node | None) -> str | None:
    if node is None or node.type != "string_literal":
        return None
    for child in node.children:
        if child.type == "string_content":
            return _text(child)
    return ""


def _int_literal_value(node: tree_sitter.Node | None) -> int | None:
    if node is None or node.type != "number_literal":
        return None
    txt = _text(node).rstrip("uUlL")
    return int(txt) if txt.isdigit() else None


def _match_start(captures: dict[str, list[tree_sitter.Node]]) -> int:
    for nodes in captures.values():
        if nodes:
            return nodes[0].start_byte
    return 0


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
    cipher_vars: dict[str, _CipherVarBinding] = {}
    ctx_state: dict[str, _CtxBinding] = {}

    for _pattern_index, captures in ordered:
        call_nodes = captures.get("call.node")
        args_nodes = captures.get("call.args")
        name_nodes = captures.get("call.name")
        if not call_nodes or not args_nodes or not name_nodes:
            continue
        call_node, args_node = call_nodes[0], args_nodes[0]
        fn = _text(name_nodes[0])
        args = _positional_args(args_node)
        line = call_node.start_point[0] + 1
        snippet = _text(call_node)[:200]
        span = Span(
            artifact_hash=artifact_hash,
            kind="ast",
            start=call_node.start_byte,
            end=call_node.end_byte,
            producing_rule=f"c_ast.{fn}",
        )
        common: dict[str, Any] = dict(
            path=path, line=line, snippet=snippet, source=FindingSource.AST, spans=[span]
        )

        if fn == "EVP_CIPHER_fetch":
            _track_cipher_fetch(call_node, args, cipher_vars, common, detections)
            continue
        if fn in _EVP_ENCRYPT_INIT_FUNCS or fn in _EVP_DECRYPT_INIT_FUNCS:
            direction = "encrypt" if fn in _EVP_ENCRYPT_INIT_FUNCS else "decrypt"
            _bind_evp_ctx(fn, args, direction, cipher_vars, ctx_state, common, detections)
            continue
        if fn in ("EVP_EncryptUpdate", "EVP_DecryptUpdate"):
            _handle_evp_update(fn, args, ctx_state, common, detections)
            continue
        if fn == "EVP_CIPHER_CTX_get_params":
            _handle_evp_get_params(args, ctx_state, common, detections)
            continue
        if fn in ("EVP_DecryptFinal_ex", "EVP_DecryptFinal"):
            _handle_evp_decrypt_final(args, ctx_state, common, detections)
            continue

        handler = _OPENSSL_HANDLERS.get(fn) or _MBEDTLS_HANDLERS.get(fn) or _WOLFSSL_HANDLERS.get(fn)
        if handler is not None:
            handler_detection = handler(fn, args, common)
            if handler_detection is not None:
                detections.append(handler_detection)
            continue

        digest_detection = _classify_openssl_digest_getter(fn, common)
        if digest_detection is not None:
            detections.append(digest_detection)

    for cipher_binding in cipher_vars.values():
        if not cipher_binding.consumed:
            detections.append(_cipher_var_to_detection(cipher_binding))
    for ctx_binding in ctx_state.values():
        if not ctx_binding.consumed:
            detections.append(_ctx_binding_to_detection(ctx_binding))

    return detections


# --- OpenSSL EVP cipher-context linkage --------------------------------


def _assigned_c_variable_name(call_node: tree_sitter.Node) -> str | None:
    parent = call_node.parent
    if parent is None:
        return None
    if parent.type == "assignment_expression":
        left = parent.child_by_field_name("left")
        return _text(left) if left is not None else None
    if parent.type == "init_declarator":
        declarator = parent.child_by_field_name("declarator")
        return _text(declarator).lstrip("*").strip() if declarator is not None else None
    return None


def _track_cipher_fetch(
    call_node: tree_sitter.Node,
    args: list[tree_sitter.Node],
    cipher_vars: dict[str, _CipherVarBinding],
    common: dict[str, Any],
    detections: list[Detection],
) -> None:
    if len(args) < 2:
        return
    name = _string_literal_text(args[1])
    if name is None:
        return
    family, key_size, mode = _parse_openssl_cipher_name(name)
    if family is None:
        return
    var = _assigned_c_variable_name(call_node)
    if var is None:
        return
    existing = cipher_vars.get(var)
    if existing is not None and not existing.consumed:
        detections.append(_cipher_var_to_detection(existing))
    cipher_vars[var] = _CipherVarBinding(info=_CipherInfo(family, key_size, mode), consumed=False, common=common)


def _lookup_cipher_getter(fn: str) -> _CipherInfo | None:
    """Zero-arg pre-3.0 cipher getters, e.g. `EVP_aes_256_gcm()`, used as
    the direct argument of an Encrypt/DecryptInit call -- classified from
    the function name alone. Unlike digest getters, these are never
    self-firing: which operation they represent (encrypt vs decrypt)
    depends entirely on which Init function they're passed to."""
    m = _EVP_AES_RE.match(fn)
    if m:
        return _CipherInfo(Family.AES, int(m.group(1)), m.group(2).upper())
    if fn.startswith("EVP_des_ede3_"):
        return _CipherInfo(Family.THREE_DES, None, None)
    if fn.startswith("EVP_des_"):
        return _CipherInfo(Family.DES, None, None)
    if fn.startswith("EVP_bf_"):
        return _CipherInfo(Family.BLOWFISH, None, None)
    if fn == "EVP_rc4":
        return _CipherInfo(Family.RC4, None, None)
    if fn in ("EVP_chacha20", "EVP_chacha20_poly1305"):
        return _CipherInfo(Family.CHACHA20, None, None)
    return None


def _resolve_cipher_arg(node: tree_sitter.Node, cipher_vars: dict[str, _CipherVarBinding]) -> _CipherInfo | None:
    if node.type == "call_expression":
        fn_node = node.child_by_field_name("function")
        return _lookup_cipher_getter(_text(fn_node)) if fn_node is not None else None
    if node.type == "identifier":
        binding = cipher_vars.get(_text(node))
        if binding is None:
            return None
        binding.consumed = True
        return binding.info
    return None


_EVP_ENCRYPT_INIT_FUNCS = {"EVP_EncryptInit_ex2", "EVP_EncryptInit_ex", "EVP_EncryptInit"}
_EVP_DECRYPT_INIT_FUNCS = {"EVP_DecryptInit_ex2", "EVP_DecryptInit_ex", "EVP_DecryptInit"}


def _bind_evp_ctx(
    fn: str,
    args: list[tree_sitter.Node],
    direction: str,
    cipher_vars: dict[str, _CipherVarBinding],
    ctx_state: dict[str, _CtxBinding],
    common: dict[str, Any],
    detections: list[Detection],
) -> None:
    if len(args) < 2 or args[0].type != "identifier":
        return
    ctx_var = _text(args[0])
    info = _resolve_cipher_arg(args[1], cipher_vars)
    if info is None:
        # Can't resolve the algorithm -- drop any stale binding for this
        # ctx rather than let an old mode/direction leak into a later
        # get_params/Final call that actually belongs to this new, opaque
        # re-init.
        ctx_state.pop(ctx_var, None)
        return
    existing = ctx_state.get(ctx_var)
    if existing is not None and not existing.consumed:
        detections.append(_ctx_binding_to_detection(existing))
    ctx_state[ctx_var] = _CtxBinding(info=info, direction=direction, consumed=False, common=common, fn=fn)


def _cipher_var_to_detection(binding: _CipherVarBinding) -> Detection:
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=binding.info.family,
        display_name="EVP_CIPHER_fetch(...) (cipher handle, direction unresolved in this snippet)",
        function=CryptoFunction.ENCRYPT, symbol="EVP_CIPHER_fetch", confidence=0.75,
        key_size=binding.info.key_size, mode=binding.info.mode, **binding.common,
    )


def _ctx_binding_to_detection(binding: _CtxBinding) -> Detection:
    function = CryptoFunction.ENCRYPT if binding.direction == "encrypt" else CryptoFunction.DECRYPT
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=binding.info.family,
        display_name=f"{binding.fn} (no Update observed in this snippet)", function=function,
        symbol=binding.fn, confidence=0.85, key_size=binding.info.key_size, mode=binding.info.mode,
        **binding.common,
    )


def _handle_evp_update(
    fn: str, args: list[tree_sitter.Node], ctx_state: dict[str, _CtxBinding], common: dict[str, Any],
    detections: list[Detection],
) -> None:
    if len(args) < 2 or args[0].type != "identifier":
        return
    binding = ctx_state.get(_text(args[0]))
    if binding is None or binding.consumed:
        return
    expected_direction = "encrypt" if fn == "EVP_EncryptUpdate" else "decrypt"
    if binding.direction != expected_direction:
        return
    if args[1].type == "null":
        return  # AAD-feeding call (NULL output) -- not the transformation itself
    function = CryptoFunction.ENCRYPT if expected_direction == "encrypt" else CryptoFunction.DECRYPT
    detections.append(Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=binding.info.family,
        display_name=f"{fn}(...)", function=function, symbol=fn, confidence=0.9,
        key_size=binding.info.key_size, mode=binding.info.mode, **common,
    ))
    binding.consumed = True


def _handle_evp_get_params(
    args: list[tree_sitter.Node], ctx_state: dict[str, _CtxBinding], common: dict[str, Any],
    detections: list[Detection],
) -> None:
    if len(args) < 1 or args[0].type != "identifier":
        return
    binding = ctx_state.get(_text(args[0]))
    if binding is None or binding.direction != "encrypt" or binding.info.mode not in _AEAD_MODES:
        return
    detections.append(Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=binding.info.family,
        display_name="EVP_CIPHER_CTX_get_params (AEAD tag retrieval)", function=CryptoFunction.TAG,
        symbol="EVP_CIPHER_CTX_get_params", confidence=0.82,
        key_size=binding.info.key_size, mode=binding.info.mode, **common,
    ))


def _handle_evp_decrypt_final(
    args: list[tree_sitter.Node], ctx_state: dict[str, _CtxBinding], common: dict[str, Any],
    detections: list[Detection],
) -> None:
    if len(args) < 1 or args[0].type != "identifier":
        return
    binding = ctx_state.get(_text(args[0]))
    if binding is None or binding.direction != "decrypt" or binding.info.mode not in _AEAD_MODES:
        return
    detections.append(Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=binding.info.family,
        display_name="EVP_DecryptFinal_ex (AEAD tag verify)", function=CryptoFunction.VERIFY,
        symbol="EVP_DecryptFinal_ex", confidence=0.82,
        key_size=binding.info.key_size, mode=binding.info.mode, **common,
    ))


# --- OpenSSL: self-contained patterns (no ctx linkage needed) ---------


def _openssl_md_fetch(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    if len(args) < 2:
        return None
    name = _string_literal_text(args[1])
    if name is None:
        return None
    family = _DIGEST_NAME_FAMILY.get(name)
    if family is None:
        return None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
        display_name=f'EVP_MD_fetch(..., "{name}", ...)', function=CryptoFunction.DIGEST,
        symbol=fn, confidence=0.9, **common,
    )


def _openssl_rsa_keygen_bits(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    if len(args) < 2:
        return None
    key_size = _int_literal_value(args[1])
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.RSA,
        display_name="EVP_PKEY_CTX_set_rsa_keygen_bits", function=CryptoFunction.KEYGEN,
        symbol=fn, confidence=0.92, key_size=key_size, **common,
    )


def _openssl_ec_paramgen_curve(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    if len(args) < 2:
        return None
    curve = _text(args[1])
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.ECDSA,
        display_name="EVP_PKEY_CTX_set_ec_paramgen_curve_nid", function=CryptoFunction.KEYGEN,
        symbol=fn, confidence=0.9, curve=curve, **common,
    )


_OPENSSL_HANDLERS = {
    "EVP_MD_fetch": _openssl_md_fetch,
    "EVP_PKEY_CTX_set_rsa_keygen_bits": _openssl_rsa_keygen_bits,
    "EVP_PKEY_CTX_set_ec_paramgen_curve_nid": _openssl_ec_paramgen_curve,
}


def _parse_openssl_cipher_name(name: str) -> tuple[Family | None, int | None, str | None]:
    m = _OPENSSL_CIPHER_RE.match(name)
    if m:
        return Family.AES, int(m.group(2)), m.group(3)
    if name.startswith("DES-EDE3"):
        return Family.THREE_DES, None, name[len("DES-EDE3-"):] or None
    if name.startswith("DES"):
        return Family.DES, None, name[len("DES-"):] or None
    if name.startswith("BF-"):
        return Family.BLOWFISH, None, name[len("BF-"):]
    if name.startswith("RC4"):
        return Family.RC4, None, None
    if name.startswith("ChaCha20"):
        return Family.CHACHA20, None, None
    return None, None, None


_EVP_AES_RE = re.compile(r"^EVP_aes_(\d+)_([a-z0-9]+)$")
_EVP_SHA2_RE = re.compile(r"^EVP_sha(224|256|384|512)$")
_EVP_SHA3_RE = re.compile(r"^EVP_sha3_(224|256|384|512)$")


def _classify_openssl_digest_getter(fn: str, common: dict[str, Any]) -> Detection | None:
    """Zero-arg pre-3.0 digest getters, e.g. `EVP_sha256()`, used as an
    argument to `EVP_DigestInit_ex` -- classified from the function name
    alone and safe to self-fire directly (unlike cipher getters, a digest
    has no encrypt/decrypt direction ambiguity to resolve first)."""
    if fn == "EVP_md5":
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.MD5,
            display_name=f"{fn}()", function=CryptoFunction.DIGEST, symbol=fn, confidence=0.88, **common,
        )
    if fn == "EVP_sha1":
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.SHA_1,
            display_name=f"{fn}()", function=CryptoFunction.DIGEST, symbol=fn, confidence=0.88, **common,
        )
    if _EVP_SHA2_RE.match(fn):
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.SHA_2,
            display_name=f"{fn}()", function=CryptoFunction.DIGEST, symbol=fn, confidence=0.88, **common,
        )
    if _EVP_SHA3_RE.match(fn):
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.SHA_3,
            display_name=f"{fn}()", function=CryptoFunction.DIGEST, symbol=fn, confidence=0.88, **common,
        )
    return None


# --- mbedTLS ------------------------------------------------------------


def _mbedtls_aes_setkey(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    function = CryptoFunction.ENCRYPT if fn.endswith("_enc") else CryptoFunction.DECRYPT
    key_size = _int_literal_value(args[2]) if len(args) >= 3 else None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.AES,
        display_name=fn, function=function, symbol=fn, confidence=0.9, key_size=key_size, **common,
    )


def _mbedtls_des_setkey(fn: str, _args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    function = CryptoFunction.ENCRYPT if fn.endswith("_enc") else CryptoFunction.DECRYPT
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.DES,
        display_name=fn, function=function, symbol=fn, confidence=0.9, **common,
    )


def _mbedtls_des3_setkey(fn: str, _args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    function = CryptoFunction.ENCRYPT if fn.endswith("_enc") else CryptoFunction.DECRYPT
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.THREE_DES,
        display_name=fn, function=function, symbol=fn, confidence=0.9, **common,
    )


def _mbedtls_digest_starts(family: Family) -> Any:
    def handler(fn: str, _args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=fn, function=CryptoFunction.DIGEST, symbol=fn, confidence=0.88, **common,
        )
    return handler


def _mbedtls_rsa_gen_key(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    key_size = _int_literal_value(args[3]) if len(args) >= 4 else None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.RSA,
        display_name=fn, function=CryptoFunction.KEYGEN, symbol=fn, confidence=0.92, key_size=key_size, **common,
    )


def _mbedtls_ecdsa_genkey(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    curve = _text(args[1]) if len(args) >= 2 else None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.ECDSA,
        display_name=fn, function=CryptoFunction.KEYGEN, symbol=fn, confidence=0.9, curve=curve, **common,
    )


def _mbedtls_gcm_setkey(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    if len(args) < 2 or "AES" not in _text(args[1]):
        return None
    key_size = _int_literal_value(args[3]) if len(args) >= 4 else None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.AES,
        display_name=fn, function=CryptoFunction.ENCRYPT, symbol=fn, confidence=0.88,
        mode="GCM", key_size=key_size, **common,
    )


_MBEDTLS_HANDLERS = {
    "mbedtls_aes_setkey_enc": _mbedtls_aes_setkey,
    "mbedtls_aes_setkey_dec": _mbedtls_aes_setkey,
    "mbedtls_des_setkey_enc": _mbedtls_des_setkey,
    "mbedtls_des_setkey_dec": _mbedtls_des_setkey,
    "mbedtls_des3_set2key_enc": _mbedtls_des3_setkey,
    "mbedtls_des3_set2key_dec": _mbedtls_des3_setkey,
    "mbedtls_des3_set3key_enc": _mbedtls_des3_setkey,
    "mbedtls_des3_set3key_dec": _mbedtls_des3_setkey,
    "mbedtls_sha256_starts": _mbedtls_digest_starts(Family.SHA_2),
    "mbedtls_sha256_starts_ret": _mbedtls_digest_starts(Family.SHA_2),
    "mbedtls_sha1_starts": _mbedtls_digest_starts(Family.SHA_1),
    "mbedtls_sha1_starts_ret": _mbedtls_digest_starts(Family.SHA_1),
    "mbedtls_md5_starts": _mbedtls_digest_starts(Family.MD5),
    "mbedtls_md5_starts_ret": _mbedtls_digest_starts(Family.MD5),
    "mbedtls_rsa_gen_key": _mbedtls_rsa_gen_key,
    "mbedtls_ecdsa_genkey": _mbedtls_ecdsa_genkey,
    "mbedtls_gcm_setkey": _mbedtls_gcm_setkey,
}


# --- wolfSSL --------------------------------------------------------------


def _wolfssl_aes_setkey(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    key_size_bytes = _int_literal_value(args[2]) if len(args) >= 3 else None
    dir_text = _text(args[4]) if len(args) >= 5 else ""
    function = CryptoFunction.DECRYPT if "DECRYPTION" in dir_text else CryptoFunction.ENCRYPT
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.AES,
        display_name=fn, function=function, symbol=fn, confidence=0.9,
        key_size=key_size_bytes * 8 if key_size_bytes is not None else None, **common,
    )


def _wolfssl_des3_setkey(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    dir_text = _text(args[3]) if len(args) >= 4 else ""
    function = CryptoFunction.DECRYPT if "DECRYPTION" in dir_text else CryptoFunction.ENCRYPT
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.THREE_DES,
        display_name=fn, function=function, symbol=fn, confidence=0.9, **common,
    )


def _wolfssl_make_rsa_key(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    key_size = _int_literal_value(args[1]) if len(args) >= 2 else None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.RSA,
        display_name=fn, function=CryptoFunction.KEYGEN, symbol=fn, confidence=0.92, key_size=key_size, **common,
    )


def _wolfssl_ecc_make_key(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    key_size_bytes = _int_literal_value(args[1]) if len(args) >= 2 else None
    return Detection(
        kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=Family.ECDSA,
        display_name=fn, function=CryptoFunction.KEYGEN, symbol=fn, confidence=0.88,
        key_size=key_size_bytes * 8 if key_size_bytes is not None else None, **common,
    )


def _wolfssl_hash(family: Family) -> Any:
    def handler(fn: str, _args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
        return Detection(
            kind=FindingKind.ALGORITHM, surface=Surface.SOURCE, family=family,
            display_name=fn, function=CryptoFunction.DIGEST, symbol=fn, confidence=0.88, **common,
        )
    return handler


_DIGEST_NAMES_BY_LENGTH_DESC = sorted(_DIGEST_NAME_FAMILY, key=len, reverse=True)


def _wolfssl_hmac_setkey(fn: str, args: list[tree_sitter.Node], common: dict[str, Any]) -> Detection | None:
    type_text = _text(args[1]) if len(args) >= 2 else ""
    normalized = type_text.replace("_", "").upper()
    underlying = None
    for name in _DIGEST_NAMES_BY_LENGTH_DESC:
        if name.replace("-", "") in normalized:
            underlying = _DIGEST_NAME_FAMILY[name]
            break
    return Detection(
        kind=FindingKind.PROTOCOL, surface=Surface.SOURCE, family=Family.HMAC,
        display_name=fn, function=CryptoFunction.TAG, symbol=fn, confidence=0.85,
        underlying_hash_family=underlying, **common,
    )


_WOLFSSL_HANDLERS = {
    "wc_AesSetKey": _wolfssl_aes_setkey,
    "wc_Des3_SetKey": _wolfssl_des3_setkey,
    "wc_MakeRsaKey": _wolfssl_make_rsa_key,
    "wc_ecc_make_key": _wolfssl_ecc_make_key,
    "wc_Sha256Hash": _wolfssl_hash(Family.SHA_2),
    "wc_ShaHash": _wolfssl_hash(Family.SHA_1),
    "wc_Md5Hash": _wolfssl_hash(Family.MD5),
    "wc_HmacSetKey": _wolfssl_hmac_setkey,
}
