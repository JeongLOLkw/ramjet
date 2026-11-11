"""2D multi-block blockMeshDict writer with per-edge grading and circular arcs (I5 onward).

A mesh is described by named vertices in the x-y plane, quadrilateral blocks (four vertex names,
counter-clockwise), and data attached to block *edges*:
  count(a, b, n)            number of cells along the edge; it propagates to every edge reached through
                            opposite sides of blocks (an edge "family"), so it is given once per family
  grade(a, b, start=s)      geometric distribution with cell size s at vertex a  (end=s: at vertex b)
  grade_family(a, b, ...)   the same specification for every edge of the family, oriented parallel to a->b
  arc(a, b, centre)         circular arc (minor arc about `centre`) instead of a straight edge
  patch(name, type, edges)  boundary patch made of block edges
Because each edge carries its own grading, the first cell size at a wall can be held constant although
the wall-normal block edges have different lengths (blockMesh `edgeGrading`).

check() verifies the topology before blockMesh is run: counter-clockwise blocks, every edge shared by
exactly two blocks or lying in exactly one patch, one cell count per family, arcs/grades/patches on
existing edges.  render() returns the blockMeshDict body (one cell thick in z, `frontAndBack` empty).
"""
import numpy as np

from scripts.i4_cases import grading as _grading  # geometric grading (last/first ratio, last size)


def _key(a, b):
    return (a, b) if a < b else (b, a)


