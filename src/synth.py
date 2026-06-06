#!/usr/bin/env python3
"""Phase 3 of the cleanroom pipeline.

Reads docs/composition.yaml (the concrete arrangement) and emits a PSID v2
file at out/friet_clean.sid. This script is the "implementation team":
it must not open any MIDI file. It only consumes the composition.

The player code mirrors the happy-hardcore design:
  V1 bass  : pulse stabs, short envelope, narrow pulse width
  V2 lead  : sawtooth, per-note filter cutoff envelope ("hoover" sweep),
             vibrato ±12 SID-freq units (~3 Hz LFO, ~0.16% pitch)
  V3 drums : noise hits with per-event ADSR; kick/snare/hat/crash
"""
import yaml, struct, subprocess, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'docs', 'composition.yaml')
OUT_SID   = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'out', 'friet_clean.sid')

PAL_CLK = 985248.0
PAL_HZ  = 50.0

WF_TRI, WF_SAW, WF_PULSE, WF_NOISE = 0x10, 0x20, 0x40, 0x80
# Bass: HHC punch. Instant attack, 168 ms decay to 7% sustain, 168 ms release.
# Each note thwacks at attack peak then drops nearly silent, leaving the
# mid-bass register clear for the pulse lead.
V1_AD, V1_SR = 0x07, 0x17
# Lead (triangle = vocal-ish tone): gentle 24 ms attack so legato pitch
# changes don't click, full sustain, medium release for breathy phrase tails.
V2_AD, V2_SR = 0x12, 0xF6

# Drum table: kind -> (freq_table_index, dur_frames, ad, sr)
# Long decay times (AD high nibble) so the envelope actually rings out
# instead of decaying to silence in 6 ms. Sustain=0 with release=0 means
# the envelope decays naturally toward 0 at the decay rate during gate-on.
DRUM_KIT = {
    'kick':    (2,  4, 0x09, 0x00),  # 80 ms gate — punchy HHC 4-on-floor
    'snare':   (36, 5, 0x07, 0x00),  # decay 168 ms — sharp snap
    'hat':     (78, 1, 0x02, 0x00),  # decay  24 ms — crisp tick (dur=1 frame)
    # Open hat: same noise pitch as closed, longer gate + slower decay so the
    # noise rings into the next 8th instead of cutting dead. 60 ms gives the
    # "tssss" attack without bleeding into the next hit = chorus shimmer.
    'open_hat':(78, 3, 0x05, 0x00),  # gate 60 ms, decay ~80 ms
    # Reverse-cymbal swell. Attack $9 = ~750 ms rise to peak, sustain $F
    # holds at peak, release $8 = 240 ms clean tail. Gated 1.6 s so the
    # envelope reaches full peak before release. Pitch index 28 (≈ MIDI 52)
    # is darker noise — more "wwoosh", less "ssss".
    'crash':   (28, 80, 0x90, 0xF8),
}

NOTE_LO, NOTE_HI = 12, 119

def midi_to_sid_freq(note):
    hz = 440.0 * 2 ** ((note - 69) / 12.0)
    return int(round(hz * (1 << 24) / PAL_CLK)) & 0xFFFF

def events_to_spans(events):
    """List of {frame, note, dur_frames} -> list of (start, end, note) spans
    with explicit rests between events."""
    if not events:
        return []
    out = []
    last_end = 0
    for ev in events:
        s = ev['frame']
        e = s + ev.get('dur_frames', 5)
        n = ev['note']
        if s > last_end:
            out.append((last_end, s, 0))  # rest
        out.append((s, e, n))
        last_end = e
    return out

def encode_voice_3byte(spans, total_frames):
    """Encode (start,end,note) spans as 3-byte events: dur_hi, dur_lo, note."""
    buf = bytearray()
    last_end = 0
    for s, e, n in spans:
        if s > last_end:
            dur = s - last_end
            while dur > 0xFFFF:
                buf += bytes([0xFF, 0xFF, 0])
                dur -= 0xFFFF
            buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, 0])
        dur = e - s
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, n & 0x7F])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, n & 0x7F])
        last_end = e
    # Pad tail with rest to total_frames
    if total_frames > last_end:
        dur = total_frames - last_end
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, 0])
            dur -= 0xFFFF
        if dur > 0:
            buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, 0])
    buf += bytes([0, 0, 0])  # loop sentinel
    return buf

