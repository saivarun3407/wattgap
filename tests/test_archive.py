import gzip
from datetime import date

import pytest

from wattgap import data, warn


@pytest.fixture
def archive(tmp_path, monkeypatch):
    """A tiny two-day archive in the format scripts/fetch_archive.py writes, including a DST fall-back day."""
    pts = ["HB_HUBAVG", "LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST"]
    rt = ["interval_start_ct," + ",".join(pts)]
    for day_, off in (("2030-11-02", "-05:00"),):
        rt += [f"{day_}T{h:02d}:{m:02d}:00{off}," + ",".join(str(10 + h) for _ in pts) for h in range(24) for m in (0, 15, 30, 45)]
    rt += ["2030-11-03T01:00:00-05:00," + ",".join("70" for _ in pts), "2030-11-03T01:00:00-06:00," + ",".join("90" for _ in pts)]
    dam = ["hour_start_ct," + ",".join(pts)]
    dam += [f"2030-11-02T{h:02d}:00:00-05:00," + ",".join(str(20 + h) for _ in pts) for h in range(24)]
    # fall-back day: hour 1 twice (averaged), hour 2 missing is not possible here, so drop hour 5 to test the fill
    dam += [f"2030-11-03T{h:02d}:00:00-06:00," + ",".join(str(30 + h) for _ in pts) for h in range(24) if h != 5]
    dam += ["2030-11-03T01:00:00-05:00," + ",".join("11" for _ in pts)]
    for name, lines in (("rt_2030.csv.gz", rt), ("dam_2030.csv.gz", dam), ("rt_2031.csv.gz", rt[:1])):
        with gzip.open(tmp_path / name, "wt") as f:
            f.write("\n".join(lines) + "\n")
    monkeypatch.setattr(data, "ARCHIVE", tmp_path)
    for fn in (data.read_archive, data._archive_days, data._archive_dam):
        fn.cache_clear()
    yield tmp_path
    for fn in (data.read_archive, data._archive_days, data._archive_dam):
        fn.cache_clear()


def test_archive_days_and_dam_hours(archive):
    assert data.archive_years() == [2030]
    ivs = data.day(date(2030, 11, 2))
    assert len(ivs) == 96 and ivs[0].prices["HB_HUBAVG"] == 10 and ivs[0].home_kwh == {}
    assert ivs[0].system_price == 10  # the four load zones only, hubs excluded
    fall = data.day(date(2030, 11, 3))
    assert [i.start.utcoffset().total_seconds() / 3600 for i in fall] == [-5, -6]
    hours = data.dam_day(date(2030, 11, 3))
    assert len(hours) == 24
    assert hours[1]["LZ_NORTH"] == pytest.approx((31 + 11) / 2)  # repeated hour averaged
    assert hours[5]["LZ_NORTH"] == hours[4]["LZ_NORTH"]  # a missing hour copies the one before


def test_missing_archive_is_explained(archive):
    with pytest.raises(KeyError, match="make archive"):
        data.read_archive("as", 2030)
    with pytest.raises(KeyError):
        data.day(date(2032, 1, 1))


def test_backtest_from_feed_files(tmp_path, monkeypatch):
    (tmp_path / "rtd.csv").write_text(
        "RTDTimestamp,IntervalEnding,SettlementPoint,LMP\n"
        + "".join(f"09/21/2026 {h:02d}:{m:02d}:03,09/21/2026 {h:02d}:{m + 5:02d}:00,LZ_NORTH,{1500 if (h, m) == (17, 10) else 30}\n"
                  for h in range(16, 19) for m in range(0, 55, 5)))
    (tmp_path / "adders.csv").write_text("SCEDTimestamp,RTRDPA\n09/21/2026 16:00:00,0\n")
    (tmp_path / "lambda.csv").write_text("SCEDTimeStamp,CappedSystemLambda\n09/21/2026 16:00:00,25\n")
    (tmp_path / "spp.csv").write_text(
        "DeliveryDate,DeliveryHour,DeliveryInterval,SettlementPointName,SettlementPointPrice\n"
        + "".join(f"09/21/2026,{h},{i},LZ_NORTH,{1100 if (h, i) == (18, 2) else 30}\n" for h in (17, 18) for i in (1, 2, 3, 4)))
    monkeypatch.setattr(warn, "FEEDS", tmp_path)
    out = warn.run_backtest()
    assert out["rtd_runs"] == 33 and out["cases"][0]["events"] == 1 and out["cases"][0]["hits"] == 1
    assert out["look_ahead_bias"][0]["lead_min"] == 5
