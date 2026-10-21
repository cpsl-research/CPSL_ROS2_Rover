#!/usr/bin/env python3
"""Rover Pro wheel-odometry calibration: record a run, then analyze it.

Read-only: subscribes to the driver's own topics with plain rclpy and
publishes nothing. No console and no custom message package is needed.

  record   python3 odom_calibrate.py record --out run.jsonl [--duration 300]
           [--namespace cpsl_rover_1]
           Needs a sourced ROS 2 and the same ROS_DOMAIN_ID / RMW_IMPLEMENTATION
           as the driver. Subscribes to /<ns>/odometry/wheels (nav_msgs/Odometry)
           and /<ns>/robot_status (std_msgs/Float32MultiArray, raw motor rpm; optional:
           without it "rpm" is []). Writes one line per new odom message, decimated
           to --rate (default 10 Hz).
           Markers: press Enter in the terminal (if stdin is a tty) to log a
           marker; independent of that, analyze auto-segments on rest periods.
           Stop early with Ctrl-C / SIGINT (file is flushed per line).
  analyze  python3 odom_calibrate.py analyze run.jsonl \
               --forward-m 2.362 --right-turns 5 --left-turns 5
           [--residual-deg D (floor-mark angle left over, CCW +)]
           Imports no ROS; runs anywhere.

Yaw is unwrapped here from the reported angle; wrapped input is fine.
"""
import argparse, json, math, signal, sys, time

TRACTION_NOW = 0.610
TWO_PI = 2 * math.pi
FT = 0.3048


def unwrap(yaws):
    out, off, prev = [], 0.0, None
    for y in yaws:
        if prev is not None:
            d = y - prev
            if d > math.pi:
                off -= TWO_PI * round(d / TWO_PI)
            elif d < -math.pi:
                off -= TWO_PI * round(d / TWO_PI)
        out.append(y + off)
        prev = y
    return out


def segment(samples, v_thr=0.02, w_thr=0.05, rest_s=2.0, min_s=0.5):
    """Split into moving segments separated by rest >= rest_s. Returns
    list of (i0, i1) inclusive sample index ranges."""
    mov = [abs(s["vx"]) > v_thr or abs(s["wz"]) > w_thr for s in samples]
    segs, start, last_mov = [], None, None
    for i, m in enumerate(mov):
        if m:
            if start is None:
                start = i
            last_mov = i
        elif start is not None and samples[i]["t"] - samples[last_mov]["t"] >= rest_s:
            segs.append((start, last_mov))
            start = None
    if start is not None:
        segs.append((start, last_mov))
    return [(a, b) for a, b in segs if samples[b]["t"] - samples[a]["t"] >= min_s]


def analyze_segments(samples, segs):
    yaw = unwrap([s["yaw"] for s in samples])
    res = []
    for a, b in segs:
        path = sum(math.hypot(samples[i + 1]["x"] - samples[i]["x"],
                              samples[i + 1]["y"] - samples[i]["y"]) for i in range(a, b))
        net = math.hypot(samples[b]["x"] - samples[a]["x"], samples[b]["y"] - samples[a]["y"])
        dyaw = yaw[b] - yaw[a]
        kind = "turn" if abs(dyaw) > 0.5 and path < 0.5 * abs(dyaw) + 0.3 else (
            "linear" if path > 0.3 and abs(dyaw) < 0.5 else "other")
        res.append(dict(i0=a, i1=b, t0=samples[a]["t"], t1=samples[b]["t"], path=path,
                        net=net, dyaw=dyaw, kind=kind))
    return res


def per_turn(samples, seg):
    """Seconds-free per-turn integrated yaw: split the segment at each
    cumulative 2*pi*k of the *integrated* value is circular, so report the
    time each integrated full-turn mark is reached (spacing = repeatability)."""
    yaw = unwrap([s["yaw"] for s in samples])
    y0 = yaw[seg["i0"]]
    sign = 1 if seg["dyaw"] > 0 else -1
    times, k = [], 1
    for i in range(seg["i0"], seg["i1"] + 1):
        while sign * (yaw[i] - y0) >= k * TWO_PI:
            times.append(samples[i]["t"])
            k += 1
    return times


