# Matrix Evo: Complete Implementation Plan

**Project specification:** Version 1.0  
**Target:** TI-84 Evo  
**Implementation:** Native TI-BASIC, launched through `PRGM`  
**Deliverable:** An installable `.8xp2` program suite with source, tests, and documentation

> **Verification note:** The hardware-specific format, commands, and transfer workflow described below are implementation targets and must be confirmed on a physical TI-84 Evo. This is a development plan, not a claim that the application is already implemented.

## Project goal

Recreate and expand the mathematical features of [Sightem's Matrix calculator](https://github.com/Sightem/matrix) as a native TI-BASIC tool for the TI-84 Evo. Cover computational material from Chapters 1–4 of linear algebra, including step-by-step row reduction, matrix algebra, vectors, linear systems, span, independence, bases, and fundamental subspaces.

This is a **rewrite**, not a direct conversion from the original C-based CE application or from the earlier Python prototype.

## 1. Target platform and technical requirements

| Characteristic | Target |
|---|---|
| Hardware | TI-84 Evo |
| Language | TI-BASIC compatible with the Evo |
| Planned program files | `.8xp2`, subject to device validation |
| Launch method | `PRGM` menu |
| Transfer | TI Connect Evo |
| Default max matrix size | 6 × 6 |
| Numeric mode | Exact rational where safe; explicitly marked approximate otherwise |
| Network | Not needed |
| External runtime/jailbreak | Not needed |

### Non-negotiable requirements

- Run without the Python application.
- Install through the normal calculator transfer workflow.
- Work offline with no external runtime.
- Support rectangular and square matrices.
- Show row-operation explanations and intermediate matrices.
- Validate dimensions and reject undefined operations.
- Preserve user-entered matrices across menu operations.
- Protect against silent numeric precision errors.
- Remain usable on common classroom-sized problems.

A native program must be built for the Evo's real file format and token set. Renaming `.py` or `.8xp` files is not a valid conversion strategy.

## 2. Complete feature specification

### Chapter 1: Linear Systems and Row Reduction (11 features)

1. REF with steps
2. RREF with steps
3. Gaussian elimination
4. Gauss-Jordan elimination
5. Elementary row operations
6. Pivot and free-variable identification
7. Solve `Ax = b`
8. Detect unique, infinite, or no solutions
9. Parametric vector solutions
10. Consistency tests
11. Homogeneous systems `Ax = 0`

### Chapter 2: Vectors and Linear Combinations (10 features)

1. Vector addition and subtraction
2. Scalar-vector multiplication
3. Dot product
4. Magnitude/norm
5. Distance between vectors
6. Unit vectors
7. Cross product in R³
8. Orthogonal projection
9. Linear combination calculator
10. Vector span membership

### Chapter 3: Matrix Algebra (13 features)

1. Matrix addition and subtraction
2. Scalar multiplication
3. Matrix-matrix multiplication
4. Matrix-vector multiplication
5. Transpose
6. Matrix powers (nonnegative integer powers)
7. Identity and zero matrix generation
8. Inverse with steps
9. Determinant with steps
10. Minors and cofactors
11. Cofactor matrix and adjugate
12. Cramer's rule
13. Invertibility tests

### Chapter 4: Subspaces and Bases in Rⁿ (13 features)

1. Linear independence/dependence
2. Span of a set of vectors
3. Basis extraction
4. Basis validation
5. Dimension of a subspace
6. Rank and nullity
7. Column space basis
8. Row space basis
9. Null space basis
10. Left null space basis
11. Four fundamental subspaces
12. Rank-nullity theorem verification
13. Coordinates relative to a basis

**Total: 47 planned mathematical capabilities.** Many share common core algorithms. The supplied Chapter 3 and 4 slide excerpts are incomplete; full lecture decks should be reviewed before claiming comprehensive syllabus coverage.

## 3. User interface

### Main menu (concept)

```text
MATRIX EVO       v1.0
1: ROW REDUCTION
2: MATRIX ALGEBRA
3: VECTOR TOOLS
4: LINEAR SYSTEMS
5: SUBSPACES
6: MATRIX EDITOR
7: SETTINGS
0: EXIT
```

### Navigation targets

| Input | Behavior |
|---|---|
| Numeric choice | Select an operation |
| ENTER | Confirm a prompt |
| CLEAR | Cancel/back when feasible |
| Arrow keys | Navigate where supported |
| `0` | Parent menu |
| Calculator quit sequence | Exit cleanly |

Use Evo-supported variants of `Menu(`, `Input`, `Prompt`, `Disp`, `Pause`, `If`, `Then`, `Else`, `End`, and `prgm`, after testing their actual behavior.

### Matrix editor (concept)

```text
EDIT MATRIX A
ROWS: 3  COLS: 3
[ 1  2  3 ]
[ 4  5  6 ]
[ 7  8  9 ]
1: EDIT CELL
2: RESIZE
3: SAVE
0: BACK
```

### Storage model

- User slots: matrix **A**, matrix **B**.
- Result slot: matrix **R**.
- Temporary workspace for elimination, augmented matrices, cofactors, and other calculations.
- Store dimensions, entries, and exact rational metadata if rational mode is implemented.
- Avoid overwriting A/B unless explicitly requested.
- Start with a **6 × 6** maximum; revise only after memory and speed profiling.
- Clearly specify how augmented matrices fit within size limits.

## 4. Exact rational arithmetic

Represent rational numbers conceptually as `p/q`, with integer numerator `p`, positive denominator `q`, and `gcd(|p|,q)=1`.

Requirements:

- Addition, subtraction, multiplication, and division.
- Sign normalization and GCD reduction.
- Division-by-zero protection.
- Intermediate overflow and integer-precision safeguards.
- Exact comparison to zero in true rational mode.
- Explicit approximation indicators whenever exact computation cannot be guaranteed.

For example, `6/8` reduces to `3/4`; `1/3 + 1/6` returns `1/2`.

**Strategies to evaluate:**

1. Use built-in matrix operations for a faster approximate mode; display rational forms only if exact reconstruction is justified.
2. Build a dedicated rational matrix engine to preserve exactness through row operations.

TI-BASIC numeric storage may not safely represent arbitrary large integers. Define precise accepted input and intermediate bounds during implementation. Never present guessed fractions as exact.

## 5. Core algorithms

### A. Row reduction

```text
for each candidate column:
    find an eligible nonzero pivot row
    if none exists:
        record a free column and continue
    if necessary, swap the pivot row into place
    for REF: eliminate below the pivot
    for RREF: normalize pivot row and eliminate above/below
    log elementary operations
    advance the pivot row
return reduced matrix, pivot indices, rank, operation log
```

This engine supports REF, RREF, rank, independence, null spaces, and linear systems. Use exact zero tests for rational values; use documented tolerances in approximate mode.

### B. Matrix multiplication

For compatible `A` and `B`, compute:

\[
C_{ij}=\sum_{k=1}^{n} A_{ik}B_{kj}.
\]

Ensure `columns(A) = rows(B)`. Optionally display each output-cell dot product in step mode.

### C. Determinant, inverse, cofactors

- Determinant: elimination with row-swap sign tracking and pivot-product accounting.
- Inverse: Gauss-Jordan elimination on `[A | I]`, with singularity detection.
- Minor: remove a selected row and column, then compute the determinant.
- Cofactor: `(-1)^(i+j)` times the corresponding minor.
- Adjugate: transpose of the cofactor matrix.
- Cramer's rule: replace each coefficient column with `b` and divide determinants if `det(A) != 0`.
- Optional cofactor-expansion walkthrough on small matrices; use elimination by default for larger sizes.

### D. Four fundamental subspaces

For an `m × n` matrix `A`:

| Space | Method |
|---|---|
| `Col(A)` | Original columns of `A` at pivot-column indices in RREF |
| `Row(A)` | Nonzero rows of RREF |
| `Null(A)` | General solution of `Ax = 0`, using free variables |
| `Null(Aᵀ)` | Null space of the transpose |

Verify `rank(A) + nullity(A) = n` and `rank(A) + nullity(Aᵀ) = m`.

### E. Linear-system classification

Reduce `[A | b]` and classify:

- **No solution:** a row `[0 ... 0 | c]` where `c != 0`.
- **Unique solution:** consistent, with a pivot in every variable column.
- **Infinitely many solutions:** consistent, with one or more free variables.

For infinitely many solutions, output a particular solution plus the null-space basis weighted by free parameters.

## 6. Step-by-step engine

Example:

```text
RREF  STEP 1/3
R2 = R2 - 2R1
BEFORE:
[ 1  2  3 ]
[ 2  5  8 ]
AFTER:
[ 1  2  3 ]
[ 0  1  2 ]
NEXT: R1 = R1 - 2R2
```

Each step should record operation kind, row indices, and scalar factor. To reduce memory use, store concise operations and replay them against the starting matrix instead of duplicating every intermediate matrix.

Modes:

- Final answer only.
- Step by step (advance between operations).
- Normal output with optional explanatory details.

## 7. Proposed TI-BASIC program layout

```text
MATRIXEV   main launcher
EVOMENU    menus
EVOINPUT   matrix editor
EVODISP    output and paging
EVOROW     REF/RREF
EVOSTEP    step replay/display
EVOMATH    arithmetic
EVODET     determinants/cofactors
EVOINV     inverse
EVOSOLVE   linear systems
EVOVECT    vectors
EVOSPACE   subspaces
EVOFRAC    rational arithmetic
EVOUTIL    validation/helpers
```

These are proposed logical module names, **not** existing released files. Validate supported program names, calling conventions, memory usage, and state sharing on the Evo before choosing the final module boundaries.

## 8. Error handling

| Condition | Required response |
|---|---|
| Addition with unequal dimensions | Dimension mismatch |
| Incompatible matrix multiplication | Explain required matching dimension |
| Singular inverse request | No inverse exists |
| Determinant of rectangular matrix | Undefined; refuse |
| Division by zero | Stop operation safely |
| Oversized matrix | Ask for allowed dimensions |
| Inconsistent equations | Report no solution |
| Projection onto zero vector | Undefined; refuse |
| Rational overflow or unsafe precision | Stop or clearly switch to approximate mode |
| Cancel during editing | Restore previous stored matrix |

Do not allow a rounding artifact to silently change a system's classification.

## 9. Development roadmap

### Phase 1: Native Evo compatibility proof

Build a minimal real program, transfer it, launch it through `PRGM`, test inputs, menus, output, and one subprogram call.

**Exit criterion:** verified successful launch and transfer on a physical Evo.

### Phase 2: Matrix editor and storage

Implement A/B/R slots, dimensions, cell entry, validation, cancellation, and safe storage.

**Exit criterion:** repeatably enter, display, resize, and reuse matrices.

### Phase 3: Fraction engine

Implement canonical rational arithmetic, zero tests, and precision safeguards.

**Exit criterion:** exact-arithmetic reference tests pass within published bounds.

### Phase 4: Row-reduction engine

Implement elementary operations, pivots, REF, RREF, and operation logging.

**Exit criterion:** correct reductions and navigable intermediate steps.

### Phase 5: Matrix algebra

Implement Chapter 3 operations, determinant and inverse algorithms, cofactors, adjugate, and Cramer's rule.

**Exit criterion:** complete Chapter 3 reference test suite passes.

### Phase 6: Vectors and systems

Implement Chapter 1/2 vector operations, projections, and solution classifications.

**Exit criterion:** correct parametric and inconsistent-solution handling.

### Phase 7: Subspace features

Implement basis, span, independence, rank/nullity, all four subspaces, and coordinates relative to a basis.

**Exit criterion:** Chapter 4 reference tests pass.

### Phase 8: Interface and optimization

Add paging, shortened explanations, formatting, persistent settings, memory optimization, and performance tests.

**Exit criterion:** common 6 × 6 workloads are practical and navigation is robust.

### Phase 9: Release validation

Test fresh installation, error recovery, mathematical regression, program dependencies, and device compatibility.

**Exit criterion:** reproducible release ZIP ready for classroom use.

## 10. Reference tests

| Test | Input | Expected |
|---|---|---|
| RREF | `[[1,2],[2,4]]` | `[[1,2],[0,0]]` |
| Determinant | `[[1,2],[3,4]]` | `-2` |
| Inverse | `[[1,2],[3,4]]` | `[[-2,1],[3/2,-1/2]]` |
| Rank | `[[1,2],[2,4]]` | `1` |
| Null space | `[[1,2],[2,4]]` | basis `{(-2,1)}` |
| Independence | `(1,2), (2,4)` | dependent |
| Identity multiplication | `A × I` | `A` |
| Inconsistent system | `x+y=1`, `x+y=2` | no solution |
| Underdetermined system | `x+y=3` | free parameter |
| Rational arithmetic | `1/3 + 1/6` | `1/2` |

Additional cases: zero matrix, rectangular matrices, singular matrices, required row swaps, negative fractions, free-variable edge cases, near-zero decimal pivots, large rational intermediates, and maximum supported dimensions.

### Release acceptance criteria

- All advertised functions pass reference tests.
- Exact and approximate output are correctly distinguished.
- Program transfers and launches from `PRGM` on the actual TI-84 Evo.
- Repeated calculations don't corrupt stored matrices.
- Errors return to a usable screen.
- A fresh user can follow installation instructions.
- Performance and memory consumption are acceptable at the specified limits.

## 11. Release package

```text
MATRIX_EVO_RELEASE.zip
├── MATRIXEV.8xp2          # native launcher (planned)
├── EVO*.8xp2             # supporting programs (planned)
├── source/               # readable source and build setup
├── tests/                # regression fixtures and device tests
├── INSTALL.txt           # install/remove instructions
├── USER_GUIDE.pdf        # menu guide and examples
└── COMPATIBILITY.txt     # verified models/OS versions/limitations
```

The build should tokenize Evo-compatible source, validate produced containers, record checksums, and package dependencies. If tooling cannot safely generate Evo-native files, perform the first build using the device's supported editor/workflow and document that limitation.

Inspect the original project's license before reusing any code or assets. An independent implementation of the documented mathematical functionality is an alternative.

## 12. Priorities and definition of done

**Priority 1: Native reliability.** Launch via `PRGM`, enter matrices, compute REF/RREF, and show steps.

**Priority 2: Complete computational coverage.** Finish matrix algebra, linear systems, span, independence, bases, and fundamental subspaces.

**Priority 3: Explanation and polish.** Improve exact fractions, readable steps, and menu navigation.

### Definition of done

A user can power on their TI-84 Evo, open `PRGM`, launch `MATRIXEV`, enter a matrix once, choose a Chapter 1–4 operation, and receive a correct result, with intermediate steps for applicable operations.

### Reference links

- [Original Matrix repository](https://github.com/Sightem/matrix)
- [Matrix v1.2 release](https://github.com/Sightem/matrix/releases/tag/v1.2)
- [TI Connect Evo](https://connectevo.ti.com/)
