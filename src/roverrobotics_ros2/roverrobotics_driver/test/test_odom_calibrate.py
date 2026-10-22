import importlib.util, json, math, pathlib, subprocess, sys

p = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "odom_calibrate.py"
spec = importlib.util.spec_from_file_location("odom_calibrate", p)
oc = importlib.util.module_from_spec(spec); spec.loader.exec_module(oc)
SCRIPT = str(p)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def synth(dt=0.1):
    """rest 3s, fwd 2.0m integrated, rest 3s, 5 right turns (integrated at
    0.9x true), rest 3s, 5 left turns (1.1x true), rest 3s."""
    S, t, x, y, yaw = [], 0.0, 0.0, 0.0, 0.0
    def add(vx, wz, dur):
        nonlocal t, x, y, yaw
        for _ in range(int(dur / dt)):
            x += vx * dt * math.cos(yaw); y += vx * dt * math.sin(yaw); yaw += wz * dt; t += dt
            S.append(dict(t=t, x=x, y=y, yaw=wrap(yaw), vx=vx, wz=wz))
    add(0, 0, 3); add(0.25, 0, 8); add(0, 0, 3)
    add(0, -0.8, 5 * TWO / 0.8 * 0.9 if False else 5 * 2 * math.pi * 0.9 / 0.8)
    add(0, 0, 3)
    add(0, 0.8, 5 * 2 * math.pi * 1.1 / 0.8); add(0, 0, 3)
    return S

TWO = 2 * math.pi


def test_unwrap_many_turns():
    ys = [wrap(i * 0.3) for i in range(300)]
    u = oc.unwrap(ys)
    assert abs(u[-1] - 299 * 0.3) < 1e-6
    ys = [wrap(-i * 0.3) for i in range(300)]
    assert abs(oc.unwrap(ys)[-1] + 299 * 0.3) < 1e-6


def test_segmentation_and_scales():
    S = synth()
    segs = oc.segment(S)
    assert len(segs) == 3
    r = oc.analyze(S, 2.489, 5, 5, segs=segs)
    assert [s["kind"] for s in r["segments"]] == ["linear", "turn", "turn"]
    assert abs(r["linear"]["integrated_m"] - 2.0) < 0.05
    assert abs(r["linear"]["scale"] - 2.489 / 2.0) < 0.03
    assert abs(r["right"]["integrated_turns"] - 4.5) < 0.05
    assert abs(r["left"]["integrated_turns"] - 5.5) < 0.05
    assert abs(r["right"]["scale"] - 5 / 4.5) < 0.01
    assert abs(r["left"]["scale"] - 5 / 5.5) < 0.01
    assert abs(r["right"]["suggested_traction"] - 0.610 * 5 / 4.5) < 0.01
    assert abs(r["combined"]["scale"] - 1.0) < 0.01
    assert r["combined"]["asymmetry_L_over_R"] > 1.2


def test_short_pause_merges():
    S = synth()
    # a 1 s dip inside the forward leg must not split it
    for s in S:
        if 6.0 <= s["t"] < 7.0:
            s["vx"] = 0.0
    assert len(oc.segment(S)) == 3


def _write_run(path, rpm):
    """Write a file with the recorder's own line builders."""
    with open(path, "w") as f:
        f.write(oc.meta_line("cpsl_rover_1", 10, 0.0) + "\n")
        for s in synth():
            odom = dict(x=s["x"], y=s["y"], yaw=s["yaw"], vx=s["vx"], wz=s["wz"], stamp=s["t"])
            f.write(oc.sample_line(s["t"], odom, rpm) + "\n")
        f.write(oc.marker_line(1.5, 1) + "\n")


def test_recorded_format_loads_and_analyzes(tmp_path):
    for rpm in ([10.0, 11.0, 10.0, 11.0], []):
        path = tmp_path / "run.jsonl"
        _write_run(path, rpm)
        first = json.loads(path.read_text().splitlines()[0])
        assert first["meta"]["namespace"] == "cpsl_rover_1" and "url" not in first["meta"]
        samples, marks = oc.load(path)
        assert len(samples) == len(synth()) and len(marks) == 1
        assert samples[0]["rpm"] == rpm
        r = oc.analyze(samples, 2.489, 5, 5)
        assert [s["kind"] for s in r["segments"]] == ["linear", "turn", "turn"]
    # rpm null (older or odom-only files) also loads
    lines = path.read_text().splitlines()
    rec = json.loads(lines[1]); rec["rpm"] = None
    lines[1] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n")
    assert len(oc.load(path)[0]) == len(synth())


