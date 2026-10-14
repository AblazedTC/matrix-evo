# Matrix Evo

**Exact-fraction linear algebra for the TI-84 Evo, written in native TI-BASIC.**

Row reduction with step-by-step replay, matrix algebra, vectors, linear systems and
the four fundamental subspaces, covering Chapters 1–4 of a first linear algebra course
(47 capabilities). No Python app, no jailbreak, no network: just programs you launch
from `PRGM`.

```text
MATRIX EVO 1.0              RREF STEP 2/3
1:ROW REDUCTION             R1=R1-2R2
2:MATRIX ALGEBRA               1   0  -1
3:VECTOR TOOLS                 0   1   2
4:LINEAR SYSTEMS
5:SUBSPACES
6:MATRIX EDITOR
7:SETTINGS                  ENTER:NEXT  CLEAR:SKIP
8:EXIT
```

> **Status: beta.** Built and tested on a computer (file-format validation plus 66
> simulator tests). Running on a real TI-84 Evo has started: the `EVOTEST` device check
> passes its six command checks. The screen, menu and key-code checks and full
> menu testing on the device are still in progress. See
> [docs/COMPATIBILITY.txt](docs/COMPATIBILITY.txt). Bug reports are welcome.

## Features

- **Row reduction:** REF/RREF with steps, Gaussian and Gauss-Jordan elimination,
  manual elementary row operations, pivots and free variables
- **Linear systems:** solve Ax = b with classification (none / unique / infinitely many),
  parametric solutions, consistency test, homogeneous systems, Cramer's rule
- **Matrix algebra:** + − scalar ×, products, transpose, powers, identity/zero, inverse
  with steps, determinant with steps, minors, cofactors, adjugate, invertibility test
- **Vectors:** ± and scalar, dot product, norm, unit vector, distance, cross product,
  projection, linear combinations, span membership
- **Subspaces:** independence, span, basis extraction and test, dimension, rank & nullity,
  Col/Row/Nul/left Nul bases, all four at once, rank-nullity check, coordinates in a basis
- **Exact answers:** fractions such as `3/2` and `-1/2`, never guessed from decimals.
  If a number would exceed 10¹⁰, or you enter `√(2)`, the result is clearly marked
  `APPROX`.
- **Step viewer:** move forward and back through each row operation, e.g. `R3=R3-2R1`.

## Install

1. Download `MATRIX_EVO_RELEASE.zip` from
   [Releases](../../releases) and unzip it.
2. Open [TI Connect Evo](https://connectevo.ti.com/), connect the calculator, and send
   **all** `.8xp2` files (select all → drag onto the calculator). `MATRIXEV` calls
   the `EVO…` helper programs, so every file is needed.
3. On the calculator: `PRGM` → **EVOTEST** to run the device check, then
   `PRGM` → **MATRIXEV**.

Details: [docs/INSTALL.txt](docs/INSTALL.txt). Full manual: [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

### Quick start

`MATRIXEV` → **6 MATRIX EDITOR** → **A** → `ENTER` → **3 RESIZE** (2, 2) →
`ENTER` → **1 ENTER ALL CELLS** (1, 2, 3, 4) → `ENTER` → **7 SAVE**.
Then **2 MATRIX ALGEBRA** → **MORE…** → **INVERSE** → **A** gives `[[-2, 1], [3/2, -1/2]]`.

## Building from source

Requires Node.js 18+ and Python 3.10+; nothing to install.

```sh
node tools/build.mjs            # src/*.tib -> dist/*.8xp2 (+ SHA256SUMS)
python tests/test_matrix_evo.py # 66 tests, ~15 s
node tools/build.mjs --zip      # release/MATRIX_EVO_RELEASE.zip
```

The build tokenizes each program for the Evo, then re-reads the `.8xp2` it wrote and
fails if:
- the decoded text differs from the source;
- a token is missing from the Evo token table;
- a command name was stored as plain letters (e.g. a bare `Pause`).

### Repository layout

```text
src/*.tib            TI-BASIC source, one file per program (52 programs)
tools/build.mjs      tokenizer/packager with validation
tools/tivars/        tivars_lib_cpp (Evo branch) compiled to WebAssembly, MIT
tools/tibsim.py      TI-BASIC subset simulator used by the tests
tests/               reference + randomized tests that drive the real menus
docs/                INSTALL, USER_GUIDE, COMPATIBILITY
MATRIX_EVO_IMPLEMENTATION_PLAN.md   the original specification
```

Source conventions: lines starting with `//` are comments stripped at build time.
Named lists are written `ʟNAME`. String literals may only use characters the Evo
can store (the build rejects `| & ;` and `->`).

## How it works

- **Exact arithmetic:** each entry is a numerator/denominator pair (`[I]`/`[J]`
  in the workspace, flat lists `ʟMXA ʟMXB ʟMXR` for stored matrices). `EVOFRAC`
  keeps fractions reduced. Below 10¹⁰ every integer is exact in the calculator's
  14-digit format, so the exact path never rounds.
- **One engine:** `EVOROW` (REF/RREF, rank, pivot map, swap sign) powers solving,
  inverses, determinants, independence, bases and every subspace routine.
- **Steps by replay:** each elementary operation is logged as
  `{kind,row,row,num,den}`. `EVOSTEP` replays the log from the starting matrix,
  so 6×12 augmented matrices fit in memory.
- **Register discipline:** TI-BASIC only has global variables, so each program's
  header lists its inputs, outputs and the variables it overwrites.

## Credits

- `.8xp2` format and token research:
  [tivars_lib_cpp](https://github.com/adriweb/tivars_lib_cpp) (Evo branch) by Adrien
  "Adriweb" Bertrand and contributors, MIT (`tools/tivars/LICENSE`).
- Feature reference: [Sightem/matrix](https://github.com/Sightem/matrix) for the
  TI-84 Plus CE. This is an independent implementation; no code was copied.

## License

[MIT](LICENSE)
