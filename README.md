# med-wind-data

Wind over the Mediterranean as one small JSON file, rebuilt four times a day from
the ECMWF IFS open-data forecast.

- `build_wind.py` downloads the 10 m wind of the latest run, crops it to
  12°W–30°E, 28°N–48°N and writes 3-hourly frames (m/s, 0.25° grid).
- The workflow in `.github/workflows/wind.yml` runs it on a schedule and
  publishes the result as `wind.json` on the `data` branch:
  `https://raw.githubusercontent.com/melispatrik/med-wind-data/data/wind.json`

The data is from [ECMWF open data](https://www.ecmwf.int/en/forecasts/datasets/open-data),
licensed CC BY 4.0. Credit ECMWF wherever you show it. It is a forecast, not a
measurement, and not for navigation.