def analyze(samples, fwd_m, n_r, n_l, residual_deg=None, segs=None):
    segs = segs if segs is not None else segment(samples)
    sg = analyze_segments(samples, segs)
    out = {"segments": sg, "ground_truth": dict(forward_m=fwd_m, right=n_r, left=n_l,
                                                residual_deg=residual_deg)}
    lin = [s for s in sg if s["kind"] == "linear"]
    right = [s for s in sg if s["kind"] == "turn" and s["dyaw"] < 0]
    left = [s for s in sg if s["kind"] == "turn" and s["dyaw"] > 0]
    if lin and fwd_m:
        ln = max(lin, key=lambda s: s["path"])
        out["linear"] = dict(integrated_m=ln["path"], net_m=ln["net"], true_m=fwd_m,
                             scale=fwd_m / ln["path"] if ln["path"] else None)
    def turns(group, n, label):
        if not group or not n:
            return None
        tot = sum(abs(s["dyaw"]) for s in group)
        true = TWO_PI * n
        d = dict(integrated_rad=tot, true_rad=true, integrated_turns=tot / TWO_PI,
                 scale=true / tot if tot else None,
                 suggested_traction=TRACTION_NOW * true / tot if tot else None)
        ts = [t for s in group for t in per_turn(samples, s)]
        if len(ts) > 2:
            gaps = [b - a for a, b in zip(ts, ts[1:])]
            m = sum(gaps) / len(gaps)
            d["turn_period_s"] = m
            d["turn_period_spread"] = (max(gaps) - min(gaps)) / m if m else None
        return d
    out["right"] = turns(right, n_r, "right")
    out["left"] = turns(left, n_l, "left")
    if out["right"] and out["left"]:
        tot = out["right"]["integrated_rad"] + out["left"]["integrated_rad"]
        true = out["right"]["true_rad"] + out["left"]["true_rad"]
        out["combined"] = dict(scale=true / tot,
                               suggested_traction=TRACTION_NOW * true / tot,
                               asymmetry_L_over_R=out["left"]["integrated_rad"] /
                               out["right"]["integrated_rad"])
    if samples:
        yaw = unwrap([s["yaw"] for s in samples])
        out["net_integrated_yaw_deg"] = math.degrees(yaw[-1] - yaw[0])
    return out


def load(path):
    samples, marks = [], []
    for line in open(path):
        r = json.loads(line)
        if "marker" in r:
            marks.append(r)
        elif "odom" in r:
            o = r["odom"] or {}
            if o.get("yaw") is None:
                continue
            samples.append(dict(t=r["t"], x=o["x"], y=o["y"], yaw=o["yaw"],
                                vx=o.get("vx") or 0.0, wz=o.get("wz") or 0.0,
                                rpm=r.get("rpm"), stamp=o.get("stamp")))
    return samples, marks


RPM_IDX = (1, 6, 11, 16)  # robot_status: motor blocks of five, rpm first after the id


def meta_line(namespace, rate, start_wall):
    topics = dict(odom=f"/{namespace}/odometry/wheels", status=f"/{namespace}/robot_status")
    return json.dumps(dict(meta=dict(namespace=namespace, topics=topics,
                                     start_wall=start_wall, rate=rate)))


def sample_line(t, odom, rpm):
    """One recorded sample. odom: dict(x, y, yaw, vx, wz, stamp); rpm: list or []."""
    return json.dumps(dict(t=round(t, 3), odom=odom, rpm=list(rpm)))


def marker_line(t, n):
    return json.dumps(dict(t=round(t, 3), marker=n))


def rpm_from_status(data):
    return [float(data[i]) for i in RPM_IDX] if len(data) > max(RPM_IDX) else []


