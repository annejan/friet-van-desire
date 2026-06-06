# Friet met Desire — build SID remixes from MIDI research material
#
# Pipeline: extract -> compose -> synth.
#   make friet           the release SID (175 BPM, hoover lead)
#   make preview-friet   .mp3 preview of the release
#   make player          standalone C64 .prg (embeds friet.sid + lyric ticker)
#   make compo           clean competition .sid (same as friet.sid, separate file)
#   make preview-clean   song-faithful workstage render (130 BPM)
#   make preview-melody  vocal-only workstage (verification)
.PHONY: all clean analyze extract compose synth \
        clean-pipeline melody-only friet lab compo disk master koala koala-art koala-edit \
        preview preview-clean preview-melody preview-friet preview-lab player

SHELL      := /bin/bash
.ONESHELL:

PYTHON     := .venv/bin/python
SRC_DIR    := src
OUT_DIR    := out
MIDI_DIR   := midi
TOOLS_DIR  := tools

SPEC       := docs/song_spec.yaml
LAYERS     := docs/song_layers.yaml
COMP       := docs/composition.yaml

CLEAN_SID  := $(OUT_DIR)/friet_clean.sid
CLEAN_MP3  := $(OUT_DIR)/friet_clean.mp3
MELODY_SID := $(OUT_DIR)/friet_melody_only.sid
MELODY_MP3 := $(OUT_DIR)/friet_melody_only.mp3
FRIET_SID  := $(OUT_DIR)/friet.sid
FRIET_MP3  := $(OUT_DIR)/friet.mp3
FRIET_PRG  := $(OUT_DIR)/friet_lyrics.prg
FRIET_D64  := $(OUT_DIR)/friet_lyrics.d64
FRIET_COMPO_PRG := $(OUT_DIR)/friet_compo.prg
COMPO_D64  := $(OUT_DIR)/friet_compo.d64
KOALA_KOA  := $(OUT_DIR)/friet.koa
KOALA_PRG  := $(OUT_DIR)/friet.prg
KOALA_D64  := $(OUT_DIR)/friet.d64
KLA_SRC    := LegerZuigtPenisCroLLer.kla
LAB_SID    := $(OUT_DIR)/lab.sid
LAB_MP3    := $(OUT_DIR)/lab.mp3

PREVIEW_SECONDS ?= 90
LAB_SECONDS     ?= 30

all: clean-pipeline melody-only friet preview-clean preview-melody preview-friet

# --- research ----
analyze:
	$(PYTHON) $(SRC_DIR)/analyze_midi.py

# --- pipeline (extract -> compose -> synth) ----
# Phase 1: MIDI -> docs/song_spec.yaml (patterns) + docs/song_layers.yaml
#          (verbatim T5/T7/T11/T12/T13 note lists). The MIDI isn't read again.
extract: $(SPEC) $(LAYERS)
$(SPEC) $(LAYERS): $(SRC_DIR)/extract_patterns.py $(MIDI_DIR)/Gala_Freed_From_Desire.mid
	$(PYTHON) $<

# Phase 2: spec + layers -> docs/composition.yaml. No MIDI access.
compose: $(COMP)
$(COMP): $(SRC_DIR)/compose.py $(SPEC) $(LAYERS)
	$(PYTHON) $<

# Phase 3: composition -> PSID. Reads only composition.yaml.
synth: $(CLEAN_SID)
$(CLEAN_SID): $(SRC_DIR)/synth.py $(COMP)
	$(PYTHON) $<

clean-pipeline: $(CLEAN_SID)

