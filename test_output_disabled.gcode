; Post-processed by cfs_postproc on 2025-10-04T09:45:42
; applied_flush_multiplier: 1.500000
; prime_volume found: 250 mm^3 (but prime tower disabled)
; original flush_volumes_matrix (mm^3):
;    200,  300,  400,  500
;      0,  600,  700,  800
;    900, 1000, 1100, 1200
;   1300, 1400, 1500, 1600
; scaled flush_volumes_matrix (mm^3) written:
;    300,  450,  600,  750
;      0,  900, 1050, 1200
;   1350, 1500, 1650, 1800
;   1950, 2100, 2250, 2400
; pre-cut: 80.0mm @ F600
; park XY: not found (no tower detected and no override)

; flush_multiplier = 1.0
; flush_volumes_matrix = 300, 450, 600, 750, 0, 900, 1050, 1200, 1350, 1500, 1650, 1800, 1950, 2100, 2250, 2400
; prime_volume = 250
; enable_prime_tower = 0

; Some G-code content
G1 X10 Y10
T0
G1 X20 Y20
; [INJECT] pre-cut retract before T1 (80.0mm @ F600)
G1 E-80.0 F600
; [INJECT] selecting tool T1
T1
G1 X30 Y30
