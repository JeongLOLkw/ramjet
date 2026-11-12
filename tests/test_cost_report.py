import pytest

from scripts.cloud import cost_report as cr


def ev(t, kind, name="vm"):
    return dict(time=t, kind=kind, name=name)


H = 3600.0


def test_single_interval():
    e = [ev(0, "on"), ev(2 * H, "off")]
    assert cr.running_hours(e, now=10 * H) == {"vm": pytest.approx(2.0)}


def test_still_running_counts_until_now():
    e = [ev(0, "on"), ev(H, "off"), ev(3 * H, "on")]
    assert cr.running_hours(e, now=5 * H) == {"vm": pytest.approx(3.0)}


def test_repeated_on_or_off_does_not_double_count():
    # start requested twice while running, stop then guestTerminate of an already stopped VM
    e = [ev(0, "on"), ev(0.5 * H, "on"), ev(H, "off"), ev(1.5 * H, "off")]
    assert cr.running_hours(e, now=9 * H) == {"vm": pytest.approx(1.0)}


def test_unsorted_input_and_two_vms():
    e = [ev(2 * H, "off", "a"), ev(0, "on", "a"), ev(H, "on", "b"), ev(4 * H, "off", "b")]
    assert cr.running_hours(e, now=9 * H) == {"a": pytest.approx(2.0), "b": pytest.approx(3.0)}


def test_vm_cost_uses_core_and_ram_rates():
    # t2d-standard-8: 8 vCPU, 32 GiB
    assert cr.vm_cost(10.0, 8, 32, core=0.027502, ram=0.003686, ip=0.005) == pytest.approx(10 * (8 * 0.027502 + 32 * 0.003686 + 0.005))


def test_disk_cost_per_gib_month():
    # 60 GiB for 730 h (one billing month) at 0.1 $/GiB-month
    assert cr.disk_cost(60, 730.0, 0.1) == pytest.approx(6.0)


def test_since_clips_intervals_not_events():
    # an interval entirely before t_min contributes nothing; one straddling it counts only after t_min
    e = [ev(0, "on", "old"), ev(H, "off", "old"), ev(2 * H, "on", "x"), ev(6 * H, "off", "x")]
    assert cr.running_hours(e, now=9 * H, t_min=4 * H) == {"old": 0.0, "x": pytest.approx(2.0)}


def test_vm_cost_c2d_rates_known():
    cpu, ram, core, ramr = cr.TYPES["c2d-standard-8"]
    assert (cpu, ram) == (8, 32) and core == pytest.approx(0.02956) and ramr == pytest.approx(0.00396)
