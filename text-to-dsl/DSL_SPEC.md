# DSL Specification

SDF geometry DSL for fine-tuning. Compiles to a DAG (FrozenDAG) for lowering and codegen.

## Token Vocabulary

| Token | Description | Example |
|-------|-------------|---------|
| Var | Variable reference | `%0`, `%1`, `%42` |
| Ident | Keyword or identifier | `sphere`, `box`, `unite`, `return` |
| Num | Float literal | `1.0`, `0.5`, `-1.0` |
| Lparen | Left parenthesis | `(` |
| Rparen | Right parenthesis | `)` |
| Comma | Comma separator | `,` |
| Eq | Assignment | `=` |
| Eof | End of input | — |

## Reserved Identifiers

| Identifier | Purpose |
|------------|---------|
| `sphere` | Sphere primitive (radius) |
| `box` | Box primitive (half-extents x,y,z) |
| `plane` | Plane primitive (normal nx,ny,nz, offset d) |
| `translate` | Translation transform (x,y,z) |
| `scale` | Scale transform (x,y,z) |
| `unite` | CSG union (2+ shapes) |
| `intersect` | CSG intersection (2+ shapes) |
| `subtract` | CSG subtraction (shape, shape) |
| `apply` | Apply transform to shape |
| `return` | Designate root shape |

## Numeric Format

- **Accepted:** `strtof`-compatible format (optional minus, digits, optional decimal, optional exponent)
- **Rejected:** NaN, Inf, -Inf
- **Examples:** `1.0`, `0.5`, `-1.0`, `1e-3`

## Semantic Rules

1. **Reference-before-use:** A var must be defined before it is referenced.
2. **Type discipline:** `shape_ref` must refer to a shape; `transform_ref` must refer to a transform.
3. **Canonical form:** Explicit `return` statement is required at the end.

## Program Structure

```
%0 = sphere(1.0)
%1 = box(0.5, 0.5, 0.5)
%2 = unite(%0, %1)
return %2
```

## Whitespace

Space, tab, newline allowed between tokens. Not inside tokens.

## Grammar

See [grammar.ebnf](grammar.ebnf) for the formal EBNF.
