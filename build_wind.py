"""Build Mediterranean wind files from ECMWF open data.

Downloads the 10 m wind (u and v) of the latest ECMWF IFS run, crops it to the
Mediterranean and writes, into the output directory:

    index.json            { "source", "run", "built",
                            "frames": [ { "validTime": "<ISO>", "file": "frames/2026111312.json" } ] }
    frames/<stamp>.json   { "validTime": "<ISO>", "header": {...}, "u": [...], "v": [...] }

One frame every three hours, from the first hour that is still ahead of "now"
when the run is published to a little over three days out. `header` + `u`/`v`
are the grid layout leaflet-velocity expects (rows from the north-west corner,
west to east, north to south). Values are m/s, one decimal.

ECMWF's files are GRIB2 with CCSDS packing, which nothing in Node can decode —
that is why this is a Python job. Data licence: CC-BY-4.0; whoever shows the
data credits ECMWF.

    pip install -r requirements.txt
    python build_wind.py out
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import eccodes
import numpy as np
from ecmwf.opendata import Client

# Adriatic to Gibraltar, with a margin so the view never shows an edge.
WEST, EAST, SOUTH, NORTH = -12.0, 30.0, 28.0, 48.0

# A run is published 7-9 hours after its nominal time and this job runs every
# six hours, so step 6 is always at or before "now". 90 h is as far as the
# 06 and 18 UTC runs go, and leaves three full days ahead at the worst moment.
STEPS = list(range(6, 91, 3))


def read_fields(path):
    """Every message in the file as (shortName, step, 2-D array, lats, lons)."""
    out = []
    with open(path, "rb") as f:
        while True:
            gid = eccodes.codes_grib_new_from_file(f)
            if gid is None:
                break
            try:
                if eccodes.codes_get(gid, "jScansPositively") != 0:
                    raise ValueError("expected rows north to south")
                if eccodes.codes_get(gid, "iScansNegatively") != 0:
                    raise ValueError("expected columns west to east")
                ni = eccodes.codes_get(gid, "Ni")
                nj = eccodes.codes_get(gid, "Nj")
                values = eccodes.codes_get_values(gid).reshape(nj, ni)
                lat0 = eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees")
                lon0 = eccodes.codes_get(gid, "longitudeOfFirstGridPointInDegrees")
                dlat = eccodes.codes_get(gid, "jDirectionIncrementInDegrees")
                dlon = eccodes.codes_get(gid, "iDirectionIncrementInDegrees")
                out.append(
                    (
                        eccodes.codes_get(gid, "shortName"),
                        int(eccodes.codes_get(gid, "step")),
                        values,
                        lat0 - dlat * np.arange(nj),
                        lon0 + dlon * np.arange(ni),
                    )
                )
            finally:
                eccodes.codes_release(gid)
    return out


def crop(values, lats, lons):
    """Cut the global grid to the box, with longitudes as -180..180."""
    lons = np.where(lons >= 180, lons - 360, lons)
    order = np.argsort(lons)
    lons, values = lons[order], values[:, order]
    rows = np.where((lats <= NORTH) & (lats >= SOUTH))[0]
    cols = np.where((lons >= WEST) & (lons <= EAST))[0]
    return values[np.ix_(rows, cols)], lats[rows], lons[cols]


def write_json(path, payload):
    with open(path, "w") as f:
        json.dump(payload, f, separators=(",", ":"))


def main(out_dir):
    client = Client(source="ecmwf")
    with tempfile.NamedTemporaryFile(suffix=".grib2") as tmp:
        result = client.retrieve(
            type="fc", step=STEPS, param=["10u", "10v"], target=tmp.name
        )
        run = result.datetime.replace(tzinfo=timezone.utc)
        fields = read_fields(tmp.name)

    by_step = {}
    for name, step, values, lats, lons in fields:
        by_step.setdefault(step, {})[name] = crop(values, lats, lons)

    frames = []
    for step in sorted(by_step):
        u, lats, lons = by_step[step]["10u"]
        v, _, _ = by_step[step]["10v"]
        valid = run + timedelta(hours=step)
        frames.append(
            {
                "validTime": valid.isoformat(),
                "header": {
                    "nx": int(len(lons)),
                    "ny": int(len(lats)),
                    "lo1": float(lons[0]),
                    "la1": float(lats[0]),
                    "lo2": float(lons[-1]),
                    "la2": float(lats[-1]),
                    "dx": float(abs(lons[1] - lons[0])),
                    "dy": float(abs(lats[0] - lats[1])),
                },
                "u": [round(float(x), 1) for x in u.ravel()],
                "v": [round(float(x), 1) for x in v.ravel()],
            }
        )
    if len(frames) != len(STEPS):
        raise SystemExit(f"expected {len(STEPS)} frames, got {len(frames)}")

    meta = {
        "source": "ECMWF IFS open data",
        "run": run.isoformat(),
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    os.makedirs(os.path.join(out_dir, "frames"), exist_ok=True)
    index = []
    for frame in frames:
        stamp = datetime.fromisoformat(frame["validTime"]).strftime("%Y%m%d%H")
        write_json(os.path.join(out_dir, "frames", f"{stamp}.json"), frame)
        index.append({"validTime": frame["validTime"], "file": f"frames/{stamp}.json"})
    write_json(os.path.join(out_dir, "index.json"), {**meta, "frames": index})

    head = frames[0]["header"]
    print(
        f"run {run:%Y-%m-%d %H}Z, {len(frames)} frames to "
        f"{frames[-1]['validTime']}, grid {head['nx']}x{head['ny']}"
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