def events_to_spans_ctrl(events, default_ctrl):
    """Like events_to_spans but each span carries a per-event ctrl byte
    (waveform without gate). Rest gaps inherit the previous span's ctrl
    so a gate-off doesn't change the waveform."""
    if not events:
        return []
    out = []
    last_end = 0
    last_ctrl = default_ctrl
    for ev in events:
        s = ev['frame']
        e = s + ev.get('dur_frames', 5)
        n = ev['note']
        ctrl = ev.get('ctrl', default_ctrl)
        if s > last_end:
            out.append((last_end, s, 0, last_ctrl))  # rest
        out.append((s, e, n, ctrl))
        last_end = e
        last_ctrl = ctrl
    return out

def encode_voice_4byte(spans_with_ctrl, total_frames, default_ctrl):
    """Encode (start, end, note, ctrl) spans as 4-byte events:
    dur_hi, dur_lo, note, ctrl. ctrl is the waveform byte without gate
    (the player ORs gate=$01 for notes, writes the bare ctrl for rests)."""
    buf = bytearray()
    last_end = 0
    last_ctrl = default_ctrl
    for s, e, n, c in spans_with_ctrl:
        if s > last_end:
            dur = s - last_end
            while dur > 0xFFFF:
                buf += bytes([0xFF, 0xFF, 0, last_ctrl & 0xFE])
                dur -= 0xFFFF
            buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, 0, last_ctrl & 0xFE])
        dur = e - s
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, n & 0x7F, c & 0xFE])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, n & 0x7F, c & 0xFE])
        last_end = e
        last_ctrl = c
    if total_frames > last_end:
        dur = total_frames - last_end
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, 0, last_ctrl & 0xFE])
            dur -= 0xFFFF
        if dur > 0:
            buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, 0, last_ctrl & 0xFE])
    buf += bytes([0, 0, 0, 0])  # loop sentinel
    return buf

def build_drum_timeline(drum_events, total_frames):
    """List of {frame, kind} -> RLE-compressed (dur, note, ctrl, ad, sr) events.

    Non-overlapping resolution: V3 is the shared noise channel — only one
    drum can play at a time. Each event is truncated to fit BEFORE the next
    event's onset, gets a clean gate-on hold + gate-off frame, and the
    timeline gap between events carries the previous drum's gate-off tuple
    so AD/SR don't toggle during the release tail. That gives each drum hit
    a clean, hardware-legal envelope (without this, overlapping events
    produced mid-cycle AD/SR changes + re-triggers = glitch artefacts).
    """
    KICK_TRI_FRAMES = 2
    KICK_TRI_PITCH = 20            # high-ish triangle "thump"
    REST_INITIAL = (0, 0x80, 0x00, 0x09)
    timeline = [REST_INITIAL] * (total_frames + 2)
    sorted_evs = sorted([e for e in drum_events if e.get('kind') in DRUM_KIT],
                        key=lambda e: e['frame'])
    for idx, ev in enumerate(sorted_evs):
        kind = ev['kind']
        pitch, gate_dur, ad, sr = DRUM_KIT[kind]
        f = ev['frame']
        next_f = sorted_evs[idx + 1]['frame'] if idx + 1 < len(sorted_evs) else total_frames
        # Truncate gate-on duration so we LEAVE at least 1 frame for our own
        # gate-off before the next event grabs the channel.
        gate_on = max(1, min(gate_dur, next_f - f - 1))
        # Write gate-on frames
        if kind == 'kick':
            tri = min(KICK_TRI_FRAMES, gate_on)
            for i in range(tri):
                if f + i < total_frames:
                    timeline[f + i] = (KICK_TRI_PITCH, 0x11, ad, sr)
            for i in range(tri, gate_on):
                if f + i < total_frames:
                    timeline[f + i] = (pitch, 0x81, ad, sr)
        else:
            for i in range(gate_on):
                if f + i < total_frames:
                    timeline[f + i] = (pitch, 0x81, ad, sr)
        # Gate-off and release-tail fill: this drum's gate-off tuple holds
        # until the next event (or end). Keeps AD/SR steady during release
        # so the SID's envelope finishes its tail at the drum's own rate
        # instead of switching to the static REST AD/SR mid-release.
        rest_tuple = (pitch, 0x80, ad, sr)
        for ff in range(f + gate_on, next_f):
            if ff < total_frames:
                timeline[ff] = rest_tuple
    # RLE
    events = []
    i = 0
    while i < total_frames:
        cur = timeline[i]
        j = i + 1
        while j < total_frames and timeline[j] == cur:
            j += 1
        events.append((j - i, cur))
        i = j
    return events