def test_rpm_from_status():
    data = [0.0] * 33
    data[1], data[6], data[11], data[16] = 1.0, 2.0, 3.0, 4.0
    assert oc.rpm_from_status(data) == [1.0, 2.0, 3.0, 4.0]
    assert oc.rpm_from_status([]) == []


def test_cli_help_without_rclpy():
    assert "import rclpy" not in "".join(
        l for l in open(SCRIPT) if not l.startswith(" "))  # only inside record()
    for args in ([], ["record"], ["analyze"]):
        r = subprocess.run([sys.executable, SCRIPT, *args, "--help"], capture_output=True, text=True)
        assert r.returncode == 0 and "usage" in r.stdout
    assert "rclpy" not in sys.modules


def test_progress_line_format():
    assert json.loads(oc.progress_line(3.04, 28)) == {"progress": {"t": 3.0, "samples": 28}}


def test_empty_namespace_is_root():
    assert oc.topic("", "odometry/wheels") == "/odometry/wheels"
    assert oc.topic("/", "robot_status") == "/robot_status"
    assert oc.topic("cpsl_rover_1", "odometry/wheels") == "/cpsl_rover_1/odometry/wheels"
    m = json.loads(oc.meta_line("", 10, 0.0))["meta"]
    assert m["topics"] == {"odom": "/odometry/wheels", "status": "/robot_status"}


def test_suggested_formula_docs32_numbers():
    sug = oc.suggested(dict(scale=1.941), dict(scale=2.051), 1.0, 0.610)
    assert abs(sug["odom_linear_scale"] - 1.941) < 1e-9
    assert abs(sug["odom_traction_factor"] - 0.610 * 2.051 / 1.941) < 1e-9
    assert round(sug["odom_traction_factor"], 3) == 0.645
    assert oc.suggested(dict(scale=1.9), None, 1.0, 0.61) is None
    assert oc.suggested(dict(scale=1.9), dict(scale=2.0), None, 0.61) is None


def test_suggested_synthetic_wheels_recover_truth():
    """Apply s', t' to the docs-32 model: the true distance and angle come out."""
    s, t = 1.0, 0.610
    S = synth()
    r = oc.analyze(S, 2.489, 5, 5, current_linear_scale=s, current_traction=t)
    sug = r["suggested"]
    s2, t2 = sug["odom_linear_scale"], sug["odom_traction_factor"]
    dist_now = r["linear"]["integrated_m"]
    ang_now = r["right"]["integrated_rad"] + r["left"]["integrated_rad"]
    # distance scales with s; angle with s*t (same wheel speeds)
    assert abs(dist_now * s2 / s - 2.489) < 0.02 * 2.489
    assert abs(ang_now * (s2 * t2) / (s * t) - 4 * math.pi * 5) < 0.02 * 4 * math.pi * 5


def test_output_unchanged_without_new_flags(tmp_path):
    path = tmp_path / "run.jsonl"
    _write_run(path, [])
    r = oc.analyze(oc.load(path)[0], 2.489, 5, 5)
    assert "suggested" not in r
    assert set(r) == {"segments", "ground_truth", "linear", "right", "left", "combined",
                      "net_integrated_yaw_deg"}
    out = subprocess.run([sys.executable, SCRIPT, "analyze", str(path), "--json", "--forward-m",
                          "2.489", "--right-turns", "5", "--left-turns", "5"],
                         capture_output=True, text=True, check=True).stdout
    assert "suggested" not in json.loads(out)
    out = subprocess.run([sys.executable, SCRIPT, "analyze", str(path), "--json", "--forward-m",
                          "2.489", "--right-turns", "5", "--left-turns", "5",
                          "--current-linear-scale", "1.94", "--current-traction", "0.645"],
                         capture_output=True, text=True, check=True).stdout
    assert set(json.loads(out)["suggested"]) == {"odom_linear_scale", "odom_traction_factor"}
