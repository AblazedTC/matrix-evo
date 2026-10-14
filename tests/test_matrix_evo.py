"""Matrix Evo reference tests.

Runs the real src/*.tib programs in the TI-BASIC simulator (tools/tibsim.py), driving
them through their menus exactly as a user would, and checks the stored result R
(and on-screen text) against exact answers computed with Python's Fraction.

    python tests/test_matrix_evo.py          run everything
    python tests/test_matrix_evo.py -k inv   run tests whose name contains "inv"
"""
from __future__ import annotations

import sys
import traceback
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))   # release zip: tibsim.py beside this file
from tibsim import Calc, D, EndOfScript, TIError  # noqa: E402

SRC = ROOT / "src" if (ROOT / "src").is_dir() else ROOT / "source"

WARNINGS: set[str] = set()
ENTER, CLEAR, LEFT, RIGHT, UP, DOWN = 105, 45, 24, 26, 25, 34
MAIN = {"rowred": 1, "alg": 2, "vec": 3, "sys": 4, "sub": 5, "edit": 6, "set": 7, "exit": 8}


# ------------------------------------------------------------------ helpers

def slot(rows, approx=0):
    """Matrix (list of rows of int/Fraction/str) -> Matrix Evo slot list."""
    rows = [[F(x) for x in r] for r in rows]
    out = [D(len(rows)), D(len(rows[0])), D(approx)]
    for r in rows:
        for x in r:
            out += [D(x.numerator), D(x.denominator)]
    return out + [D(0)] * (147 - len(out))


def read_slot(lst):
    m, n = int(lst[0]), int(lst[1])
    vals = []
    for i in range(m):
        row = []
        for j in range(n):
            k = 3 + 2 * (i * n + j)
            num, den = lst[k], lst[k + 1]
            if num == int(num):
                row.append(F(int(num), int(den)))
            else:
                row.append(float(num) / float(den))
        vals.append(row)
    return vals, int(lst[2])


def M(*rows):
    return [[F(x) for x in r] for r in rows]


def col(*xs):
    return [[F(x)] for x in xs]


class Session:
    def __init__(self, A=None, B=None, R=None, steps=False):
        self.calc = Calc(SRC)
        c = self.calc
        c.lists["MXSET"] = [D(int(steps)), D(6), D(0), D(0), D(0), D(0), D(0), D(1)]
        for name, val in (("MXA", A), ("MXB", B), ("MXR", R)):
            if val is not None:
                c.lists[name] = slot(val) if not isinstance(val, list) or not isinstance(val[0], Decimal) else val

    def run(self, *events):
        evs = []
        for e in events:
            if isinstance(e, tuple):
                evs.append(e)
            elif isinstance(e, str):
                evs.append(("input", e))
            else:
                raise ValueError(e)
        self.calc.events = evs
        try:
            self.calc.run("MATRIXEV")
        except EndOfScript as e:
            raise AssertionError(f"script ran out (program wants {e})\n" + self.calc.transcript[-1])
        if self.calc.events:
            raise AssertionError(f"unused script events {self.calc.events}")
        WARNINGS.update(self.calc.warnings)
        return self

    @property
    def R(self):
        return read_slot(self.calc.lists["MXR"])[0]

    @property
    def R_approx(self):
        return read_slot(self.calc.lists["MXR"])[1]

    def slot(self, name):
        return read_slot(self.calc.lists[name])[0]

    def screens(self):
        return "\n".join(self.calc.transcript)

    def saw(self, text):
        assert text in self.screens(), f"expected to see {text!r} on screen\n" + self.screens()[-3000:]


def menu(n):
    return ("menu", n)


def key(k):
    return ("key", k)


OK = key(ENTER)
EXIT = menu(MAIN["exit"])


def eq(a, b):
    assert a == b, f"\n got {a}\nwant {b}"


# exact Fraction reference implementations ------------------------------

def rref(A):
    A = [list(r) for r in A]
    m, n = len(A), len(A[0])
    piv, r = [], 0
    for c in range(n):
        p = next((i for i in range(r, m) if A[i][c] != 0), None)
        if p is None:
            continue
        A[r], A[p] = A[p], A[r]
        pv = A[r][c]
        A[r] = [x / pv for x in A[r]]
        for i in range(m):
            if i != r and A[i][c] != 0:
                f = A[i][c]
                A[i] = [x - f * y for x, y in zip(A[i], A[r])]
        piv.append(c)
        r += 1
    return A, piv


def matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]


