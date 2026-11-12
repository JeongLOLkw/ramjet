#!/usr/bin/env python3
"""GCE cost of this project reconstructed from the Cloud Audit Logs (not the billing console).

Usage:  python3 scripts/cloud/cost_report.py [--days 30] [--since 2026-11-11]

VM running time = intervals between start/insert requests and stop/guestTerminate/delete events (Admin Activity and
System Event audit logs). Rates are the official Cloud Billing Catalog prices for us-central1 (USD; T2D queried
2026-11-13: core 0.027502 $/vCPU-h, RAM 0.003686 $/GiB-h; C2D from decisions.md D-014), Balanced PD 0.10 $/GiB-month,
in-use external IPv4 0.005 $/h. Machine type and boot disk size come from each instance's insert request in the log.
NOT included: Cloud Storage (bucket, a few GB, cents/month), network egress (result downloads, ~0.12 $/GB),
free-trial credits/discounts. The billing console is the authoritative number.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

PROJECT = "project-03050886-e5fd-4c6a-a2a"
RATES = dict(ip=0.005, disk_month=0.10)   # USD, us-central1, 2026-11-13
# vCPU, GiB, $/vCPU-h, $/GiB-h (on-demand, us-central1; T2D queried 2026-11-13, C2D from decisions.md D-014)
TYPES = {"t2d-standard-4": (4, 16, 0.027502, 0.003686), "t2d-standard-8": (8, 32, 0.027502, 0.003686),
         "c2d-standard-8": (8, 32, 0.02956, 0.00396)}
HOURS_PER_MONTH = 730.0
ON = ("v1.compute.instances.insert", "v1.compute.instances.start")
OFF = ("v1.compute.instances.stop", "v1.compute.instances.delete", "compute.instances.guestTerminate",
       "compute.instances.stop", "compute.instances.preempted")


def running_hours(events, now, t_min=0.0):
    """events: dicts time [s], kind 'on'|'off', name. Running hours per name; an interval still open counts to now.
    Only the part of each interval after t_min is counted."""
    out, since = {}, {}

    def add(n, a, b):
        out[n] += max(0.0, b - max(a, t_min)) / 3600.0

    for e in sorted(events, key=lambda e: e["time"]):
        n = e["name"]
        out.setdefault(n, 0.0)
        if e["kind"] == "on":
            since.setdefault(n, e["time"])
        elif n in since:
            add(n, since.pop(n), e["time"])
    for n, t0 in since.items():
        add(n, t0, now)
    return out


def vm_cost(hours, vcpu, ram_gib, core, ram, ip):
    return hours * (vcpu * core + ram_gib * ram + ip)


def disk_cost(gib, hours, per_gib_month):
    return gib * per_gib_month * hours / HOURS_PER_MONTH


def _ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def read_log(days, project):
    methods = " OR ".join(f'"{m}"' for m in ON + OFF)
    flt = f'resource.type="gce_instance" AND logName:"cloudaudit.googleapis.com" AND protoPayload.methodName:({methods})'
    gc = os.path.expanduser("~/google-cloud-sdk/bin/gcloud")
    r = subprocess.run([gc if os.path.exists(gc) else "gcloud", "logging", "read", flt, "--project", project,
                        f"--freshness={days}d", "--format=json", "--limit=5000"], capture_output=True, text=True, check=True)
    return json.loads(r.stdout or "[]")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--since", help="only count time after this UTC date (YYYY-MM-DD)")
    ap.add_argument("--project", default=PROJECT)
    a = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    t_min = _ts(a.since + "T00:00:00Z") if a.since else 0.0
    vm_ev, disk_ev, mtype, dsize = [], [], {}, {}
    for e in read_log(a.days, a.project):
        pp, op = e["protoPayload"], e.get("operation", {})
        m, name = pp["methodName"], pp["resourceName"].rsplit("/", 1)[-1]
        if m.startswith("v1.") and not op.get("first"):      # count each request once (its first log entry)
            continue
        t = _ts(e["timestamp"])
        if m == "v1.compute.instances.insert":
            req = pp.get("request", {})
            mtype[name] = req.get("machineType", "?").rsplit("/", 1)[-1]
            for d in req.get("disks", []):
                if d.get("boot"):
                    dsize[name] = int(d.get("initializeParams", {}).get("diskSizeGb", 0))
            disk_ev.append(dict(time=t, kind="on", name=name))
        if m == "v1.compute.instances.delete":
            disk_ev.append(dict(time=t, kind="off", name=name))
        vm_ev.append(dict(time=t, kind="on" if m in ON else "off", name=name))
    vh, dh = running_hours(vm_ev, now, t_min), running_hours(disk_ev, now, t_min)
    total = 0.0
    print(f"{'instance':<14} {'type':<16} {'VM h':>7} {'VM $':>7} {'disk GiB':>8} {'disk h':>7} {'disk $':>7}")
    for n in sorted(vh):
        ty = mtype.get(n, "?")
        cpu, ram, rc, rr = TYPES.get(ty, (None,) * 4)
        c_vm = vm_cost(vh[n], cpu, ram, rc, rr, RATES["ip"]) if cpu else float("nan")
        g = dsize.get(n, 0)
        c_d = disk_cost(g, dh.get(n, 0.0), RATES["disk_month"])
        total += (c_vm if cpu else 0.0) + c_d
        print(f"{n:<14} {ty:<16} {vh[n]:7.2f} {c_vm:7.2f} {g:8d} {dh.get(n, 0.0):7.1f} {c_d:7.2f}"
              + ("" if cpu else "   (machine type rate unknown: not in total)"))
    print(f"TOTAL (VM + boot disk, excl. storage/egress): {total:.2f} USD   as of {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
