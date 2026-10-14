# Matrix Evo 1.0 — User Guide

Matrix Evo is a linear-algebra toolkit for the TI-84 Evo, written in native TI-BASIC.
It covers the computational material of Chapters 1–4 of a first linear algebra
course and shows row-reduction steps one operation at a time.

## Starting

Press `PRGM`, choose `MATRIXEV`, press `ENTER`. (Programs named `EVO…` are helpers
that `MATRIXEV` calls; you never run them directly, except `EVOTEST`, the device check.)

```text
MATRIX EVO 1.0
1:ROW REDUCTION
2:MATRIX ALGEBRA
3:VECTOR TOOLS
4:LINEAR SYSTEMS
5:SUBSPACES
6:MATRIX EDITOR
7:SETTINGS
8:EXIT
```

Choose an item with its number key. Every sub-menu ends with `BACK`.

## The three matrices: A, B and R

* **A** and **B** are your matrices. You enter them once in the **Matrix Editor**
  and they stay on the calculator between runs.
* **R** is the result slot. Every operation that produces a matrix saves it as R
  (the result screen says `SAVED AS R`). A and B are never overwritten by a
  calculation. To reuse a result, open the editor on A or B and pick
  `COPY FROM A/B/R`, then `SAVE`.
* Most single-matrix operations first ask `USE WHICH MATRIX?` (A, B or R).
* Vectors are 1×n or n×1 matrices. Vector tools use **u = A** and **v = B**.
* For systems, **A** holds the coefficients and **B** the right-hand side column.
* Size limits: you can enter matrices up to **6×6**. Results can hold up to 72 cells
  (for example [A:I] for a 6×6 inverse is 6×12 during the computation).

## Entering numbers

In the editor each cell is typed on its own line:

| You type | Stored as |
|---|---|
| `3` `-7` `⁻7` | exact integer |
| `2/5` `-3/4` `6/8` | exact fraction (6/8 becomes 3/4) |
| `1.25` `0.3` | exact fraction (5/4, 3/10) |
| `1.5/2` | exact (3/4) |
| `√(2)` `π` `2^(1/3)` | **approximate** decimal; the matrix is marked APPROX |
| empty `ENTER` | keep the current value |

Malformed entries such as `1/0`, `5/` or `1.2.3` show `INVALID ENTRY` and ask again.
Anything that is not a plain number or fraction is evaluated by the calculator
(`expr(`), so a true syntax error in such an expression stops the program with the
calculator's error screen; choose `Quit` and run `MATRIXEV` again. Your saved
matrices are not affected.

### Editor menu

```text
1:ENTER ALL CELLS     type every entry, row by row
2:EDIT ONE CELL       row, column, value
3:RESIZE              1-6 rows and columns; new cells are 0
4:MAKE IDENTITY
5:MAKE ZERO
6:COPY FROM A/B/R
7:SAVE                commit and leave
8:CANCEL              leave; the stored matrix is unchanged
```

Edits happen on a copy, so `CANCEL` always restores the previous matrix.

## Exact and approximate results