def det(A):
    n = len(A)
    if n == 1:
        return A[0][0]
    return sum((-1) ** j * A[0][j] * det([r[:j] + r[j + 1:] for r in A[1:]]) for j in range(n))


def inverse(A):
    n = len(A)
    R, piv = rref([r + [F(int(i == j)) for j in range(n)] for i, r in enumerate(A)])
    return [r[n:] for r in R]


def transpose(A):
    return [list(r) for r in zip(*A)]


# ------------------------------------------------------------------ tests
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


# --- plan section 10 reference table --------------------------------------

@test
def ref_rref_singular():
    s = Session(A=M([1, 2], [2, 4])).run(menu(1), menu(2), menu(1), OK, menu(7), EXIT)
    eq(s.R, M([1, 2], [0, 0]))
    s.saw("RANK 1")


@test
def ref_determinant():
    s = Session(A=M([1, 2], [3, 4])).run(menu(2), menu(8), menu(3), menu(1), OK, menu(8), menu(9), EXIT)
    eq(s.R, M([-2]))
    s.saw("DET = ⁻2")


@test
def ref_inverse():
    s = Session(A=M([1, 2], [3, 4])).run(menu(2), menu(8), menu(2), menu(1), OK, menu(8), menu(9), EXIT)
    eq(s.R, M([-2, 1], [F(3, 2), F(-1, 2)]))
    s.saw("3/2")


@test
def ref_rank():
    s = Session(A=M([1, 2], [2, 4])).run(menu(5), menu(6), menu(1), menu(9), EXIT)
    s.saw("RANK = 1")
    s.saw("NULLITY = 1")


@test
def ref_null_space():
    s = Session(A=M([1, 2], [2, 4])).run(menu(5), menu(8), menu(3), menu(1), OK, menu(7), menu(9), EXIT)
    eq(s.R, col(-2, 1))


@test
def ref_independence():
    s = Session(A=M([1, 2], [2, 4])).run(menu(5), menu(1), menu(1), OK, menu(9), EXIT)
    s.saw("LINEARLY DEPENDENT")
    eq(s.R, col(-2, 1))


@test
def ref_identity_multiplication():
    A = M([1, 2, 3], [4, 5, 6])
    I3 = M([1, 0, 0], [0, 1, 0], [0, 0, 1])
    s = Session(A=A, B=I3).run(menu(2), menu(4), OK, menu(9), EXIT)
    eq(s.R, A)


@test
def ref_inconsistent_system():
    s = Session(A=M([1, 1], [1, 1]), B=col(1, 2)).run(menu(4), menu(1), OK, menu(5), EXIT)
    s.saw("NO SOLUTION")


@test
def ref_underdetermined_system():
    s = Session(A=M([1, 1]), B=col(3)).run(menu(4), menu(1), OK, OK, menu(5), EXIT)
    s.saw("INFINITELY MANY")
    s.saw("FREE: X2")
    eq(s.R, M([3, -1], [0, 1]))   # x = (3,0) + t(-1,1)


@test
def ref_rational_arithmetic():
    c = Calc(SRC)
    c.reals.update(P=D(1), Q=D(3), R=D(1), S=D(6), O=D(1), V=D(0))
    c.call("EVOFRAC")
    eq((c.reals["P"], c.reals["Q"]), (D(1), D(2)))
    c.reals.update(P=D(6), Q=D(8), R=D(0), S=D(1), O=D(1))
    c.call("EVOFRAC")
    eq((c.reals["P"], c.reals["Q"]), (D(3), D(4)))


# --- additional cases -------------------------------------------------------

@test
def rref_needs_row_swap_and_fractions():
    A = M([0, 2, 4, 2], [3, 1, 0, -1], [1, 1, 1, 1])
    s = Session(A=A).run(menu(1), menu(2), menu(1), OK, menu(7), EXIT)
    eq(s.R, rref(A)[0])
    assert s.R_approx == 0


@test
def ref_matches_echelon_form():
    A = M([2, 4, -2], [4, 9, -3], [-2, -3, 7])
    s = Session(A=A).run(menu(1), menu(1), menu(1), OK, menu(7), EXIT)
    eq(s.R, M([2, 4, -2], [0, 1, 1], [0, 0, 4]))


@test
def rref_rectangular_wide_and_tall():
    for A in (M([1, 2, 3, 4], [2, 4, 6, 9]), M([1, 2], [3, 4], [5, 6], [7, 9])):
        s = Session(A=A).run(menu(1), menu(2), menu(1), OK, menu(7), EXIT)
        eq(s.R, rref(A)[0])