preview-clean: $(CLEAN_MP3)
$(CLEAN_MP3): $(CLEAN_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

# Vocal-only verification build — useful when the surrounding mix obscures
# the melody and you need to confirm the notes themselves.
melody-only: $(MELODY_SID)
$(MELODY_SID): $(SRC_DIR)/compose.py $(SRC_DIR)/synth.py $(SPEC) $(LAYERS)
	MELODY_ONLY=1 $(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py
	cp $(CLEAN_SID) $@
	$(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py

preview-melody: $(MELODY_MP3)
$(MELODY_MP3): $(MELODY_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

# Release build — 175 BPM with hoover lead. This is the final SID.
friet: $(FRIET_SID)
$(FRIET_SID): $(SRC_DIR)/compose.py $(SRC_DIR)/synth.py $(SPEC) $(LAYERS)
	FAST=1 $(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py
	cp $(CLEAN_SID) $@
	$(PYTHON) $(SRC_DIR)/compose.py
	$(PYTHON) $(SRC_DIR)/synth.py

preview-friet: $(FRIET_MP3)
$(FRIET_MP3): $(FRIET_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(PREVIEW_SECONDS)

# Music-compo deliverables — PURE AUDIO, no lyrics, no strobe:
#   1. the clean PSID (HVSC-ready), and
#   2. a .d64 holding the static-credit pure-audio player ($(FRIET_COMPO_PRG),
#      built by build_player.py) PLUS the raw SID.
# (The lyric/visual version is the separate $(FRIET_D64) — see `make disk`.)
COMPO_SID := $(OUT_DIR)/Friet_met_Desire-deFEEST.sid
compo: $(COMPO_SID) $(COMPO_D64)
$(COMPO_SID): $(FRIET_SID)
	cp $< $@
	@echo "Competition SID: $@"
$(COMPO_D64): $(FRIET_PRG) $(COMPO_SID)
	c1541 -format "friet met desire,fd" d64 $@ \
	  -write $(FRIET_COMPO_PRG) "friet met desire" \
	  -write $(COMPO_SID) "friet.sid" >/dev/null
	@echo "Music-compo disk: $@"
	@c1541 $@ -dir

# Experimental sandbox — short loop of a fragment + hand-written
# beat/bass pattern. Tweak src/lab.py SETTINGS and re-run `make lab`.
lab: $(LAB_MP3)
$(LAB_SID): $(SRC_DIR)/lab.py $(SRC_DIR)/synth.py $(LAYERS)
	$(PYTHON) $(SRC_DIR)/lab.py
$(LAB_MP3): $(LAB_SID)
	$(TOOLS_DIR)/render-preview.sh $< $@ $(LAB_SECONDS)
preview-lab: $(LAB_MP3)

# Stand-alone C64 .prg that plays the release SID with a lyric ticker.
# Build with KickAssembler (kickass/KickAss.jar). Run with `x64sc out/friet.prg`.
player: $(FRIET_PRG)
$(FRIET_PRG): $(SRC_DIR)/build_player.py $(SRC_DIR)/player/friet.asm \
              $(FRIET_SID) docs/friet_met_desire_lyrics.yaml \
              docs/nul_bytes_vrij_lyrics.yaml docs/tl_buis_lyrics.yaml
	$(PYTHON) $(SRC_DIR)/build_player.py

# Floppy deliverable — a .d64 holding the standalone lyric-ticker player
# (kick-strobe + lyrics). This is the WITH-LYRICS version for the disk; the
# music-compo entry is the animation-free $(COMPO_SID) instead.
# Load on a C64 with:  LOAD"FRIET MET DESIRE",8,1  then  RUN
disk: $(FRIET_D64)
$(FRIET_D64): $(FRIET_PRG)
	c1541 -format "friet met desire,fd" d64 $@ -write $< "friet met desire" >/dev/null
	@echo "Floppy: $@"
	@c1541 $@ -dir

# Demo deliverable — full-screen KoalaPainter snackbar picture + the SID +
# a beat-reactive colour cycle (border/bg step on every kick). This is the
# "demo" version (the music-compo entry is the pure-audio $(FRIET_COMPO_PRG)).
# Load on a C64 with:  LOAD"FRIET MET DESIRE",8,1  then  RUN
koala: $(KOALA_D64)
# Demo = the dragon (Miep) mixed into a nicer composition (warm glow-vignette
# background + frikandel speciaal in his mouth, tools/mix_koala.py) as the
# full-screen bitmap, + 8 flying/spinning 3D-cube hardware sprites + a
# raster-split lyric ticker + a song-structure escalation arc + the SID.
# (Alt art: kla_to_bins.py = plain .kla; make_koala.py = procedural snackbar
# via `make koala-art`.)
$(KOALA_KOA): FrietFromDesireMiep.kla $(TOOLS_DIR)/mix_koala.py
	$(PYTHON) $(TOOLS_DIR)/mix_koala.py
koala-art:
	$(PYTHON) $(TOOLS_DIR)/make_koala.py
# Build the demo from a HAND-EDITED koala instead of the procedural composite.
# Export the current art with `cp out/friet.koa FrietDemo_edit.kla` (already
# done), edit FrietDemo_edit.kla in Multipaint/KoalaPainter, then `make
# koala-edit`. This bypasses mix_koala (so your edits aren't overwritten).
koala-edit:
	$(PYTHON) $(TOOLS_DIR)/kla_to_bins.py FrietDemo_edit.kla
	$(PYTHON) $(SRC_DIR)/build_player.py
	@echo "Demo built from FrietDemo_edit.kla -> $(KOALA_PRG)"
# 32 rotation frames of the 3D cube, from the Spritemate .spm. Lives at $4440
# (just past the grown SID); the text screen moved to $5800 to make room.
$(SRC_DIR)/player/sprite_cube.bin: $(TOOLS_DIR)/spm_to_sprites.py FinaLKjoep32.spm
	$(PYTHON) $(TOOLS_DIR)/spm_to_sprites.py FinaLKjoep32.spm $@ 1
$(KOALA_PRG): $(KOALA_KOA) $(SRC_DIR)/player/friet_koala.asm \
              $(SRC_DIR)/player/sprite_cube.bin $(SRC_DIR)/build_player.py $(FRIET_SID) \
              docs/friet_met_desire_lyrics.yaml
	$(PYTHON) $(SRC_DIR)/build_player.py
$(KOALA_D64): $(KOALA_PRG)
	c1541 -format "friet met desire,fd" d64 $@ -write $(KOALA_PRG) "friet" >/dev/null
	@echo "Demo (koala) disk: $@"
	@c1541 $@ -dir

# Shareable audio master — 192 kbps, +6.8 dB make-up gain (verified 0 clips),
# smooth 10s fade, rendered on 8580. The .sid/.prg is the actual entry; this
# MP3 is only for sharing/preview (a SID plays at its own chip volume on a PA).
master: $(FRIET_SID)
	FAST=1 $(PYTHON) $(SRC_DIR)/compose.py >/dev/null
	SECS=$$($(PYTHON) -c "import yaml,math;print(math.ceil(yaml.safe_load(open('$(COMP)'))['length_frames']/50))")
	$(TOOLS_DIR)/render-preview.sh $(FRIET_SID) $(FRIET_MP3) $$SECS 10 192k 6.8
	$(PYTHON) $(SRC_DIR)/compose.py >/dev/null

# --- previews ----
preview: preview-clean preview-melody preview-friet

clean:
	rm -f $(OUT_DIR)/*.sid $(OUT_DIR)/*.wav $(OUT_DIR)/*.mp3 $(OUT_DIR)/*.prg
	rm -f docs/lab_composition.yaml
	rm -f /tmp/freed*.s /tmp/freed*.prg
