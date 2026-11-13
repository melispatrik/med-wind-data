# med-wind-data

Wind over the Mediterranean as small JSON files, rebuilt four times a day from
the ECMWF IFS open-data forecast.

- `build_wind.py` downloads the 10 m wind of the latest run, crops it to
  12°W–30°E, 28°N–48°N and writes one frame every three hours, a little over
  three days ahead (m/s, 0.25° grid).
- The workflow in `.github/workflows/wind.yml` runs it on a schedule and
  publishes the result on the `data` branch:
  - `index.json` lists the frames:
    `https://raw.githubusercontent.com/melispatrik/med-wind-data/data/index.json`
  - `frames/<YYYYMMDDHH>.json` is one frame, named by the UTC hour it describes.

The data is from [ECMWF open data](https://www.ecmwf.int/en/forecasts/datasets/open-data),
licensed CC BY 4.0. Credit ECMWF wherever you show it. It is a forecast, not a
measurement, and not for navigation.
