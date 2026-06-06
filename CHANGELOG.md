# Changelog

All notable changes to **Friet met Desire** are recorded here.
Dates are local (Europe/Amsterdam).

## 2026-06-06 — Happy-hardcore rewrite of the rhythm section

The lead vocal stays — that's the recognisable hook — but everything else
under it is rebuilt as authentic happy hardcore, dropping the verbatim
karaoke-MIDI replay for V1 + V3.

- **Tempo: 175 BPM** (genre canonical; was 175 → temporarily 150/160 during
  iteration → back to 175 once the mix supported it).
- **V1 bass: synthetic tresillo on the chord cycle.** Pumping Dm-F-Bb-C
  (i-III-VI-VII), one chord per 4-beat bar, six hits per bar at the
  3-3-2-sixteenth offsets `[0, 0.75, 1.5, 2, 2.75, 3.5]`. Roots in octave 2
  (D2 / F2 / Bb2 / C3). Breakdown gets a single sustained D2 sub-bass drone
  under the naked vocal instead. The karaoke MIDI's chorus source range
  (88–117.5) has no V1 content at all, so the verbatim-T5/T11/organ path
  was leaving V1 silent through every chorus — fixed by synthesising
  authentic HHC bass from scratch.
- **V1 contention resolved.** Each bass event truncates to fit before the
  next onset so V1 doesn't drift later in absolute time (was a silent bug:
  the encoder wrote each note's full dur_frames back-to-back without
  correcting overlap).
- **V2 lead: pulse waveform (25% PW)** for HHC stab character — cuts
  through the drum/bass mix where the previous triangle was being buried.
  Base octave still `-12` to land in Gala's actual sung register; chorus
  lift `+7` (perfect fifth) — `+12` read as too piercing under the
  brighter waveform.
- **V3 drums: rewritten per-section.** intro silent, verse closed-hat
  offbeat 8ths, prechorus rolling 16th hats (build), chorus open hat every
  offbeat (the "tssh tssh" shimmer), postchorus rolling 16ths, breakdown
  silent, breathe = kick + snare roll. Two-beat 16th-note snare fills at
  the tail of verse1 / prechorus1 / chorus1 lift into the next drop.
- **V3 noise channel hygiene.** `build_drum_timeline` now resolves
  overlapping events cleanly — each drum gets its own gate-on hold and
  gate-off, the timeline gap between events carries the previous drum's
  AD/SR so envelope releases finish at the drum's own rate. Without this
  fix, overlapping crash + kick + hat hits produced mid-envelope register
  changes that the SID renders as glitch artefacts.
- **Open hat as a distinct kit voice.** Added `open_hat` to `DRUM_KIT`
  with a 60 ms gate so the chorus shimmer rings the right length without
  bleeding into the next hit.
- **Crash duration capped at 1.6 s** (was 4 s) so the reverse-cymbal
  swell doesn't hog the noise channel through half a chorus and block
  kicks/hats.
- **Filter sweep retuned.** Resonance `$4` (was `$7` — peakier than the
  8580 wanted); cutoff init `$C0` decays to `$80` (less LP attenuation
  so the pulse lead keeps its harmonics); LFO ±3 shimmer; ZP_VIB_IDX
  now advanced from inside `filter_env` instead of from `apply_vibrato`
  (which is no longer in the play loop).

## 2026-06-03 — Koala demo: full-screen snackbar picture

- **New demo deliverable**: `out/friet_koala.prg` / `friet_koala.d64`
  (`make koala`) — a full-screen KoalaPainter (multicolor bitmap) snackbar
  scene + the SID + a beat-reactive colour cycle (border/bg step on each
  kick). Replaces the text-ticker as the visual "demo" version; the lyrics
  player stays as an extra.
- **Composition** chosen via an ADHD divergent-ideation run (5 frames → 30
  ideas → top-3 deepened): a split-depth TWO-POINT PERSPECTIVE — big
  foreground patatzak (messy dithered fries + mayo) clipped bottom-left, a
  steel counter receding to a neon "FRIET MET DESIRE" sign at the upper-right
  power point, frikandel speciaal (curry + uitjes) and kaassouffle staggered
  by depth.
- **`tools/make_koala.py`**: procedural art in numpy with ordered (Bayer)
  dithering for shading/gradients/neon-glow, irregular fry clump, and a
  `clash_lint()` that reports cells exceeding the C64 4-colours-per-cell
  limit. Writes `out/friet.koa` + the player .asm import bins.
- `src/player/friet_koala.asm`: multicolor-bitmap display (VIC bank 1,
  bitmap $6000, screen $5C00) + kick-locked colour cycle.

