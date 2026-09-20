; Captures Go package call expressions shaped as `pkg.Func(...)`
(call_expression
  function: (selector_expression
    operand: (identifier) @call.pkg
    field: (field_identifier) @call.fn)
  arguments: (argument_list) @call.args) @call.node

; Captures every `pkg.Func` selector expression, called or not (M6: a
; function VALUE referenced without being called, e.g. `hashFunc:
; sha256.New,` or `s.BlockFunc(aes.NewCipher)`). This also matches the
; `pkg.Func` inside a real call (same node the pattern above already
; captures) -- engine/source_go.py filters those out by checking whether
; the selector is the `function` field of an enclosing call_expression,
; same dedup approach as source_python.py's `attr.node` pattern.
(selector_expression
  operand: (identifier) @attr.pkg
  field: (field_identifier) @attr.fn) @attr.node