@test
def rref_zero_matrix():
    s = Session(A=M([0, 0, 0], [0, 0, 0])).run(menu(1), menu(2), menu(1), OK, menu(7), EXIT)
    eq(s.R, M([0, 0, 0], [0, 0, 0]))
    s.saw("RANK 0")


@test
def rref_with_steps_navigation():
    A = M([1, 2, 3], [2, 5, 8])
    # step screens: START, op1, op2 (back to op1), op2, final ENTER exits viewer
    s = Session(A=A, steps=True).run(menu(1), menu(2), menu(1),
                                     OK, OK, key(LEFT), OK, OK, OK, menu(7), EXIT)
    eq(s.R, rref(A)[0])
    s.saw("RREF STEP 1/2")
    s.saw("R2=R2-2R1")
    s.saw("R1=R1-2R2")


@test
def steps_clear_skips_to_result():
    A = M([2, 1], [1, 3])
    s = Session(A=A, steps=True).run(menu(1), menu(2), menu(1), OK, key(CLEAR), OK, menu(7), EXIT)
    eq(s.R, M([1, 0], [0, 1]))
    s.saw("R1=(1/2)R1")


@test
def gaussian_elimination_unique():
    A = M([2, 1, -1], [-3, -1, 2], [-2, 1, 2])
    b = col(8, -11, -3)
    s = Session(A=A, B=b).run(menu(1), menu(3), OK, OK, menu(7), EXIT)
    s.saw("UNIQUE SOLUTION")
    eq(s.R, col(2, 3, -1))


@test
def gauss_jordan_with_steps():
    A = M([1, 1], [1, -1])
    b = col(3, 1)
    s = Session(A=A, B=b, steps=True).run(menu(1), menu(4), key(CLEAR), OK, OK, menu(7), EXIT)
    eq(s.R, col(2, 1))
    s.saw("G-JORDAN STEP")


@test
def pivots_and_free_variables():
    A = M([1, 2, 0, 3], [0, 0, 1, 4], [1, 2, 1, 7])
    s = Session(A=A).run(menu(1), menu(6), menu(1), OK, menu(7), EXIT)
    s.saw("PIVOT COLUMNS: 1 3")
    s.saw("FREE COLUMNS: 2 4")


@test
def manual_row_operations():
    A = M([1, 2], [3, 4])
    s = Session(A=A).run(menu(1), menu(5), menu(1),
                         OK, menu(3), "2", "1", "-3",      # R2 = R2 - 3R1
                         OK, menu(2), "2", "-1/2",         # R2 = (-1/2)R2
                         OK, menu(1), "1", "2",            # swap
                         OK, menu(4), OK, menu(7), EXIT)
    eq(s.R, M([0, 1], [1, 2]))
    s.saw("R2=R2-3R1")
    s.saw("R2=-(1/2)R2")
    s.saw("R1<>R2")
    eq(s.slot("MXA"), A)  # the stored matrix is untouched


@test
def parametric_solution_two_free_vars():
    A = M([1, 2, -1, 3], [2, 4, 0, 2])
    b = col(4, 6)
    s = Session(A=A, B=b).run(menu(4), menu(1), OK, OK, menu(5), EXIT)
    s.saw("FREE: X2 X4")
    P = [r[0] for r in s.R]
    V1 = [r[1] for r in s.R]
    V2 = [r[2] for r in s.R]
    for t1, t2 in ((0, 0), (1, 0), (0, 1), (F(2, 3), -5)):
        x = [[p + t1 * a + t2 * c] for p, a, c in zip(P, V1, V2)]
        eq(matmul(A, x), b)


@test
def consistency_test():
    s = Session(A=M([1, 2], [2, 4]), B=col(3, 6)).run(menu(4), menu(2), menu(5), EXIT)
    s.saw("CONSISTENT")
    s = Session(A=M([1, 2], [2, 4]), B=col(3, 7)).run(menu(4), menu(2), menu(5), EXIT)
    s.saw("INCONSISTENT")


@test
def homogeneous_system():
    A = M([1, 2, 3], [4, 5, 6], [7, 8, 9])
    s = Session(A=A).run(menu(4), menu(3), OK, OK, menu(5), EXIT)
    s.saw("INFINITELY MANY")
    eq(s.R, M([0, 1], [0, -2], [0, 1]))


@test
def homogeneous_trivial():
    s = Session(A=M([1, 2], [3, 4])).run(menu(4), menu(3), OK, OK, menu(5), EXIT)
    s.saw("UNIQUE SOLUTION")
    eq(s.R, col(0, 0))