def encode_v3(events):
    """6-byte events: dur_hi, dur_lo, note, ctrl, ad, sr."""
    buf = bytearray()
    for dur, (note, ctrl, ad, sr) in events:
        if dur < 1: dur = 1
        while dur > 0xFFFF:
            buf += bytes([0xFF, 0xFF, note & 0x7F, ctrl, ad, sr])
            dur -= 0xFFFF
        buf += bytes([(dur >> 8) & 0xFF, dur & 0xFF, note & 0x7F, ctrl, ad, sr])
    buf += bytes([0, 0, 0, 0, 0, 0])  # loop sentinel
    return buf

# -------------------- main --------------------
def main():
    with open(COMP_PATH) as f:
        comp = yaml.safe_load(f)
    total_frames = comp['length_frames']
    title = comp.get('title', 'Friet From Desire')[:31]
    bpm   = comp.get('bpm', 175)

    bass_spans = events_to_spans(comp['voices']['bass'])
    lead_spans = events_to_spans(comp['voices']['lead'])

    bass_spans_ctrl = events_to_spans_ctrl(comp['voices']['bass'], default_ctrl=WF_PULSE)
    v1_data = encode_voice_4byte(bass_spans_ctrl, total_frames, default_ctrl=WF_PULSE)

    lead_spans_ctrl = events_to_spans_ctrl(comp['voices']['lead'], default_ctrl=WF_TRI)
    v2_data = encode_voice_4byte(lead_spans_ctrl, total_frames, default_ctrl=WF_TRI)
    v3_data = encode_v3(build_drum_timeline(comp['voices']['drums'], total_frames))

    print(f"  bass : {len(comp['voices']['bass']):4d} events -> {len(v1_data)}B")
    print(f"  lead : {len(comp['voices']['lead']):4d} events -> {len(v2_data)}B")
    print(f"  drums: {len(comp['voices']['drums']):4d} events -> {len(v3_data)}B")

    # Frequency table
    freq_lo, freq_hi = [], []
    for n in range(NOTE_LO, NOTE_HI + 1):
        f = midi_to_sid_freq(n)
        freq_lo.append(f & 0xFF)
        freq_hi.append((f >> 8) & 0xFF)

    def bytes_to_asm(name, data, per_line=16):
        out = [f"{name}:"]
        for i in range(0, len(data), per_line):
            chunk = data[i:i+per_line]
            out.append("    .byt " + ",".join(f"${b:02X}" for b in chunk))
        return "\n".join(out)

    asm = f"""
NOTE_LO = {NOTE_LO}
SID = $D400

ZP_V0   = $FB
ZP_V1   = $FD
ZP_V2   = $F7
ZP_CNT0 = $02
ZP_CNT1 = $04
ZP_CNT2 = $06
ZP_FILT_CUR = $08
ZP_FILT_TGT = $09
ZP_V2_LAST = $0A         ; last lead note played (0 = rest); drives legato
ZP_V2BASE_LO = $0B       ; V2 base freq lo (vibrato adds to this)
ZP_V2BASE_HI = $0C       ; V2 base freq hi
ZP_VIB_IDX   = $0D       ; vibrato LFO phase
ZP_V0_CTRL   = $0E       ; ctrl byte read from V1 event stream
ZP_V1_CTRL   = $0F       ; ctrl byte read from V2 event stream

*=$1000
    jmp init_routine
    jmp play_routine

init_routine:
    sei
    lda #0
    ldx #$18
init_clr:
    sta SID,x
    dex
    bpl init_clr
    lda #${V1_AD:02X}
    sta SID+5
    lda #${V1_SR:02X}
    sta SID+6
    lda #${V2_AD:02X}
    sta SID+12
    lda #${V2_SR:02X}
    sta SID+13
    ; V1 pulse width — 50% squarewave, rounder than 25% in the mix.
    lda #$00
    sta SID+2
    lda #$08
    sta SID+3
    ; V2 pulse width — 25% duty. Lots of odd-harmonic content (thin, reedy,
    ; HHC-stab-flavoured) that cuts through the mid-bass range the bass
    ; and snare occupy.
    lda #$00
    sta SID+9           ; V2 PW LO
    lda #$04
    sta SID+10          ; V2 PW HI
    ; Filter — route V2 (lead) through a resonant low-pass. Each V2 note-on
    ; resets the cutoff to $C0 (open); filter_env decays it toward $80 over
    ; the note's life => "hoover wow" sweep on every lead note.
    lda #$00
    sta SID+21          ; FC LO
    lda #$80
    sta SID+22          ; FC HI — open enough to keep the pulse lead's
                        ; high harmonics audible (was $60 when the lead
                        ; was a soft triangle).
    lda #$42            ; resonance $4, V2 routed (bit 1). On 8580 res $4
                        ; is gentle ring without a piercing peak — $7+
                        ; made the lead whistle against the kick.
    sta SID+23
    lda #$1F            ; LP mode + volume max
    sta SID+24
    lda #$C0
    sta ZP_FILT_CUR     ; start open ($C0 is near fully-open on 8580)
    lda #$80
    sta ZP_FILT_TGT     ; sweep settles to a warm-bright mid-LP
    lda #<v0_data
    sta ZP_V0
    lda #>v0_data
    sta ZP_V0+1
    lda #<v1_data
    sta ZP_V1
    lda #>v1_data
    sta ZP_V1+1
    lda #<v2_data
    sta ZP_V2
    lda #>v2_data
    sta ZP_V2+1
    lda #0
    sta ZP_CNT0
    sta ZP_CNT0+1
    sta ZP_CNT1
    sta ZP_CNT1+1
    sta ZP_CNT2
    sta ZP_CNT2+1
    sta ZP_V2_LAST
    sta ZP_V2BASE_LO
    sta ZP_V2BASE_HI
    sta ZP_VIB_IDX
    cli
    rts

play_routine:
    jsr tick0
    jsr tick1
    jsr tick2
    ; filter_env: per-note cutoff sweep $C0->$80 plus a synchronised LFO
    ; ±3 wobble. Verse notes sit below the cutoff (warm); chorus notes
    ; brush it (audible sweep + shimmer = the HHC "wow"). apply_vibrato
    ; and pwm_sweep stay defined below but are not called: vibrato
    ; didn't complete on short notes and PWM dropped out at PW extremes.
    jsr filter_env
    rts

; PWM sweep on V1 bass — cycle pulse width continuously for thick movement
; (Hubbard/Galway trick). Increment +$0060/frame = full cycle in ~860 ms.
; Currently not called from play_routine — kept for future re-enable.
pwm_sweep:
    clc
    lda SID+2          ; V1 PW LO
    adc #$60
    sta SID+2
    lda SID+3          ; V1 PW HI
    adc #$00
    and #$0F           ; keep in 0-F range
    sta SID+3
    rts

; Add a small LFO to V2's base freq each frame so the vocal feels SUNG
; rather than dead-pan. Skipped while V2 hasn't received a note yet
; (base = 0) — otherwise the LFO wraps to ~$FFxx and we hear a ~4 kHz beep.
apply_vibrato:
    lda ZP_V2BASE_LO
    ora ZP_V2BASE_HI
    bne vib_active
    rts
vib_active:
    inc ZP_VIB_IDX
    lda ZP_VIB_IDX
    and #$0F
    tay
    lda vib_lo,y
    clc
    adc ZP_V2BASE_LO
    sta SID+7
    lda vib_hi,y
    adc ZP_V2BASE_HI
    sta SID+8
    rts

; Modulate filter cutoff each frame: decay sweep + LFO wobble.
; The LFO uses the free-running ZP_VIB_IDX phase (advanced here since
; apply_vibrato is not currently called) for a subtle shimmer.
filter_env:
    inc ZP_VIB_IDX        ; advance shared LFO phase
    lda ZP_FILT_CUR
    cmp ZP_FILT_TGT
    beq fe_lfo          ; skip decay if at target, but still wobble
    bcc fe_up
    sec
    sbc #2
    cmp ZP_FILT_TGT
    bcs fe_store
    lda ZP_FILT_TGT
    jmp fe_store
fe_up:
    clc
    adc #1
fe_store:
    sta ZP_FILT_CUR
fe_lfo:
    lda ZP_VIB_IDX
    and #$0F
    tay
    lda ZP_FILT_CUR
    clc
    adc filt_lfo,y
    bmi fe_clamp_lo
    cmp #$F0
    bcc fe_final
    lda #$EF
    jmp fe_final
fe_clamp_lo:
    lda #$40
fe_final:
    sta SID+22
    rts

tick0:
    lda ZP_CNT0
    bne d0lo
    lda ZP_CNT0+1
    bne d0hi
    jmp fetch0
d0hi:
    dec ZP_CNT0+1
    dec ZP_CNT0
    rts
d0lo:
    dec ZP_CNT0
    rts

; --- V1 4-byte event: dur_hi, dur_lo, note, ctrl (waveform, no gate) ---
fetch0:
    ldy #0
    lda (ZP_V0),y
    sta ZP_CNT0+1
    iny
    lda (ZP_V0),y
    sta ZP_CNT0
    iny
    lda (ZP_V0),y         ; A = note
    pha
    lda ZP_CNT0
    ora ZP_CNT0+1
    bne f0go
    pla
    lda #<v0_data
    sta ZP_V0
    lda #>v0_data
    sta ZP_V0+1
    rts
f0go:
    iny
    lda (ZP_V0),y         ; A = ctrl (waveform without gate)
    sta ZP_V0_CTRL        ; stash for use after note/rest branch
    pla                   ; A = note
    cmp #0
    beq f0rest
    sec
    sbc #NOTE_LO
    tax
    lda freq_lo,x
    sta SID+0
    lda freq_hi,x
    sta SID+1
    lda ZP_V0_CTRL        ; waveform alone -> gate off
    sta SID+4
    ora #$01              ; OR gate -> attack
    sta SID+4
    jmp f0adv
f0rest:
    lda ZP_V0_CTRL        ; rest: waveform without gate (release)
    sta SID+4
f0adv:
    clc
    lda ZP_V0
    adc #4
    sta ZP_V0
    bcc f0done
    inc ZP_V0+1
f0done:
    rts

tick1:
    lda ZP_CNT1
    bne d1lo
    lda ZP_CNT1+1
    bne d1hi
    jmp fetch1
d1hi:
    dec ZP_CNT1+1
    dec ZP_CNT1
    rts
d1lo:
    dec ZP_CNT1
    rts

; --- V2 4-byte event: dur_hi, dur_lo, note, ctrl (waveform without gate) ---
fetch1:
    ldy #0
    lda (ZP_V1),y
    sta ZP_CNT1+1
    iny
    lda (ZP_V1),y
    sta ZP_CNT1
    iny
    lda (ZP_V1),y         ; A = note
    pha
    lda ZP_CNT1
    ora ZP_CNT1+1
    bne f1go
    pla
    lda #<v1_data
    sta ZP_V1
    lda #>v1_data
    sta ZP_V1+1
    rts
f1go:
    iny
    lda (ZP_V1),y         ; A = ctrl byte (waveform without gate)
    sta ZP_V1_CTRL
    pla                   ; A = note
    cmp #0
    beq f1rest_path

    ; NOTE event — store BASE frequency; apply_vibrato writes SID+7/+8.
    tax
    sec
    sbc #NOTE_LO
    tay
    lda freq_lo,y
    sta ZP_V2BASE_LO
    sta SID+7
    lda freq_hi,y
    sta ZP_V2BASE_HI
    sta SID+8

    ; Reset filter cutoff on every new note — hoover "wow" sweep
    lda #$C0            ; $E0->$C0: 8580 curve opens brighter, $C0 keeps the wow
    sta ZP_FILT_CUR

    ; Retrigger the envelope on EVERY note onset. The old code skipped
    ; the gate cycle on pitch changes (legato glide) which left most
    ; syllables with no attack transient — the lead floated, with no
    ; audible onset to lock against the kick. Re-articulating every note
    ; (8 ms attack = soft, not clicky) puts a transient on every grid
    ; position the melody hits. (cpx ZP_V2_LAST kept only for parity.)
f1retrig:
    lda ZP_V1_CTRL        ; gate off (waveform alone)
    sta SID+11
    ora #$01              ; OR gate -> attack
    sta SID+11
f1stash:
    stx ZP_V2_LAST
    jmp f1adv

f1rest_path:
    lda ZP_V1_CTRL        ; rest: waveform without gate -> release
    sta SID+11
    lda #0
    sta ZP_V2_LAST
f1adv:
    clc
    lda ZP_V1
    adc #4
    sta ZP_V1
    bcc f1done
    inc ZP_V1+1
f1done:
    rts

tick2:
    lda ZP_CNT2
    bne d2lo
    lda ZP_CNT2+1
    bne d2hi
    jmp fetch2
d2hi:
    dec ZP_CNT2+1
    dec ZP_CNT2
    rts
d2lo:
    dec ZP_CNT2
    rts

fetch2:
    ldy #0
    lda (ZP_V2),y
    sta ZP_CNT2+1
    iny
    lda (ZP_V2),y
    sta ZP_CNT2
    iny
    lda (ZP_V2),y
    pha
    lda ZP_CNT2
    ora ZP_CNT2+1
    bne f2go
    pla
    lda #<v2_data
    sta ZP_V2
    lda #>v2_data
    sta ZP_V2+1
    rts
f2go:
    iny
    lda (ZP_V2),y      ; ctrl
    pha
    iny
    lda (ZP_V2),y      ; ad
    sta SID+19
    iny
    lda (ZP_V2),y      ; sr
    sta SID+20
    tsx
    lda $0102,x        ; peek note (under ctrl)
    cmp #96
    bcc f2_note_ok
    lda #95
f2_note_ok:
    tax
    lda freq_lo,x
    sta SID+14
    lda freq_hi,x
    sta SID+15
    pla                ; ctrl
    pha
    and #$FE
    sta SID+18
    pla
    sta SID+18
    pla                ; pop note
    clc
    lda ZP_V2
    adc #6
    sta ZP_V2
    bcc f2done
    inc ZP_V2+1
f2done:
    rts

{bytes_to_asm('freq_lo', freq_lo)}
{bytes_to_asm('freq_hi', freq_hi)}

; Vibrato LFO: 16-step zigzag, ±6 freq units (~quarter-tone wobble at A4).
; vib_hi is the sign-extended high byte so the 16-bit add carries correctly.
{bytes_to_asm('vib_lo', [(v & 0xFF) for v in [0,2,4,6,6,4,2,0,0,-2,-4,-6,-6,-4,-2,0]])}
{bytes_to_asm('vib_hi', [0xFF if v < 0 else 0x00 for v in [0,2,4,6,6,4,2,0,0,-2,-4,-6,-6,-4,-2,0]])}
; Filter LFO: 16-step triangle, ±3 on cutoff HI byte — gentle flange shimmer.
{bytes_to_asm('filt_lfo', [(v & 0xFF) for v in [0,1,1,2,3,2,1,1,0,-1,-1,-2,-3,-2,-1,-1]])}
{bytes_to_asm('v0_data', v1_data)}
{bytes_to_asm('v1_data', v2_data)}
{bytes_to_asm('v2_data', v3_data)}
"""
    asm_path = '/tmp/friet_clean.s'
    prg_path = '/tmp/friet_clean.prg'
    with open(asm_path, 'w') as f:
        f.write(asm)
    r = subprocess.run(['xa', '-XMASM', '-o', prg_path, asm_path], capture_output=True, text=True)
    if r.returncode != 0:
        print("xa failed:")
        print(r.stdout)
        print(r.stderr)
        sys.exit(1)
    with open(prg_path, 'rb') as f:
        prg = f.read()
    prg = bytes([0x00, 0x10]) + prg
    print(f"Code load=$1000 size={len(prg)-2} bytes")

    def pad32(s):
        b = s.encode('ascii', errors='replace')[:31]
        return b + b'\0' * (32 - len(b))
    header = b'PSID'
    header += struct.pack('>H', 2)
    header += struct.pack('>H', 0x7C)
    header += struct.pack('>H', 0)
    header += struct.pack('>H', 0x1000)
    header += struct.pack('>H', 0x1003)
    header += struct.pack('>H', 1)
    header += struct.pack('>H', 1)
    header += struct.pack('>I', 0)
    # PSID metadata for the deFEEST / X2026 release.
    # Title is the song title (≤31 chars); Author = scene handles; Released
    # is "YYYY <PARTY>". Truncated automatically by pad32.
    header += pad32('Friet met Desire')
    header += pad32('Kloot, Anus & Augurk / deFEEST')
    header += pad32('2026 X / deFEEST + MAYO')
    # PSID flags: PAL (clock bits 2-3 = 01 -> 0x04) + MOS 8580 (model bits
    # 4-5 = 10 -> 0x20). Single SID. = 0x0024.
    header += struct.pack('>H', 0x0024)
    header += bytes([0, 0, 0, 0])
    assert len(header) == 0x7C
    os.makedirs(os.path.dirname(OUT_SID), exist_ok=True)
    with open(OUT_SID, 'wb') as f:
        f.write(header + prg)
    print(f"Wrote {OUT_SID} ({len(header) + len(prg)} bytes)")

if __name__ == '__main__':
    main()
