run:
\tPYTHONPATH=src python -m cfs_postproc.cfs_postproc samples/input.gcode out/input_scaled_precut.gcode --m118-sentinels --console-summary

test:
\tPYTHONPATH=src pytest -q

lint:
\truff check .
\tblack --check .

format:
\tblack .
\truff check . --fix
