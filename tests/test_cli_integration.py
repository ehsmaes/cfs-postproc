import pathlib
import subprocess
import sys


def test_cli_runs_and_writes_output(tmp_path: pathlib.Path):
    infile = tmp_path / "in.gcode"
    outfile = tmp_path / "out.gcode"
    infile.write_text(";FLAVOR:Marlin\n;TYPE:CUSTOM\n", encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "cfs_postproc.cfs_postproc",
        str(infile),
        str(outfile),
        "--m118-sentinels",
        "--console-summary",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert outfile.exists()
    assert outfile.read_text(encoding="utf-8")
