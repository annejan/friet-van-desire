#!/usr/bin/env python3
"""Export docs/composition.yaml -> a GoatTracker v2 .sng (GTS5) skeleton.

This is NOT a faithful render of our custom SID engine — GoatTracker plays the
song with its own playroutine. It gives the NOTES + structure (orderlist +
patterns + basic instruments) so the tune can be opened and refined in
GoatTracker. Expect to rework instruments/tables there.

Timing: tempo 3 (3 frames/row) keeps the absolute speed correct AND preserves
16th-note resolution (events quantise to the 3-frame row grid, ~±1.5f jitter).
Notes: gt_note = midi + 84 (C-4 <-> MIDI C4); octave may need a transpose in GT.

Format per the GoatTracker readme section 6.1 (GTS5).
"""
import os, sys, yaml, struct

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'docs', 'composition.yaml')
OUT  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'out', 'friet.sng')

FRAMES_PER_ROW = 3                 # tempo 3
ROWS_PER_PAT   = 64
NOTE_OFF       = 84                # gt_note = midi + 84
GT_REST, GT_KEYOFF, GT_PATEND = 0xBD, 0xBE, 0xFF
DRUM_NOTE = 0x90                   # fixed pitch for (noise) drums

def gt_note(midi):
    v = midi + NOTE_OFF
    return max(0x60, min(0xBC, v))

def pad(s, n):
    b = s.encode('latin-1', 'replace')[:n]
    return b + b'\x00' * (n - len(b))

# ---- load composition --------------------------------------------------
c = yaml.safe_load(open(COMP))
V = c['voices']
def rowof(frame): return int(round(frame / FRAMES_PER_ROW))

# ch index: 0 = bass (V1), 1 = lead (V2), 2 = drums (V3)
DRUM_INST = {'kick':3,'snare':4,'hat':5,'open_hat':6,'crash':7,'swell':8}

# per-channel: row -> (note, instr, cmd, data)
chan = [dict(), dict(), dict()]

def place_melodic(events, ch, inst):
    evs = sorted(events, key=lambda e: e['frame'])
    for i, e in enumerate(evs):
        r = rowof(e['frame'])
        chan[ch][r] = (gt_note(int(e['note'])), inst, 0, 0)
        end = rowof(e['frame'] + e.get('dur_frames', FRAMES_PER_ROW))
        nxt = rowof(evs[i+1]['frame']) if i+1 < len(evs) else end+1
        if end < nxt and end not in chan[ch]:      # gap -> key off (else legato)
            chan[ch][end] = (GT_KEYOFF, 0, 0, 0)

place_melodic(V['bass'], 0, 1)
place_melodic(V['lead'], 1, 2)
for e in sorted(V['drums'], key=lambda e: e['frame']):
    r = rowof(e['frame'])
    if r in chan[2]:                                # one drum per row (V3 is mono)
        continue
    chan[2][r] = (DRUM_NOTE, DRUM_INST.get(e.get('kind'), 5), 0, 0)

# tempo command on ch0 row0 (F03 = tempo 3, all channels)
n0, i0, _, _ = chan[0].get(0, (GT_REST, 0, 0, 0))
chan[0][0] = (n0, i0, 0x0F, FRAMES_PER_ROW)

total_rows = max((max(d) for d in chan if d), default=0) + 1
K = (total_rows + ROWS_PER_PAT - 1) // ROWS_PER_PAT      # patterns per channel
total_rows = K * ROWS_PER_PAT

# ---- build patterns + orderlists --------------------------------------
patterns = []                       # list of bytes (each a full pattern)
orderlists = []                     # per channel: list of pattern numbers
for ch in range(3):
    pats = []
    for p in range(K):
        body = bytearray()
        for r in range(p*ROWS_PER_PAT, (p+1)*ROWS_PER_PAT):
            note, inst, cmd, data = chan[ch].get(r, (GT_REST, 0, 0, 0))
            body += bytes([note, inst, cmd, data])
        body += bytes([GT_PATEND, 0, 0, 0])          # end-mark row
        length = ROWS_PER_PAT + 1                     # rows incl. end-mark
        patterns.append(bytes([length]) + bytes(body))
        pats.append(len(patterns) - 1)
    orderlists.append(pats)

# ---- instruments -------------------------------------------------------
# (AD, SR, wave_ptr, pulse_ptr, filt_ptr, vib, vibdelay, gateoff, hr, name)
GATEOFF = 0x02                       # must be < tempo(3)
INSTR = [
    (0x07, 0x18, 1, 0, 0, 0, 0, GATEOFF, 0x00, 'bass'),   # 1 sawtooth
    (0x12, 0xF6, 1, 0, 0, 0, 0, GATEOFF, 0x00, 'lead'),   # 2 sawtooth
    (0x09, 0x00, 3, 0, 0, 0, 0, GATEOFF, 0x00, 'kick'),   # 3 noise
    (0x07, 0x00, 3, 0, 0, 0, 0, GATEOFF, 0x00, 'snare'),
    (0x02, 0x00, 3, 0, 0, 0, 0, GATEOFF, 0x00, 'hat'),
    (0x05, 0x00, 3, 0, 0, 0, 0, GATEOFF, 0x00, 'ohat'),
    (0x90, 0xF8, 3, 0, 0, 0, 0, GATEOFF, 0x00, 'crash'),
    (0xC0, 0xF9, 3, 0, 0, 0, 0, GATEOFF, 0x00, 'swell'),
]
instr_blob = bytes([len(INSTR)])
for ad, sr, wv, pu, fi, vi, vd, go, hr, nm in INSTR:
    instr_blob += bytes([ad, sr, wv, pu, fi, vi, vd, go, hr]) + pad(nm, 16)

# ---- tables ------------------------------------------------------------
# wavetable: pos1 saw+gate (loop), pos3 noise+gate (loop). 1-based jumps.
wt_left  = [0x21, 0xFF, 0x81, 0xFF]
wt_right = [0x00, 0x01, 0x00, 0x03]
def table(left, right):
    assert len(left) == len(right)
    return bytes([len(left)]) + bytes(left) + bytes(right)
tables = table(wt_left, wt_right) + table([], []) + table([], []) + table([], [])

# ---- assemble file -----------------------------------------------------
out = bytearray(b'GTS5')
out += pad('Friet met Desire', 32)
out += pad('deFEEST: Kloot/Cinder/Anus', 32)
out += pad('2026 deFEEST', 32)
out += bytes([1])                                    # 1 subtune
for ch in range(3):                                  # orderlists
    data = bytes(orderlists[ch]) + bytes([0xFF, 0]) # patterns + RST + restart 0
    out += bytes([len(orderlists[ch]) + 1])          # length = #patterns + 1 (RST mark)
    out += data
out += instr_blob
out += tables
out += bytes([len(patterns)])                        # patterns header
for p in patterns:
    out += p

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'wb').write(out)
print(f"wrote {OUT} ({len(out)} bytes): {K} patterns/ch, {len(patterns)} total, "
      f"{total_rows} rows, {len(INSTR)} instruments, tempo {FRAMES_PER_ROW}")