@test
def dimension_mismatch_messages():
    s = Session(A=M([1, 2]), B=M([1, 2, 3])).run(menu(2), menu(1), menu(9), EXIT)
    s.saw("DIMENSION MISMATCH")
    s = Session(A=M([1, 2]), B=M([1, 2])).run(menu(2), menu(4), menu(9), EXIT)
    s.saw("DIMENSION MISMATCH")
    s = Session(A=M([1, 2]), B=col(1, 2)).run(menu(4), menu(1), menu(5), EXIT)
    s.saw("DIMENSION MISMATCH")


# --- Chapter 3 ----------------------------------------------------------------

@test
def add_subtract_scalar():
    A, B = M([1, F(1, 2)], [F(-2, 3), 4]), M([F(1, 3), F(1, 2)], [1, -4])
    s = Session(A=A, B=B).run(menu(2), menu(1), OK, menu(9), EXIT)
    eq(s.R, [[a + b for a, b in zip(ra, rb)] for ra, rb in zip(A, B)])
    s = Session(A=A, B=B).run(menu(2), menu(2), OK, menu(9), EXIT)
    eq(s.R, [[a - b for a, b in zip(ra, rb)] for ra, rb in zip(A, B)])
    s = Session(A=A, B=B).run(menu(2), menu(3), menu(2), "-3/4", OK, menu(9), EXIT)
    eq(s.R, [[F(-3, 4) * b for b in r] for r in B])


@test
def matrix_products():
    A = M([1, 2, 3], [4, 5, 6])
    B = M([F(1, 2), 0], [1, -1], [2, F(1, 3)])
    s = Session(A=A, B=B).run(menu(2), menu(4), OK, menu(9), EXIT)
    eq(s.R, matmul(A, B))
    x = col(1, -1, 2)
    s = Session(A=A, B=x).run(menu(2), menu(5), OK, menu(9), EXIT)
    eq(s.R, matmul(A, x))


@test
def transpose_and_power():
    A = M([1, 2, 3], [4, 5, 6])
    s = Session(A=A).run(menu(2), menu(6), menu(1), OK, menu(9), EXIT)
    eq(s.R, transpose(A))
    S = M([1, 1], [1, 0])
    s = Session(A=S).run(menu(2), menu(7), menu(1), "10", OK, menu(9), EXIT)
    eq(s.R, M([89, 55], [55, 34]))
    s = Session(A=S).run(menu(2), menu(7), menu(1), "0", OK, menu(9), EXIT)
    eq(s.R, M([1, 0], [0, 1]))
    s = Session(A=S).run(menu(2), menu(7), menu(1), "1", OK, menu(9), EXIT)
    eq(s.R, S)


@test
def identity_and_zero():
    s = Session().run(menu(2), menu(8), menu(1), menu(1), "3", OK, menu(8), menu(9), EXIT)
    eq(s.R, M([1, 0, 0], [0, 1, 0], [0, 0, 1]))
    s = Session().run(menu(2), menu(8), menu(1), menu(2), "2", "3", OK, menu(8), menu(9), EXIT)
    eq(s.R, M([0, 0, 0], [0, 0, 0]))


@test
def inverse_3x3_with_steps():
    A = M([2, -1, 0], [-1, 2, -1], [0, -1, 2])
    s = Session(A=A, steps=True).run(menu(2), menu(8), menu(2), menu(1), key(CLEAR), OK, menu(8), menu(9), EXIT)
    eq(s.R, inverse(A))
    eq(matmul(A, s.R), M([1, 0, 0], [0, 1, 0], [0, 0, 1]))


@test
def inverse_singular():
    s = Session(A=M([1, 2], [2, 4])).run(menu(2), menu(8), menu(2), menu(1), OK, menu(8), menu(9), EXIT)
    s.saw("NO INVERSE EXISTS")


@test
def determinant_requires_square():
    s = Session(A=M([1, 2, 3])).run(menu(2), menu(8), menu(3), menu(1), menu(8), menu(9), EXIT)
    s.saw("NEED A SQUARE MATRIX")


@test
def determinant_4x4_with_swaps():
    A = M([0, 1, 2, 3], [1, 0, 1, 0], [2, 3, 0, 1], [1, 1, 1, 2])
    s = Session(A=A).run(menu(2), menu(8), menu(3), menu(1), OK, menu(8), menu(9), EXIT)
    eq(s.R, M([det(A)]))


