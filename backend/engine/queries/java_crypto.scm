; Captures Java method calls shaped as `obj.method(args)` (covers
; `Cipher.getInstance(...)`, `kpg.initialize(...)`, `md.digest(...)`, etc.)
; and `new Type(args)` object creation (covers `new SecretKeySpec(...)` and
; direct BouncyCastle class usage like `new SHA256Digest()`). Semantic
; matching (which class/method pairs are real crypto usages, transformation-
; string parsing, variable-to-initialize linking) happens in Python
; (engine/source_java.py), same approach as the Go/Python detectors.

(method_invocation
  object: (identifier) @call.object
  name: (identifier) @call.name
  arguments: (argument_list) @call.args) @call.node

(object_creation_expression
  type: (type_identifier) @new.type
  arguments: (argument_list) @new.args) @new.node