Matrix Evo does its own fraction arithmetic: every entry is a numerator and a
denominator kept in lowest terms. Results are **exact** as long as every numerator
and denominator stays below 10¹⁰ (any whole number below that is exactly
representable in the calculator's 14-digit format, so no rounding can occur).

If a computation would exceed that bound, or an input was approximate, Matrix Evo
switches to decimals and **says so**: result screens show `APPROX` in the bottom
line and text screens add `(APPROXIMATE)`. In approximate mode:

* the pivot is the largest entry in the column (partial pivoting);
* a sum that cancels to less than 10⁻¹⁰ of its larger term is treated as exactly 0.
  This keeps rounding noise from creating fake pivots. Results that depend on it,
  such as a rank or a classification, carry the APPROX warning so you can double-check.

Fractions are never guessed from decimals: a value is shown as a fraction only if
it was computed exactly.

## Result screens

```text
RREF (3X4)               MORE
RANK 2
   1   2   0    1
   0   0   1    2
   0   0   0    0

SAVED AS R   ENTER:OK
```

* Line 1 is the title, line 2 a short explanation.
* If the matrix is wider or taller than the screen, `MORE` appears; use the arrow
  keys to page.
* `ENTER` (or `CLEAR`) continues.

## Step-by-step mode

`SETTINGS > STEP-BY-STEP` switches it ON or OFF (default ON). When on, REF, RREF,
Gaussian and Gauss-Jordan elimination, inverse, determinant and the subspace
routines first open the **step viewer**:

```text
RREF STEP 2/3
R1=R1-2R2
   1   0  -1
   0   1   2
ENTER:NEXT  CLEAR:SKIP
```

* `ENTER` or `→` goes to the next operation; `←` goes back one; `CLEAR` jumps to the end.
* Step 0 is the starting matrix. Each step shows the operation and the matrix after it.
  Going back (`←`) shows the matrix before it.
* Notation: `R1<>R3` swap rows; `R2=(1/3)R2` scale; `R3=R3-2R1` replace.
* The viewer stores only the list of operations and replays them, so it works
  even for 6×12 augmented matrices.

## Menu reference

### 1 Row reduction (Chapter 1)

| Item | What it does |
|---|---|
| REF WITH STEPS | Row echelon form (pivots not scaled to 1) |
| RREF WITH STEPS | Reduced row echelon form, rank |
| GAUSSIAN ELIM. [A:B] | Forward elimination on [A:B] with steps, then back-substitution and the solution |
| GAUSS-JORDAN [A:B] | Full reduction of [A:B] with steps, then the solution |
| ELEMENTARY ROW OPS | Apply swap / scale / replace yourself to a copy; `SAVE AS R` keeps the result |
| PIVOTS AND FREE VARS | Pivot columns, free columns, rank |

### 4 Linear systems (A x = B)

| Item | What it does |
|---|---|
| SOLVE AX=B | RREF of [A:B], then one of: **no solution** (row [0 … 0 : 1]), **unique** (x saved as R), or **infinitely many**: R = [P V1 V2 …] meaning x = P + t1·V1 + t2·V2 + …, with the free variables listed |
| CONSISTENCY TEST | Compares rank A and rank [A:B] |
| HOMOGENEOUS AX=0 | Same classification for A x = 0. Column P is 0 and the V's span the null space |
| CRAMER'S RULE | x_i = det(A_i)/det(A); refuses if det(A) = 0 |

### 2 Matrix algebra (Chapter 3)

Page 1: `A+B`, `A-B`, `SCALAR K*M`, `A*B`, `A*X (X = B)`, `TRANSPOSE`, `POWER M^K`
(k = 0…99, k = 0 gives I), `MORE...`

Page 2: `IDENTITY / ZERO`, `INVERSE (STEPS)` (Gauss-Jordan on [A:I]; reports singular
matrices), `DETERMINANT (STEPS)` (REF without scaling; det = (−1)^swaps × product
of pivots), `MINOR AND COFACTOR` (shows the submatrix, M_ij and C_ij),
`COFACTOR MATRIX AND ADJ` (C, then adj(A) = Cᵀ saved as R), `CRAMER'S RULE`,
`INVERTIBLE?` (det, rank and the Invertible Matrix Theorem equivalences).

Dimension errors are explained, e.g. `A*B NEEDS … COLS A = ROWS B`.

### 3 Vector tools (Chapter 2), u = A, v = B

Page 1: `U+V`, `U-V`, `SCALAR K*U`, `DOT PRODUCT U.V` (notes orthogonality),
`NORM AND UNIT VECTOR` (exact when ‖u‖² is a ratio of perfect squares, otherwise
`SQRT(…)` plus a decimal and an APPROX unit vector), `DISTANCE NORM(U-V)`,
`CROSS PRODUCT UXV` (R³ only).

Page 2: `PROJECTION OF U ON V` (refuses v = 0; shows u·v, v·v and the coefficient),
`LINEAR COMBINATION` (columns of A weighted by B), `SPAN MEMBERSHIP` (is B a
combination of the columns of A? If yes, one set of weights).

### 5 Subspaces (Chapter 4). The vectors are the columns of the chosen matrix

Page 1: `INDEPENDENCE` (if dependent, shows weights x with A x = 0), `SPAN`
(dimension, whether it is all of Rᵐ, basis), `BASIS EXTRACTION` (pivot columns),
`BASIS TEST (R^M)`, `DIMENSION` (all four subspace dimensions), `RANK AND NULLITY`,
`COORDINATES [X]B` (basis = columns of A, x = B).

Page 2: `COLUMN SPACE COL(A)` (pivot columns of A), `ROW SPACE ROW(A)` (nonzero rows of
RREF), `NULL SPACE NUL(A)`, `LEFT NULL NUL(AT)` (null space of Aᵀ), `ALL FOUR SUBSPACES`
(dimensions, then each basis), `RANK-NULLITY CHECK` (rank A + nullity A = n and
rank Aᵀ + nullity Aᵀ = m, computed from two independent reductions).

## Worked examples

**RREF.** Editor: A = [[1,2],[2,4]]. `ROW REDUCTION > RREF > A` gives
[[1,2],[0,0]], rank 1.

**Inverse.** A = [[1,2],[3,4]]. `MATRIX ALGEBRA > MORE > INVERSE > A` gives
[[−2,1],[3/2,−1/2]].

**System with a free variable.** A = [[1,1]], B = [[3]] (1×1).
`LINEAR SYSTEMS > SOLVE` reports infinitely many solutions, FREE: X2, and
R = [[3,−1],[0,1]], i.e. x = (3,0) + t(−1,1).

**Null space.** A = [[1,2],[2,4]]. `SUBSPACES > MORE > NULL SPACE` gives the basis
{(−2,1)}.

## Feature coverage (47 capabilities)

| # | Capability | Where |
|---|---|---|
| 1.1–1.2 | REF / RREF with steps | Row reduction 1, 2 |
| 1.3–1.4 | Gaussian / Gauss-Jordan elimination | Row reduction 3, 4 |
| 1.5 | Elementary row operations | Row reduction 5 |
| 1.6 | Pivots and free variables | Row reduction 6 |
| 1.7–1.9 | Solve Ax=b, classify, parametric form | Systems 1 |
| 1.10 | Consistency test | Systems 2 |
| 1.11 | Homogeneous systems | Systems 3 |
| 2.1–2.2 | Vector add/subtract, scalar multiple | Vectors 1–3 |
| 2.3–2.6 | Dot product, norm, distance, unit vector | Vectors 4–6 |
| 2.7 | Cross product | Vectors 7 |
| 2.8–2.10 | Projection, linear combination, span membership | Vectors page 2 |
| 3.1–3.6 | Add/subtract, scalar, products, transpose, powers | Algebra page 1 |
| 3.7 | Identity / zero matrices | Algebra page 2, item 1 |
| 3.8–3.9 | Inverse and determinant with steps | Algebra page 2, items 2–3 |
| 3.10–3.11 | Minors, cofactors, cofactor matrix, adjugate | Algebra page 2, items 4–5 |
| 3.12 | Cramer's rule | Algebra page 2, item 6, and Systems 4 |
| 3.13 | Invertibility test | Algebra page 2, item 7 |
| 4.1–4.6 | Independence, span, basis extraction/test, dimension, rank & nullity | Subspaces page 1 |
| 4.7–4.11 | Column, row, null, left null space, all four | Subspaces page 2 |
| 4.12 | Rank-nullity verification | Subspaces page 2, item 6 |
| 4.13 | Coordinates relative to a basis | Subspaces page 1, item 7 |

## Variables Matrix Evo uses

Kept between runs: lists `ʟMXA`, `ʟMXB`, `ʟMXR` (the slots) and `ʟMXSET` (settings).
Scratch (overwritten freely): matrices **[G], [H], [I], [J]**, lists `ʟMXW ʟMXST ʟMXLOG
ʟMXPR ʟMXO ʟMXV ʟMXDT`, strings Str0–Str9, and the real variables A–Z and θ.
Do not keep your own data in those while using Matrix Evo. Matrix Evo also sets the
calculator to `Float` and `Normal` display modes when it starts.

To uninstall, delete the `MATRIXEV` and `EVO…` programs and the `MX…` lists
(`2nd` `MEM` › Mem Management).