@test
def minor_and_cofactor():
    A = M([1, 2, 3], [0, 4, 5], [1, 0, 6])
    s = Session(A=A).run(menu(2), menu(8), menu(4), menu(1), "1", "2", OK, menu(8), menu(9), EXIT)
    # M12 = det([[0,5],[1,6]]) = -5 ; C12 = 5
    s.saw("MINOR M12 = ⁻5")
    eq(s.R, M([5]))


@test
def cofactor_matrix_and_adjugate():
    A = M([1, 2, 3], [0, 4, 5], [1, 0, 6])
    s = Session(A=A).run(menu(2), menu(8), menu(5), menu(1), OK, OK, menu(8), menu(9), EXIT)
    adj = s.R
    eq(matmul(A, adj), [[det(A) * int(i == j) for j in range(3)] for i in range(3)])


@test
def cramers_rule():
    A = M([2, 1, -1], [-3, -1, 2], [-2, 1, 2])
    b = col(8, -11, -3)
    s = Session(A=A, B=b).run(menu(2), menu(8), menu(6), OK, menu(8), menu(9), EXIT)
    eq(s.R, col(2, 3, -1))
    s.saw("DET(A) = ⁻1")


@test
def cramers_rule_singular():
    s = Session(A=M([1, 2], [2, 4]), B=col(1, 2)).run(menu(4), menu(4), menu(5), EXIT)
    s.saw("CRAMER'S RULE DOES")


@test
def invertibility_test():
    s = Session(A=M([1, 2], [3, 4])).run(menu(2), menu(8), menu(7), menu(1), menu(8), menu(9), EXIT)
    s.saw("INVERTIBLE, SINCE:")
    s = Session(A=M([1, 2], [2, 4])).run(menu(2), menu(8), menu(7), menu(1), menu(8), menu(9), EXIT)
    s.saw("NOT INVERTIBLE, SINCE:")
    s = Session(A=M([1, 2, 3])).run(menu(2), menu(8), menu(7), menu(1), menu(8), menu(9), EXIT)
    s.saw("NOT SQUARE")


# --- Chapter 2 ----------------------------------------------------------------

U3, V3 = col(1, 2, 2), M([3, 0, 4])


@test
def vector_add_sub_scale():
    s = Session(A=U3, B=V3).run(menu(3), menu(1), OK, menu(9), EXIT)
    eq(s.R, col(4, 2, 6))
    s = Session(A=U3, B=V3).run(menu(3), menu(2), OK, menu(9), EXIT)
    eq(s.R, col(-2, 2, -2))
    s = Session(A=U3, B=V3).run(menu(3), menu(3), "1/2", OK, menu(9), EXIT)
    eq(s.R, col(F(1, 2), 1, 1))


@test
def dot_product_and_orthogonal():
    s = Session(A=U3, B=V3).run(menu(3), menu(4), menu(9), EXIT)
    eq(s.R, M([11]))
    s = Session(A=col(1, -1), B=col(1, 1)).run(menu(3), menu(4), menu(9), EXIT)
    s.saw("ORTHOGONAL")


@test
def norm_exact_and_unit_vector():
    s = Session(A=U3).run(menu(3), menu(5), OK, menu(9), EXIT)
    s.saw("NORM(U) = 3")
    eq(s.R, col(F(1, 3), F(2, 3), F(2, 3)))
    assert s.R_approx == 0


@test
def norm_irrational_is_marked_approximate():
    s = Session(A=col(1, 1)).run(menu(3), menu(5), OK, menu(9), EXIT)
    s.saw("NORM(U) = SQRT(2)")
    s.saw("(APPROX)")
    assert s.R_approx == 1
    vals = s.R
    assert abs(vals[0][0] - 2 ** -0.5) < 1e-9


@test
def distance():
    s = Session(A=col(1, 2), B=col(4, 6)).run(menu(3), menu(6), menu(9), EXIT)
    s.saw("NORM(U-V) = 5")


@test
def cross_product():
    s = Session(A=col(1, 2, 3), B=col(4, 5, 6)).run(menu(3), menu(7), OK, menu(9), EXIT)
    eq(s.R, col(-3, 6, -3))
    s = Session(A=col(1, 2), B=col(4, 5)).run(menu(3), menu(7), menu(9), EXIT)
    s.saw("TWO VECTORS IN R^3")


