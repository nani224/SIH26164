; Captures every call expression shaped either as `module.attr(...)` or a
; bare `name(...)`. Semantic matching (which module/attr pairs are actual
; crypto usages, and extracting their arguments) happens in Python
; (engine/source_python.py) rather than in query predicates, since the
; patterns we need (kwarg lookup, positional-arg text) are easier and more
; robustly expressed there than in tree-sitter's predicate syntax.

(call
  function: (attribute
    object: (_) @call.object
    attribute: (identifier) @call.attr)
  arguments: (argument_list) @call.args) @call.node

(call
  function: (identifier) @call.name
  arguments: (argument_list) @call.args) @call.node

(attribute
  object: (identifier) @attr.object
  attribute: (identifier) @attr.name) @attr.node