def record(a):
    import select
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from nav_msgs.msg import Odometry
    from std_msgs.msg import Float32MultiArray

    stop = []
    for sg in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sg, lambda *_: stop.append(1))
    rclpy.init(signal_handler_options=rclpy.SignalHandlerOptions.NO)
    node = Node("odom_calibrate")
    ns = a.namespace.strip("/")
    latest = dict(odom=None, rpm=[])

    def on_odom(m):
        q = m.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        latest["odom"] = dict(x=m.pose.pose.position.x, y=m.pose.pose.position.y, yaw=yaw,
                              vx=m.twist.twist.linear.x, wz=m.twist.twist.angular.z,
                              stamp=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)

    def on_status(m):
        latest["rpm"] = rpm_from_status(m.data)

    node.create_subscription(Odometry, f"/{ns}/odometry/wheels", on_odom, qos_profile_sensor_data)
    node.create_subscription(Float32MultiArray, f"/{ns}/robot_status", on_status,
                             qos_profile_sensor_data)
    f = open(a.out, "w", buffering=1)
    t0 = time.time()
    f.write(meta_line(ns, a.rate, t0) + "\n")
    tty = sys.stdin.isatty()
    last_stamp, last_write, n, mk = None, -1e9, 0, 0
    while not stop and time.time() - t0 < a.duration:
        rclpy.spin_once(node, timeout_sec=0.02)
        t = time.time() - t0
        o = latest["odom"]
        if o and o["stamp"] != last_stamp and t - last_write >= 1.0 / a.rate:
            last_stamp, last_write = o["stamp"], t
            f.write(sample_line(t, o, latest["rpm"]) + "\n")
            n += 1
        if tty and select.select([sys.stdin], [], [], 0)[0]:
            sys.stdin.readline()
            mk += 1
            f.write(marker_line(time.time() - t0, mk) + "\n")
            print("marker", mk, flush=True)
    f.close()
    node.destroy_node()
    rclpy.shutdown()
    print(f"recorded {n} samples, {time.time() - t0:.1f}s -> {a.out}")
    if n == 0:
        print(f"no odometry received on /{ns}/odometry/wheels: check the driver is running "
              "and ROS_DOMAIN_ID / RMW_IMPLEMENTATION match", file=sys.stderr)


def report(r):
    for i, s in enumerate(r["segments"]):
        print(f"seg{i} {s['kind']:6} t={s['t0']:.1f}-{s['t1']:.1f}s path={s['path']:.3f}m "
              f"dyaw={math.degrees(s['dyaw']):.1f}deg")
    for k in ("linear", "right", "left", "combined"):
        if r.get(k):
            print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in r[k].items()})
    if "net_integrated_yaw_deg" in r:
        print("net integrated yaw deg", round(r["net_integrated_yaw_deg"], 2),
              "| user residual deg", r["ground_truth"]["residual_deg"])


def main(argv=None):
    p = argparse.ArgumentParser(description="Rover wheel-odometry calibration (record / analyze)")
    sp = p.add_subparsers(dest="cmd", required=True)
    rc = sp.add_parser("record", help="subscribe to the driver topics and write a jsonl")
    rc.add_argument("--out", required=True)
    rc.add_argument("--duration", type=float, default=300)
    rc.add_argument("--rate", type=float, default=10)
    rc.add_argument("--namespace", default="cpsl_rover_1")
    an = sp.add_parser("analyze")
    an.add_argument("file")
    an.add_argument("--forward-ft", type=float, default=0)
    an.add_argument("--forward-in", type=float, default=0)
    an.add_argument("--forward-m", type=float, default=None)
    an.add_argument("--right-turns", type=float, default=0)
    an.add_argument("--left-turns", type=float, default=0)
    an.add_argument("--residual-deg", type=float, default=None)
    an.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "record":
        return record(a)
    fwd = a.forward_m if a.forward_m is not None else (a.forward_ft * 12 + a.forward_in) * 0.0254
    samples, _ = load(a.file)
    r = analyze(samples, fwd, a.right_turns, a.left_turns, a.residual_deg)
    print(json.dumps(r, indent=1) if a.json else "", end="")
    if not a.json:
        report(r)


if __name__ == "__main__":
    main()