@test
def projection():
    s = Session(A=col(2, 3), B=col(1, 1)).run(menu(3), menu(8), menu(1), OK, menu(4), menu(9), EXIT)
    eq(s.R, col(F(5, 2), F(5, 2)))
    s = Session(A=col(2, 3), B=col(0, 0)).run(menu(3), menu(8), menu(1), menu(4), menu(9), EXIT)
    s.saw("CANNOT PROJECT ONTO")


@test
def linear_combination():
    A = M([1, 0], [0, 1], [1, 1])
    s = Session(A=A, B=col(2, -3)).run(menu(3), menu(8), menu(2), OK, menu(4), menu(9), EXIT)
    eq(s.R, col(2, -3, -1))


@test
def span_membership():
    A = M([1, 0], [0, 1], [1, 1])
    s = Session(A=A, B=col(2, 3, 5)).run(menu(3), menu(8), menu(3), OK, menu(4), menu(9), EXIT)
    s.saw("YES: B IS IN THE SPAN")
    eq(s.R, col(2, 3))
    s = Session(A=A, B=col(2, 3, 4)).run(menu(3), menu(8), menu(3), menu(4), menu(9), EXIT)
    s.saw("NO: B IS NOT IN THE")


@test
def vector_validation():
    s = Session(A=M([1, 2], [3, 4]), B=col(1, 2)).run(menu(3), menu(1), menu(9), EXIT)
    s.saw("U = A IS NOT A VECTOR")
    s = Session(A=col(1, 2), B=col(1, 2, 3)).run(menu(3), menu(1), menu(9), EXIT)
    s.saw("SAME LENGTH AS U")


# --- Chapter 4 ----------------------------------------------------------------

A4 = M([1, 2, 0, 1], [2, 4, 1, 4], [3, 6, 1, 5])   # rank 2


@test
def span_and_basis():
    s = Session(A=A4).run(menu(5), menu(2), menu(1), OK, menu(9), EXIT)
    s.saw("HAS DIMENSION 2")
    s.saw("THEY DO NOT SPAN R^3")
    eq(s.R, M([1, 0], [2, 1], [3, 1]))
    s = Session(A=A4).run(menu(5), menu(3), menu(1), OK, menu(9), EXIT)
    eq(s.R, M([1, 0], [2, 1], [3, 1]))
    s.saw("COLUMNS 1 3 OF THE MATRIX")


@test
def basis_test():
    s = Session(A=M([1, 1], [0, 1])).run(menu(5), menu(4), menu(1), menu(9), EXIT)
    s.saw("YES: A BASIS OF R^2")
    s = Session(A=A4).run(menu(5), menu(4), menu(1), menu(9), EXIT)
    s.saw("NO: NOT A BASIS OF R^3")
    s.saw("VECTORS ARE DEPENDENT")


@test
def dimension_and_rank_nullity():
    s = Session(A=A4).run(menu(5), menu(5), menu(1), menu(9), EXIT)
    s.saw("DIM NUL(A) = 2")
    s.saw("DIM NUL(AT) = 1")
    s = Session(A=A4).run(menu(5), menu(6), menu(1), menu(9), EXIT)
    s.saw("RANK + NULLITY = 4")


@test
def coordinates_relative_to_basis():
    Bm = M([1, 1], [1, -1])
    s = Session(A=Bm, B=col(3, 1)).run(menu(5), menu(7), OK, menu(9), EXIT)
    eq(s.R, col(2, 1))
    s = Session(A=M([1, 2], [2, 4]), B=col(1, 2)).run(menu(5), menu(7), menu(9), EXIT)
    s.saw("DEPENDENT: NOT A BASIS")


@test
def four_fundamental_subspaces():
    A = A4
    Rr, piv = rref(A)
    # column space
    s = Session(A=A).run(menu(5), menu(8), menu(1), menu(1), OK, menu(7), menu(9), EXIT)
    eq(s.R, [[A[i][j] for j in piv] for i in range(3)])
    # row space
    s = Session(A=A).run(menu(5), menu(8), menu(2), menu(1), OK, menu(7), menu(9), EXIT)
    eq(s.R, Rr[:2])
    # null space: every basis vector solves Ax = 0 and there are n - r of them
    s = Session(A=A).run(menu(5), menu(8), menu(3), menu(1), OK, menu(7), menu(9), EXIT)
    eq(len(s.R[0]), 2)
    eq(matmul(A, s.R), [[0, 0]] * 3)
    # left null space
    s = Session(A=A).run(menu(5), menu(8), menu(4), menu(1), OK, menu(7), menu(9), EXIT)
    eq(matmul(transpose(A), s.R), [[0]] * 4)
    eq(len(s.R[0]), 1)
    # all four in one pass
    s = Session(A=A).run(menu(5), menu(8), menu(5), menu(1), OK, OK, OK, OK, menu(7), menu(9), EXIT)
    s.saw("NUL(AT): DIM 1 IN R^3")
    eq(matmul(transpose(A), s.R), [[0]] * 4)