class BlockMesh:
    def __init__(self, z=0.005):
        self.z = z
        self.v = {}          # name -> (x, y), insertion order = vertex index
        self.blocks = []     # (name, (a, b, c, d))
        self.arcs = {}       # key -> centre (x, y)
        self.counts = {}     # key -> n as given by the user
        self.grades = {}     # key -> (vertex at the specified end, size)
        self.patches = {}    # name -> (type, [(a, b)])
        self._fam = None

    # ---------------------------------------------------------------- definition
    def vertex(self, name, x, y):
        if name in self.v:
            raise ValueError(f"vertex {name} defined twice")
        self.v[name] = (float(x), float(y))
        self._fam = None

    def block(self, name, a, b, c, d):
        for n in (a, b, c, d):
            if n not in self.v:
                raise ValueError(f"block {name}: unknown vertex {n}")
        self.blocks.append((name, (a, b, c, d)))
        self._fam = None

    def arc(self, a, b, centre):
        self.arcs[_key(a, b)] = (float(centre[0]), float(centre[1]))

    def count(self, a, b, n):
        if int(n) < 1:
            raise ValueError(f"count({a}, {b}): n must be >= 1")
        self.counts[_key(a, b)] = int(n)

    def grade(self, a, b, start=None, end=None):
        if (start is None) == (end is None):
            raise ValueError("give exactly one of start=, end=")
        self.grades[_key(a, b)] = (a, float(start)) if start is not None else (b, float(end))

    def grade_family(self, a, b, start=None, end=None):
        for u, v in self.family_edges(a, b):
            self.grade(u, v, start=start, end=end)

    def patch(self, name, typ, edges):
        self.patches.setdefault(name, (typ, []))[1].extend(edges)

    # ---------------------------------------------------------------- geometry
    def length(self, a, b):
        A, B = np.array(self.v[a]), np.array(self.v[b])
        c = self.arcs.get(_key(a, b))
        if c is None:
            return float(np.linalg.norm(B - A))
        C = np.array(c)
        ra, rb = A - C, B - C
        R = np.linalg.norm(ra)
        return float(R * np.arccos(np.clip(ra @ rb / (R * np.linalg.norm(rb)), -1.0, 1.0)))

    def arc_midpoint(self, a, b):
        C = np.array(self.arcs[_key(a, b)])
        ra, rb = np.array(self.v[a]) - C, np.array(self.v[b]) - C
        m = ra + rb
        return C + np.linalg.norm(ra) * m / np.linalg.norm(m)

    def area(self, corners):
        x, y = np.array([self.v[n] for n in corners]).T
        return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))

    # ---------------------------------------------------------------- families
    def _block_edges(self, corners):
        """Directed edges of a block: two i-edges (a->b, d->c) and two j-edges (a->d, b->c)."""
        a, b, c, d = corners
        return ((a, b), (d, c)), ((a, d), (b, c))

    def _families(self):
        """key -> (family id, sign); sign = +1 if the canonical direction of the key is parallel
        to the canonical direction of the family's first edge."""
        if self._fam is not None:
            return self._fam
        adj = {}
        for _, corners in self.blocks:
            for (e1, e2) in self._block_edges(corners):
                k1, k2 = _key(*e1), _key(*e2)
                s = (1 if e1 == k1 else -1) * (1 if e2 == k2 else -1)
                adj.setdefault(k1, []).append((k2, s))
                adj.setdefault(k2, []).append((k1, s))
        fam, fid = {}, 0
        for k0 in adj:
            if k0 in fam:
                continue
            fam[k0] = (fid, 1)
            stack = [k0]
            while stack:
                k = stack.pop()
                for k2, s in adj[k]:
                    sign = fam[k][1] * s
                    if k2 not in fam:
                        fam[k2] = (fid, sign)
                        stack.append(k2)
                    elif fam[k2][1] != sign:
                        raise ValueError(f"edge family of {k0} is not orientable (edge {k2})")
            fid += 1
        self._fam = fam
        return fam

    def family_edges(self, a, b):
        """All edges of the family of (a, b) as directed pairs parallel to a -> b."""
        fam = self._families()
        k0 = _key(a, b)
        if k0 not in fam:
            raise ValueError(f"({a}, {b}) is not a block edge")
        fid, s0 = fam[k0]
        s0 *= 1 if (a, b) == k0 else -1
        return [k if s * s0 > 0 else (k[1], k[0]) for k, (f, s) in fam.items() if f == fid]

    def n(self, a, b):
        fam = self._families()
        fid = fam[_key(a, b)][0]
        ns = {self.counts[k] for k, (f, _) in fam.items() if f == fid and k in self.counts}
        if len(ns) != 1:
            raise ValueError(f"edge family of ({a}, {b}) has {len(ns)} cell counts {sorted(ns)}; need exactly one")
        return ns.pop()

    # ---------------------------------------------------------------- distributions
    def expansion(self, u, v):
        """blockMesh expansion ratio (last cell / first cell) travelling u -> v."""
        g = self.grades.get(_key(u, v))
        n = self.n(u, v)
        if g is None or n == 1:
            return 1.0
        at, size = g
        e = _grading(size, self.length(u, v), n)[0]
        return e if at == u else 1.0 / e

    def sizes(self, u, v):
        """Cell lengths along the edge from u to v (geometric progression)."""
        n, L, e = self.n(u, v), self.length(u, v), self.expansion(u, v)
        if n == 1 or abs(e - 1.0) < 1e-12:
            return np.full(n, L / n)
        r = e ** (1.0 / (n - 1))
        return L * (r - 1) / (r**n - 1) * r ** np.arange(n)

    def cell_ratio(self, u, v):
        """Cell-to-cell size ratio (>= 1) along the edge."""
        n, e = self.n(u, v), self.expansion(u, v)
        return 1.0 if n == 1 else max(e, 1 / e) ** (1.0 / (n - 1))

    # ---------------------------------------------------------------- checks
    def check(self):
        fam = self._families()
        use = {}
        for name, corners in self.blocks:
            if self.area(corners) <= 0:
                raise ValueError(f"block {name} is not counter-clockwise (area {self.area(corners):.3g})")
            a, b, c, d = corners
            for e in ((a, b), (b, c), (c, d), (d, a)):
                use.setdefault(_key(*e), []).append(name)
        in_patch = {}
        for pname, (_, edges) in self.patches.items():
            for e in edges:
                k = _key(*e)
                if k not in use:
                    raise ValueError(f"patch {pname}: ({e[0]}, {e[1]}) is not a block edge")
                if k in in_patch:
                    raise ValueError(f"edge {k} is in patches {in_patch[k]} and {pname}")
                in_patch[k] = pname
        for k, names in use.items():
            if len(names) > 2:
                raise ValueError(f"edge {k} is used by {len(names)} blocks {names}")
            if len(names) == 2 and k in in_patch:
                raise ValueError(f"interior edge {k} (blocks {names}) is in patch {in_patch[k]}")
            if len(names) == 1 and k not in in_patch:
                raise ValueError(f"boundary edge {k} of block {names[0]} is in no patch")
        for what, keys in (("arc", self.arcs), ("count", self.counts), ("grade", self.grades)):
            for k in keys:
                if k not in use:
                    raise ValueError(f"{what} on ({k[0]}, {k[1]}), which is not a block edge")
        for k in use:
            self.n(*k)          # raises if a family has no or several counts
            self.expansion(*k)  # raises if a grading cannot be met
        return dict(blocks=len(self.blocks), vertices=len(self.v), cells=self.n_cells(),
                    families=len({f for f, _ in fam.values()}),
                    max_cell_ratio=max(self.cell_ratio(*k) for k in use))

    def n_cells(self):
        return sum(self.n(a, b) * self.n(a, d) for _, (a, b, c, d) in self.blocks)

    # ---------------------------------------------------------------- output
    def render(self):
        self.check()
        names = list(self.v)
        idx = {n: i for i, n in enumerate(names)}
        nv = len(names)
        out = ["convertToMeters 1;", "vertices", "("]
        for z in (-self.z, self.z):
            out += [f"    ({self.v[n][0]:.12g} {self.v[n][1]:.12g} {z:.12g})  // {idx[n] + (nv if z > 0 else 0)} {n}"
                    for n in names]
        out += [");", "blocks", "("]
        for name, (a, b, c, d) in self.blocks:
            ia, ib, ic, id_ = (idx[k] for k in (a, b, c, d))
            gi = (self.expansion(a, b), self.expansion(d, c))
            gj = (self.expansion(a, d), self.expansion(b, c))
            eg = " ".join(f"{g:.10g}" for g in (gi[0], gi[1], gi[1], gi[0], gj[0], gj[1], gj[1], gj[0], 1, 1, 1, 1))
            out.append(f"    hex ({ia} {ib} {ic} {id_} {ia + nv} {ib + nv} {ic + nv} {id_ + nv}) "
                       f"({self.n(a, b)} {self.n(a, d)} 1) edgeGrading ({eg})  // {name}")
        out += [");", "edges", "("]
        for (a, b) in self.arcs:
            m = self.arc_midpoint(a, b)
            for z, off in ((-self.z, 0), (self.z, nv)):
                out.append(f"    arc {idx[a] + off} {idx[b] + off} ({m[0]:.12g} {m[1]:.12g} {z:.12g})")
        out += [");", "boundary", "("]
        ccw = {}
        for _, (a, b, c, d) in self.blocks:
            for e in ((a, b), (b, c), (c, d), (d, a)):
                ccw[_key(*e)] = e          # boundary edges belong to one block: its CCW direction
        for pname, (typ, edges) in self.patches.items():
            faces = []
            for e in edges:
                a, b = ccw[_key(*e)]       # (a b b' a') then points out of the block
                faces.append(f"({idx[a]} {idx[b]} {idx[b] + nv} {idx[a] + nv})")
            out.append(f"    {pname} {{ type {typ}; faces ({' '.join(faces)}); }}")
        fb = [f"({idx[a]} {idx[d]} {idx[c]} {idx[b]})" for _, (a, b, c, d) in self.blocks] + \
             [f"({idx[a] + nv} {idx[b] + nv} {idx[c] + nv} {idx[d] + nv})" for _, (a, b, c, d) in self.blocks]
        out += [f"    frontAndBack {{ type empty; faces ({' '.join(fb)}); }}", ");", "mergePatchPairs ();", ""]
        return "\n".join(out)
