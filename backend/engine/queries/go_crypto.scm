; Captures Go package call expressions shaped as `pkg.Func(...)`
(call_expression
  function: (selector_expression
    operand: (identifier) @call.pkg
    field: (field_identifier) @call.fn)
  arguments: (argument_list) @call.args) @call.node