@test
def rank_nullity_check():
    s = Session(A=A4).run(menu(5), menu(8), menu(6), menu(1), menu(7), menu(9), EXIT)
    s.saw("RANK-NULLITY VERIFIED")
    s.saw("ROW RANK = COLUMN RANK")


@test
def full_rank_null_space_is_zero():
    s = Session(A=M([1, 2], [3, 4])).run(menu(5), menu(8), menu(3), menu(1), menu(7), menu(9), EXIT)
    s.saw("NULL SPACE = {0}")


# --- editor, storage, settings ---------------------------------------------------

@test
def editor_enter_all_and_save():
    s = Session().run(menu(6), menu(1), OK, menu(3), "2", "3",   # resize to 2x3
                      OK, menu(1), "1", "-2/4", "0.25", "3", "", "⁻7",
                      OK, menu(7), EXIT)
    eq(s.slot("MXA"), M([1, F(-1, 2), F(1, 4)], [3, 0, -7]))


@test
def editor_cancel_keeps_matrix():
    A = M([1, 2], [3, 4])
    s = Session(A=A).run(menu(6), menu(1), OK, menu(2), "1", "1", "99", OK, menu(8), EXIT)
    eq(s.slot("MXA"), A)


@test
def editor_rejects_bad_input():
    s = Session().run(menu(6), menu(2), OK, menu(2), "3", "1", "2", "1/0", "1.2.3", "5/", "7/3",
                      OK, menu(7), EXIT)
    eq(s.slot("MXB")[0][1], F(7, 3))
    s.saw("INVALID ENTRY")


@test
def editor_identity_copy_and_approx_entry():
    s = Session(R=M([5, 6])).run(menu(6), menu(1), OK, menu(4), "3", OK, menu(7), EXIT)
    eq(s.slot("MXA"), M([1, 0, 0], [0, 1, 0], [0, 0, 1]))
    s = Session(R=M([5, 6])).run(menu(6), menu(2), OK, menu(6), menu(3), OK, menu(7), EXIT)
    eq(s.slot("MXB"), M([5, 6]))
    s = Session().run(menu(6), menu(1), OK, menu(2), "1", "1", "√(2)", OK, menu(7), EXIT)
    assert read_slot(s.calc.lists["MXA"])[1] == 1


@test
def results_do_not_corrupt_inputs():
    A, B = M([1, 2], [3, 4]), M([5, 6], [7, 8])
    s = Session(A=A, B=B).run(menu(2), menu(4), OK, menu(1), OK, menu(8), menu(2), menu(1), OK,
                              menu(3), menu(1), OK, menu(8), menu(9), EXIT)
    eq(s.slot("MXA"), A)
    eq(s.slot("MXB"), B)


@test
def settings_toggle_steps_and_first_run_init():
    c = Calc(SRC)
    c.events = [menu(7), menu(1), menu(4), EXIT]
    c.run("MATRIXEV")
    assert c.lists["MXSET"][0] == 0      # first run defaults to steps on, toggled off
    eq(read_slot(c.lists["MXA"])[0], M([0, 0], [0, 0]))


@test
def approximate_mode_overflow_is_flagged():
    big = 99999
    A = M([big, 1, 0], [1, big, 1], [0, 1, big])
    s = Session(A=A).run(menu(2), menu(8), menu(2), menu(1), OK, menu(8), menu(9), EXIT)
    ref = inverse(A)
    got = s.R
    if s.R_approx:
        for gr, rr in zip(got, ref):
            for g, r in zip(gr, rr):
                assert abs(float(g) - float(r)) <= 1e-9 * abs(float(r)), (g, r)
        s.saw("APPROX")
    else:
        eq(got, ref)


@test
def approximate_entries_keep_singular_classification():
    # [[√2, 2], [1, √2]] is singular; rounding must not turn rank 1 into rank 2
    s = Session().run(menu(6), menu(1), OK, menu(1), "√(2)", "2", "1", "√(2)", OK, menu(7),
                      menu(1), menu(2), menu(1), OK, menu(7), EXIT)
    s.saw("RANK 1")
    s.saw("APPROX")
    assert s.R_approx == 1
    assert s.R[1] == [0, 0]


