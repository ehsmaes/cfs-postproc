; Post-processed by cfs_postproc on 2025-10-04T09:38:13
; applied_flush_multiplier: 1.500000
; prime_volume subtracted: 250 mm^3
; original flush_volumes_matrix (mm^3):
;    200,  300,  400,  500
;      0,  600,  700,  800
;    900, 1000, 1100, 1200
;   1300, 1400, 1500, 1600
; scaled flush_volumes_matrix (mm^3) written:
;    100,  200,  350,  500
;      0,  650,  800,  950
;   1100, 1250, 1400, 1550
;   1700, 1850, 2000, 2150
; pre-cut: 80.0mm @ F600
; park XY: not found (no tower detected and no override)

; flush_multiplier = 1.0
; flush_volumes_matrix = 100, 200, 350, 500, 0, 650, 800, 950, 1100, 1250, 1400, 1550, 1700, 1850, 2000, 2150
; prime_volume = 250

; Some G-code content
G1 X10 Y10
T0
G1 X20 Y20
; [INJECT] pre-cut retract before T1 (80.0mm @ F600)
G1 E-80.0 F600
; [INJECT] selecting tool T1
T1
G1 X30 Y30
