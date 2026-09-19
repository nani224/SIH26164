; Captures every plain `name(args)` C function call. OpenSSL/mbedTLS/
; wolfSSL crypto APIs are all free functions (no method-call syntax), so a
; single bare-call pattern covers all three libraries -- semantic matching
; (which function names are real crypto usages, algorithm-string/NID
; parsing) happens in Python (engine/source_c.py), same approach as the
; Go/Python/Java detectors.

(call_expression
  function: (identifier) @call.name
  arguments: (argument_list) @call.args) @call.node