@test
def max_size_6x6_inverse():
    A = [[F(1, i + j + 1) for j in range(4)] for i in range(4)]  # Hilbert 4x4: exact fractions
    s = Session(A=A).run(menu(2), menu(8), menu(2), menu(1), OK, menu(8), menu(9), EXIT)
    eq(s.R, inverse(A))
    A6 = [[F((i * 7 + j * 3) % 5 - 2 + (i == j) * 6) for j in range(6)] for i in range(6)]
    s = Session(A=A6).run(menu(2), menu(8), menu(2), menu(1), OK, menu(8), menu(9), EXIT)
    eq(s.R, inverse(A6))
    s = Session(A=A6).run(menu(2), menu(8), menu(3), menu(1), OK, menu(8), menu(9), EXIT)
    eq(s.R, M([det(A6)]))


# --- randomized cross-checks against exact Fraction arithmetic ----------------

def rand_matrix(rng, m, n):
    pool = [0, 0, 1, -1, 2, -3, 5, F(1, 2), F(-2, 3), F(3, 4), 7]
    return [[F(rng.choice(pool)) for _ in range(n)] for _ in range(m)]


def engine(A, F_mode):
    c = Calc(SRC)
    c.lists["MXA"] = slot(A)
    c.reals.update(Z=D(1), V=D(0))
    c.call("EVOLOAD")
    c.reals.update(F=D(F_mode), E=c.reals["N"], L=D(0))
    c.call("EVOROW")
    m, n = int(c.reals["M"]), int(c.reals["N"])
    out = [[F(int(c.mats["I"][i][j]), int(c.mats["J"][i][j])) for j in range(n)] for i in range(m)]
    piv = [j for j in range(n) if c.lists["MXPR"][j] != 0]
    return c, out, piv


@test
def fuzz_rref_rank_det():
    import random
    rng = random.Random(2026)
    for trial in range(150):
        m, n = rng.randint(1, 5), rng.randint(1, 6)
        A = rand_matrix(rng, m, n)
        c, R, piv = engine(A, 2)
        want, wpiv = rref(A)
        assert c.reals["V"] == 0, "unexpected approximate mode"
        eq(R, want)
        eq(piv, wpiv)
        eq(int(c.reals["U"]), len(wpiv))
        # every stored fraction is in lowest terms with a positive denominator
        for i in range(m):
            for j in range(n):
                p, q = int(c.mats["I"][i][j]), int(c.mats["J"][i][j])
                assert q > 0 and F(p, q).denominator == q
        if m == n:
            c = Calc(SRC)
            c.lists["MXA"] = slot(A)
            c.reals.update(Z=D(1), V=D(0))
            c.call("EVOLOAD")
            c.call("EVODETC")
            eq(F(int(c.reals["P"]), int(c.reals["Q"])), det(A))


@test
def fuzz_inverse_and_null_space_via_menus():
    import random
    rng = random.Random(84)
    for trial in range(25):
        n = rng.randint(1, 4)
        A = rand_matrix(rng, n, n)
        s = Session(A=A).run(menu(2), menu(8), menu(2), menu(1), OK, menu(8), menu(9), EXIT)
        if det(A) != 0:
            eq(s.R, inverse(A))
        else:
            s.saw("NO INVERSE EXISTS")
        m, k = rng.randint(1, 4), rng.randint(2, 5)
        A = rand_matrix(rng, m, k)
        r = len(rref(A)[1])
        s = Session(A=A).run(menu(5), menu(8), menu(3), menu(1), *([OK] if r < k else []), menu(7), menu(9), EXIT)
        if r < k:
            eq(len(s.R[0]), k - r)
            eq(matmul(A, s.R), [[0] * (k - r)] * m)
            eq(len(rref(transpose(s.R))[1]), k - r)   # basis vectors are independent


# ------------------------------------------------------------------ runner

def main(argv):
    pat = argv[argv.index("-k") + 1] if "-k" in argv else ""
    failed = 0
    ran = 0
    for t in TESTS:
        if pat not in t.__name__:
            continue
        ran += 1
        try:
            t()
            print(f"PASS  {t.__name__}")
        except (AssertionError, TIError, Exception) as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}: {type(e).__name__}: {e}")
            if "-v" in argv:
                traceback.print_exc()
    for w in sorted(WARNINGS):
        print("WARN ", w)
    print(f"\n{ran - failed}/{ran} passed, {len(WARNINGS)} screen-layout warnings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