## 2026-06-03 — 8580/PAL target, submission polish, two deliverables

- **Committed to MOS 8580 + PAL.** PSID flags `0x0000 → 0x0024` (PAL clock +
  8580 model). Filter retuned for the 8580's brighter/near-linear cutoff curve
  and stronger resonance: res `$8→$7`, cutoff init/target `$80→$60`, per-note
  open `$E0→$C0`, filter LFO `±10→±6`. `render-preview.sh` now forces 8580+PAL
  (`-sidenginemodel 257 -pal`) — VICE's default is 6581, so every earlier
  preview was the wrong chip. (Determined + adversarially verified via a
  research workflow.)
- **Lyrics rewrite.** New `docs/friet_met_desire_lyrics.yaml` (primary ticker):
  frituur-meets-demoscene parody of FFD — crew is proud not poor, "Meer en
  meer", soldeerflux + lauwe energiedrank, the compo deadline, sporthal.
  Replaces the "nul bytes vrij" theme. `to_screen()` now renders `&`.
- **Two submission deliverables.**
  - Music compo (pure audio): `out/Friet_met_Desire-deFEEST.sid` +
    `out/friet_compo.prg` (new static-credit player, no ticker/strobe) +
    `out/friet_compo.d64` (`make compo`).
  - Lyrics floppy (bonus): `out/friet.d64` — the ticker/strobe player
    (`make disk`).
- **Shareable master:** `make master` → 192 kbps, +6.8 dB make-up gain,
  rendered on 8580.
- **Scene files:** `FRIET.NFO` and `docs/hvsc_stub.md` (Songlengths + STIL).
- Credits aligned to "Kloot, Anus & Augurk / deFEEST" (banner = SID author);
  pre-submission audit (28-agent workflow) cleared sync (91% of lyric lines
  within 30 ms — the loose feel is the deliberate 8th-grid prechorus), audio
  (clean, no clipping), and PSID-header correctness.

## 2026-05-30 — The "new standard": melody / sync / sound overhaul

