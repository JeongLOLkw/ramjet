"""Helpers for the I2 speed benchmark (log parsing, case scaling)."""
import re


def parse_steps(text):
    """Parse a solver log into per-step records.

    Each record: time (float), wall (s, from cumulative ExecutionTime),
    pseudo_iters (int for HiSA's dual-time loop, else None).
    """
    steps = []
    prev_exec = 0.0
    # split on lines that begin a time step
    blocks = re.split(r"(?m)^Time = ", text)[1:]
    for b in blocks:
        t = float(b.split()[0])
        m = re.search(r"ExecutionTime = ([0-9.eE+-]+) s", b)
        if not m:
            continue  # incomplete last step
        ex = float(m.group(1))
        conv = re.search(r"pseudoTime: converged in (\d+) iterations", b)
        if conv:
            it = int(conv.group(1))
        else:
            its = re.findall(r"pseudoTime: iteration (\d+)", b)
            it = int(its[-1]) if its else None
        steps.append({"time": t, "wall": ex - prev_exec, "pseudo_iters": it})
        prev_exec = ex
    return steps


def mean_step_wall(steps, skip=0):
    """Mean wall time per step, ignoring the first `skip` steps."""
    use = steps[skip:]
    if not use:
        raise ValueError("no steps left after skipping")
    return sum(s["wall"] for s in use) / len(use)


_HEX = re.compile(r"(hex\s*\([\d\s]+\)\s*\()(\d+)\s+(\d+)\s+(\d+)(\))")


def scale_blocks(text, factor):
    """Multiply the i,j cell counts of every hex block; return (text, total cells)."""
    total = 0

    def sub(m):
        nonlocal total
        i, j, k = (int(x) for x in m.group(2, 3, 4))
        i, j = round(i * factor), round(j * factor)
        total += i * j * k
        return f"{m.group(1)}{i} {j} {k}{m.group(5)}"

    return _HEX.sub(sub, text), total


def set_entry(text, key, value):
    """Replace `key  <old>;` (first occurrence at line start) with the new value."""
    pat = re.compile(rf"(?m)^(\s*{re.escape(key)}\s+)[^;]*;")
    if not pat.search(text):
        raise KeyError(key)
    return pat.sub(lambda m: f"{m.group(1)}{value};", text, count=1)
