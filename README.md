# Friet met Desire

A Commodore 64 SID remix of Gala's "Freed from Desire" (1996), released by
**deFEEST** at the **X2026** demoparty. Composed by
**Kloot/deFEEST** (Claude), **Augurk/deFEEST** (Big Pickle / OpenCode),
and **Anus/deFEEST** ([annejan](https://github.com/annejan)). Companion demo:
[`outline26-claude-c64`](https://github.com/annejan/outline26-claude-c64)
("Kloten met de broodtrommel").

**Friet** is Dutch for fries — the title is a playful misreading of
"Freed". See [`docs/RELEASE.md`](docs/RELEASE.md) for the scene-release
metadata.

**Repo:** [github.com/annejan/friet-met-desire](https://github.com/annejan/friet-met-desire)

## Concept

The five MIDI files in `midi/` are **research material** — not source for a
direct transcription. They're studied for their patterns (drum grooves,
bassline rhythm, melodic contours, chord progressions). The output SIDs are
*remixes* that take those patterns and re-arrange them for the C64's 3-voice
SID chip in a happy-hardcore style.

### Pipeline

The build is a three-stage extract → compose → synth chain. Each stage
writes a YAML file the next stage reads, so a tweak at one level doesn't
require redoing the others.

```
midi/*.mid  ──>  extract_patterns.py  ──>  docs/song_spec.yaml    (patterns)
                                       \──>  docs/song_layers.yaml (verbatim notes)
                                                  │
                                                  ▼
                                            compose.py  ──>  docs/composition.yaml
                                                                       │
                                                                       ▼
                                                                 synth.py  ──>  out/friet_clean.sid
```

| Phase | Tool                        | Reads                                | Writes              |
|-------|-----------------------------|--------------------------------------|---------------------|
| 1     | `src/extract_patterns.py`   | the MIDI                             | `docs/song_spec.yaml` + `docs/song_layers.yaml` (verbatim note lists + organ + lyric markers) |
| 2     | `src/compose.py`            | spec + layers (no MIDI)              | `docs/composition.yaml` (sectioned event list) |
| 3     | `src/synth.py`              | composition only                     | `out/friet_clean.sid` (PSID v2) |

## Voice assignment

Only V2 (the lead vocal) plays MIDI-sourced material — that's the
recognisable hook. V1 (bass) and V3 (drums) are synthesised from scratch
to an authentic happy-hardcore template at 175 BPM:

| Section | V1 (synthetic HHC bass) | V2 (T7 vocal verbatim) | V3 (synthetic HHC kit) |
|---------|----|----|-----|
| Intro | silent | — | silent (riser crash from source T12) |
| Verse | tresillo on Dm/F/Bb/C | pulse 25% PW, base -12 | kick + clap + closed hat offbeat |
| Pre-chorus | tresillo continues | base -12 | rolling 16th hats (build) |
| Chorus 1 | tresillo continues | **+7 lift** (perfect fifth) | full kit + **open hat every offbeat** |
| Na-na | tresillo continues | +7 | rolling 16ths (drive) |
| Chorus 2 | tresillo continues | +7 | full kit + open hat shimmer |
| Breakdown | sustained D2 sub-bass drone | base -12 | silent |
| Chorus 3 | tresillo continues | +7 (climax sits an octave above verse) | full kit + open hat shimmer |

Section endings (verse1, prechorus1, chorus1) get a 2-beat 16th-note
snare-roll fill into the next section.

SID production tricks:
- **Pulse 25% PW** on V2 lead — odd-harmonic content cuts through the bass/drum mix
- **Tresillo (3-3-2)** on V1 — 6 hits per bar at offsets `[0, 0.75, 1.5, 2, 2.75, 3.5]`
- **Per-note filter sweep** on V2: cutoff $C0→$80 + LFO ±3 shimmer
- **Kick pitch-sweep**: 2 frames triangle at high pitch → noise body
- **Open hat as a distinct kit voice**: 60 ms gate so the chorus shimmer doesn't haze
- **Bresenham frame grid** (30/7 integer accumulation) for drift-free timing
- **Non-overlapping V3 scheduler**: each drum gets a clean gate-on hold + gate-off
  so overlapping events don't toggle AD/SR mid-envelope

## Layout

```
friet/
├── README.md               this file
├── LICENSE.md              MIT for our code; fair-use note for the song
├── CHANGELOG.md            day-by-day record of major changes
├── AGENTS.md               notes for future AI sessions: pitfalls, gotchas
├── Makefile                all build targets
├── midi/                   5 source MIDIs (karaoke + ossh + AUD transcriptions)
├── stems/                  per-track MIDI stems (role-named: vocal.mid, bass.mid, etc.)
├── src/
│   ├── analyze_midi.py     dump per-track stems + textual analysis
│   ├── extract_patterns.py phase 1: MIDI → song_spec + song_layers
│   ├── compose.py          phase 2: layers → composition (per-section V1 switching)
│   ├── synth.py            phase 3: composition → PSID (PWM sweep, kick pitch-sweep)
│   ├── lab.py              experimental composition sandbox (make lab)
│   ├── build_player.py     bundles SID + lyrics into 3 .prg players (lyric ticker, compo, demo)
│   └── player/             KickAssembler source (friet.asm, friet_compo.asm, friet_koala.asm)
├── docs/
│   ├── melody_understanding.md  canonical melody theory
│   ├── voice_essence.md         DNA of each instrument (Pattern A/B engines)
│   ├── score_transcription.md   beat-by-beat 16th-grid (ossh MIDI)
│   ├── sheet_music.md           bladmuziek voor zangers + muzikanten
│   ├── lyric_writing_guide.md   rhythm templates for writing lyrics
│   ├── lyrics_melody_harmony.md combined lyrics × melody × chord analysis
│   ├── lyrics.md                TL-Buis Dutch parody lyrics (work in progress)
│   ├── midi_sources.md          5-MIDI comparison + provenance
│   ├── rhythm_research.md       drums/bass coupling research
│   ├── song_analysis.md         music theory: key/chords/structure
│   ├── melody_analysis.md       phrase-by-phrase T7 vocal analysis
│   ├── friet_met_desire_lyrics.yaml frituur/demoscene lyrics (PRIMARY ticker)
│   ├── nul_bytes_vrij_lyrics.yaml constraint-war lyrics (fallback)
│   ├── tl_buis_lyrics.yaml      TL-Buis Dutch parody lyrics (fallback)
│   ├── polish_plan.md           completed work log
│   └── RELEASE.md               scene-release metadata
├── tools/
│   └── render-preview.sh   headless vsid → WAV → MP3
├── out/                    generated deliverables
└── .venv/                  Python venv (mido, numpy, pyyaml)
```

## Build

```sh
source .venv/bin/activate

# Release build (175 BPM — this is the final track):
make friet                          # → out/friet.sid
make preview-friet                  # → out/friet.mp3

# The one-file C64 demo (koala bitmap + 8 spinning 3D cubes + lyric ticker):
make koala                          # → out/friet.prg  (+ out/friet.d64)

# Standalone C64 .prg with just the lyric ticker + kick strobe:
make player                         # → out/friet_lyrics.prg

# Competition SID (HVSC-ready, scene-standard filename):
make compo                          # → out/Friet_met_Desire-deFEEST.sid

# Workstages:
make extract compose synth          # → out/friet_clean.sid (130 BPM)
make melody-only preview-melody     # → vocal only

# Lab sandbox:
make lab                            # → out/lab.sid + out/lab.mp3

# Research:
make analyze                        # dump per-track stems
```

Listen interactively: `vsid out/friet.sid`.

## Research docs

Seven research documents capture the musicology work:

- **[melody_understanding.md](docs/melody_understanding.md)** — 4-pitch
  vocabulary, tresillo vs straight 8ths, chord colour.
- **[voice_essence.md](docs/voice_essence.md)** — Pattern A (organ stab)
  and Pattern B (tresillo bass): the two rhythmic engines.
- **[score_transcription.md](docs/score_transcription.md)** — bar-by-bar
  16th-grid from the ossh MIDI (128.5 BPM, 15 tracks).
- **[sheet_music.md](docs/sheet_music.md)** — bladmuziek for singers and
  musicians with note values (staccato 16ths + held 8th accents).
- **[lyric_writing_guide.md](docs/lyric_writing_guide.md)** — rhythm
  templates per phrase for writing lyrics in any language.
- **[midi_sources.md](docs/midi_sources.md)** — comparison of all 5 MIDIs.
- **[rhythm_research.md](docs/rhythm_research.md)** — drums/bass coupling
  and why the chorus tresillo must not be quantized.

## Tools required

- `xa` — 6502 cross-assembler (with `-XMASM` for `:` in comments)
- `vsid` from VICE (C64 ROMs at `/usr/share/vice/C64/`)
- Python venv with `mido`, `numpy`
- `ffmpeg` for WAV → MP3
- KickAssembler for the .prg player

Note: `sidplayfp` is broken on the dev box. Use `vsid`.

## Copyright / Fair use

See [LICENSE.md](LICENSE.md). MIT for our code; the underlying
composition is © 1996 Gala Rizzatto / Maurizio Molella / Filippo Carmeni;
the karaoke MIDIs are someone else's transcriptions; this repo is a
transformative fan/educational remix with no commercial intent.