Signed off by Anus as "the new standard — it rocks on all levels".
Full engine writeup in `docs/sound_engine.md`; new pitfalls 9–13 in
`AGENTS.md`; companion SID-craft notes in the demo repo
(`outline26-claude-c64` PR #39).

- **Frame-grid sync.** Drums + all FX moved onto the lead's zero-drift
  Bresenham 16th grid (`grid_frame`). ~30% of source drum hits had been on
  `round(beat * fbeat)` and flammed against the grid-snapped lead. The groove
  now locks.
- **Lead retrigger + legato-fill.** Every note re-articulates (no more silent
  legato glide that floated off the beat); each note extends to the next onset
  *minus a 2-frame gate-off* so the envelope hard-restarts cleanly. Killed 116
  ~80 ms blips and 19 of 21 silent gaps — the melody sings, continuous *and*
  accented.
- **Octave-up final chorus** (`chorus3` +12) for a climactic lift; `chorus3`
  back to fat saw (`$50` tri+pulse AND-combined to a thin, note-dropping tone —
  the "missing notes").
- **Aggressive plucky bass** (V1 attack `$0` → decay to ~40 % sustain).
- **Flange** on the lead: resonant filter sweep, res `$8` + cutoff-LFO `±10`
  (res `$A` / `±16` masked the fundamentals = muddy).
- **No more dead air.** `length_frames` tracks the actual last event (+ tail),
  not the synthetic 92-bar length that padded ~2 min of rests before the loop.
- **Smooth ending.** `render-preview.sh` gained an `afade`-out — and fixed the
  `SECONDS` bash-special-variable clash that had silently broken `-t` and the
  fade on *every* render.

## 2026-05-27 — ADHD lyrics: "Nul bytes vrij" constraint-war lyrics

- **ADHD divergence loop** (5 frames × 6 ideas → 30 → score/cluster → top 3
  deepened): generated constraint-war, raster-interrupt, and NFO-cult lyric
  angles. Documented in `docs/lyrics_adhd.md`.
- **"Nul bytes vrij" lyrics** written (`docs/nul_bytes_vrij_lyrics.yaml`):
  constraint-war stories over the existing T7 melody — 1K intro, zeropage
  starvation, cycle-counting. Refrein: "nul bytes vrij / maar het moet
  steeds kleiner / geen raster telt voor niks / geen cycle is te mager".
  Na-na section reworked as raster-interrupt ticking.
- **Lyric file priority** in `build_player.py`: nul_bytes_vrij.yaml →
  tl_buis_lyrics.yaml → karaoke fallback. Makefile dependency updated.
- **Temp files cleaned**, polish_plan/RELEASE.md/README updated.

## 2026-05-26 — Verbatim source layers, per-section waveform, interleaving bass

- **Back to verbatim source layers**: V2 plays T7 vocal verbatim, V3 plays
  T13 drums verbatim (section-filtered). No more synthetic HH patterns —
  the real source data is richer.
- **Per-section V2 waveform**: triangle in verse, sawtooth+hoover in chorus,
  pulse in final reprise. Each section has its own timbre character.
- **Interleaving bass**: V1 plays T6 grid positions (0, 1, 1.75, 2.5, 3.5
  beats per bar) computed per output bar so the bass **never collides with
  any V2 vocal note**. D2 pedal. Silent in intro/breathes. Call-and-response
  with the vocal — zero collisions per bar.
- **V3 section filtering**: verse=kick only, prechorus=kick+snare,
  chorus=full kit. Snare fills in breathe sections. Hat boost (8th on+off)
  in chorus2/3. Crash swell: long attack ($D), dark pitch (28), 4s gate.
- **ossh MIDI analysis**: added `Gala-freedfromdesire.mid` (128.5 BPM,
  15 tracks, 473 vocal notes). Full score transcription
  (`docs/score_transcription.md`) and voice essence (`docs/voice_essence.md`)
  documenting Pattern A (4-3-3-4) and Pattern B (3-3-2) engines.
- **Multiple source MIDIs analyzed**: karaoke, ossh, AUD_HO1152, AUD_RC5718.

## 2026-05-25 — Timbre polish, repo cleanup

- **Timbre tweaks**: V1 bass pulse width narrowed to 25% for a sharper stab
  feel; sustain lowered to $A for a snappier envelope. Hat duration shortened
  to 1 frame for a tighter tick.
- **Bass silent in intro/breathe bars**: V1 rests during intro and breathe
  sections so the swell + vocal have room.
- **MP4 video recording** added: `make mp4` captures a VICE screen recording
  of the `.prg` player into `out/friet.mp4` (gitignored -- regeneratable).
- **Intro title card timing fix**: credit line delayed to 2.4s so the title
  card is readable before scrolling starts.
- **Repo cleanup**: removed superseded docs (`chorus_melody.md`,
  `melody_theory.md`); gitignored generated files (`composition.yaml`,
  `lab_composition.yaml`, `friet.mp4`); updated README with research docs
  section.

## 2026-05-25 — Filter LFO, TL-Buis ticker, polish items closed

- **Filter LFO wobble** added: triangle-wave LFO (±4 on cutoff HI) creates a
  subtle phaser-like shimmer on V2. Resonance raised from $4 to $6 for a more
  pronounced sweep. LFO shares the free-running ZP_VIB_IDX phase with vibrato.
- **TL-Buis Dutch lyrics** fully wired into the standalone `.prg` ticker via
  `docs/tl_buis_lyrics.yaml`. Lyrics appear as full lines mapped to the
  OUTPUT timeline; English karaoke fallback kept when the yaml is absent.
  Timing: 0.0s title card → 2.4s credit → 7.4s verse (synced to vocal).
- **Polish plan items 1–8 marked ✅** — arrangement, drums, vibrato, reprise
  dynamics, TL-Buis lyrics all closed.
- **Docs cleaned up**: `polish_plan.md`, `RELEASE.md` updated with completed
  item lists. `Makefile` dependency added for `tl_buis_lyrics.yaml`.
- **Reproducible build**: `make all` builds release + workstage + previews.

## 2026-05-25 — T6 stab bass, clean HH drums, source vocal timing, lab sandbox

- **V1 bass reworked**: replaced T5 verbatim / T11 loop with T6-derived
  stab rhythm (4-3-3-4 sixteenths, positions 0, 1, 1.75, 2.5, 3.5 per
  bar). D-pedal in verses, chord-following Dm-F-Bb-C in choruses.
- **V3 drums reworked (FAST mode)**: synthetic HH kit replaces T13
  verbatim. Kick 4-on-floor + off-beat 8th hat everywhere, snare
  backbeat only in chorus/na-na sections. Cleaner and more appropriate
  for the happy-hardcore feel.
- **Vocal timing preserved**: T7 source timing is kept as-is, including
  the tresillo feel in the chorus. The syncope is the song's rhythmic
  identity, not a transcription artefact -- no 8th-grid quantization.
- **Lab sandbox**: added `src/lab.py` + `make lab` for experimental
  composition work, outputs `out/lab.sid` / `out/lab.mp3` with its own
  `docs/lab_composition.yaml`. Separate from the release pipeline.
- **Musicology research docs** added:
  - `docs/melody_understanding.md` — why the FFD melody works
  - `docs/midi_sources.md` — provenance of the karaoke MIDIs
  - `docs/rhythm_research.md` — analysis of FFD's rhythmic identity
- Documentation updated (README, AGENTS, RELEASE, polish_plan) to
  reflect the new arrangement.

## 2026-05-23 — Pipeline cleanup + release-name rename

- Deleted legacy direct-conversion scripts `src/midi2sid.py` and
  `src/midi2sid_hh.py` and their artefacts (`out/friet_from_desire*`).
  All builds now flow through the extract → compose → synth pipeline.
- Release file is now `out/friet.sid` (was `friet_hh.sid`), built by
  `make friet` (was `make hh-build`/`make hh`). Preview target is
  `make preview-friet`. The standalone C64 player is `out/friet.prg`
  (was `friet_player.prg`) and now embeds the release SID.
- `friet_clean.sid` and `friet_melody_only.sid` kept as workstage
  builds — used for shaving the arrangement without remixing the whole
  thing.
- Internal: env var `HH_TEMPO` → `FAST`; Python `HH_BPM` → `FAST_BPM`;
  player ASM source `src/player/friet_player.asm` → `friet.asm`.
- The `port` / `preview-port` make targets are gone.

## 2026-05-23 — Release target: X2026 / deFEEST

- PSID metadata updated: title "Friet met Desire",
  author "Kloot & Anus / deFEEST", released "2026 X / deFEEST".
- Added `docs/RELEASE.md` with scene-release metadata, arrangement
  description, and known gaps before the party.
- README + AGENTS.md updated with the deFEEST handles and the link to
  the companion demo (`outline26-claude-c64`).
- Makefile reworked: `make all` builds both the maintained build and
  the melody-only verification SID + previews; legacy direct-conversion
  scripts moved off the default chain.

## 2026-05-23 — Dynamic arrangement, audible swell, T11 hook bass

- `compose.py` defines a section table (intro → verse → pre-chorus → chorus
  → post-chorus → break → instrumental → verse2 → pre-chorus2 → chorus2 →
  outro) keyed off T2's `\` markers, then filters T13 drum hits per section
  so verses are kick-only, pre-choruses add snare, choruses go full kit.
- V1 now plays T11's 4-note "na-na" pattern (transposed −12 to bass
  register) looped from beat 5 until T5's actual bassline kicks in at
  beat 120 — no more sparse verses.
