# DSL Specification

SDF geometry DSL for fine-tuning. Compiles to a DAG (FrozenDAG) for lowering and codegen.

## Token Vocabulary

| Token | Description | Example |
|-------|-------------|---------|
| ShapeVar | Shape variable reference | `s0`, `s1`, `s42` |
| TransformVar | Transform variable reference | `t0`, `t1`, `t42` |
| Ident | Keyword or identifier | `sphere`, `box`, `union`, `return` |
| Num | Float literal | `1.0`, `0.5`, `-1.0` |
| Lparen | Left parenthesis | `(` |
| Rparen | Right parenthesis | `)` |
| Comma | Comma separator | `,` |
| Eq | Assignment | `=` |
| Eof | End of input | — |

## Reserved Identifiers

| Identifier | Purpose |
|------------|---------|
| `sphere` | Sphere primitive (r=radius) |
| `box` | Box primitive (x,y,z half-extents) |
| `plane` | Plane primitive (nx,ny,nz normal, d offset) |
| `translate` | Translation transform (x,y,z) |
| `scale` | Scale transform (x,y,z) |
| `union` | CSG union (2+ shapes) |
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
s0 = sphere(r=1.0)
s1 = box(x=0.5, y=0.5, z=0.5)
s2 = union(s0, s1)
return s2
```

## Comments

Line comments: `#` or `//` to end of line. Comments are ignored by the parser.

## Whitespace

Space, tab, newline allowed between tokens. Not inside tokens.

## Canonical Form (1:1 DSL-to-DAG)

To ensure exactly one DSL script per DAG:

1. **Variable numbering:** `s0`, `s1`, ... and `t0`, `t1`, ... in definition order.
2. **Definition order:** Topological (dependencies before dependents).
3. **Parameter order:** Fixed per op (e.g. x,y,z for box/translate).
4. **Single return:** Exactly one `return` at end.

## Grammar

See [grammar.ebnf](grammar.ebnf) for the formal EBNF.