- During T11's natural section (~beat 184–248) V1 plays T11 verbatim at
  the original octave, then falls back to T5 for the outro.
- T12 reverse-cymbal swell envelope rewritten: 800 ms attack, sustain at
  $C, short release — sounds like a proper *whoosh* rising into each
  section instead of a 160 ms tick.
- `extract_patterns.py` now dumps T13 drum hits to `docs/song_layers.yaml`
  alongside T5/T7/T11/T12; nothing in the synth path reads MIDI anymore.

## 2026-05-22 — Recognisable melody (the milestone)

- Verified T7 IS the sung melody by aligning T2's Soft-Karaoke syllable
  markers to T7 note positions: each lyric beat lands on the expected
  T7 pitch. Documented in `docs/melody_analysis.md`.
- `extract_patterns.py` writes `docs/song_layers.yaml` and
  `docs/melody_lyrics.yaml` (verbatim T5 bass + T7 vocal + T11 hook +
  T12 SFX + lyric mapping).
- `compose.py` reads the layers and emits T5 + T7 verbatim instead of
  synthetic guesses. `MELODY_ONLY=1` env var renders the vocal alone.
- All voices play at source 130 BPM (mixing tempos broke alignment).

## 2026-05-21 — Cleanroom pipeline

- Three-stage extract → compose → synth chain; each stage reads only
  YAML written by the previous stage.
- `src/extract_patterns.py` produces `docs/song_spec.yaml` (BPM, key,
  1-bar rhythm grids, melodic contour, chord roots).
- `src/compose.py` produces `docs/composition.yaml`.
- `src/synth.py` emits PSID v2.
- Makefile targets: `analyze`, `extract`, `compose`, `synth`,
  `preview-clean`.

## 2026-05-21 — Initial commit

- Project organised: `src/`, `midi/`, `out/`, `stems/`, `docs/`,
  `tools/`.
- README + AGENTS.md + Makefile + render-preview.sh.
- Legacy direct-conversion scripts (`midi2sid.py`, `midi2sid_hh.py`)
  for comparison; not on the maintained pipeline.
- Pushed to `git@github.com:annejan/friet-met-desire.git`.
