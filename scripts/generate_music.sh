#!/usr/bin/env bash
# Generate background music and sound effects using ffmpeg synthesis
# Styles: upbeat (130 BPM), romantic (100 BPM), epic (140 BPM), chill (90 BPM)

set -euo pipefail

# Defaults
STYLE="upbeat"
DURATION=60
BPM=130
OUTPUT_DIR="./assets/audio"
FFMPEG="/tmp/ffmpeg-7.0.2-amd64-static/ffmpeg"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --style STYLE      Music style: upbeat|romantic|epic|chill (default: upbeat)"
    echo "  --duration SECS    Music duration in seconds (default: 60)"
    echo "  --bpm BPM          Beats per minute (default: auto from style)"
    echo "  --output-dir DIR   Output directory (default: ./assets/audio)"
    echo "  --ffmpeg PATH      Path to ffmpeg binary"
    echo "  -h, --help         Show this help"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --style) STYLE="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        --bpm) BPM="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --ffmpeg) FFMPEG="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Auto-detect ffmpeg
if [ ! -f "$FFMPEG" ]; then
    if command -v ffmpeg &>/dev/null; then
        FFMPEG="ffmpeg"
    else
        echo "Error: ffmpeg not found. Run setup_tts.sh first." >&2
        exit 1
    fi
fi

# Set BPM from style if not overridden
case "$STYLE" in
    upbeat)   DEFAULT_BPM=130 ;;
    romantic) DEFAULT_BPM=100 ;;
    epic)     DEFAULT_BPM=140 ;;
    chill)    DEFAULT_BPM=90  ;;
    *) echo "Unknown style: $STYLE"; exit 1 ;;
esac

# Use default BPM if not explicitly set
if [ "$BPM" = "130" ] && [ "$STYLE" != "upbeat" ]; then
    BPM=$DEFAULT_BPM
fi

mkdir -p "$OUTPUT_DIR"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

BEAT_DUR=$(python3 -c "print(f'{60.0/$BPM:.4f}')")
HALF_BEAT=$(python3 -c "print(f'{30.0/$BPM:.4f}')")

echo "=== Generating Music ==="
echo "Style: $STYLE | BPM: $BPM | Duration: ${DURATION}s"

# --- Generate drum pattern ---
# Kick drum (low sine burst)
$FFMPEG -y -f lavfi -i "sine=frequency=60:duration=0.1" \
    -af "volume=0.8,apad=whole_dur=${BEAT_DUR}" \
    "$TMPDIR/kick.wav" 2>/dev/null

# Hi-hat (filtered noise)
$FFMPEG -y -f lavfi -i "anoisesrc=duration=0.05:color=white" \
    -af "highpass=f=8000,volume=0.3,apad=whole_dur=${HALF_BEAT}" \
    "$TMPDIR/hihat.wav" 2>/dev/null

# Snare (noise burst + tone)
$FFMPEG -y -f lavfi -i "anoisesrc=duration=0.08:color=pink" \
    -af "volume=0.5,apad=whole_dur=${BEAT_DUR}" \
    "$TMPDIR/snare.wav" 2>/dev/null

# --- Build pattern based on style ---
case "$STYLE" in
    upbeat|epic)
        # kick-hihat-snare-hihat pattern
        $FFMPEG -y -i "$TMPDIR/kick.wav" -i "$TMPDIR/hihat.wav" \
            -i "$TMPDIR/snare.wav" -i "$TMPDIR/hihat.wav" \
            -filter_complex "[0:a][1:a][2:a][3:a]concat=n=4:v=0:a=1[out]" \
            -map "[out]" "$TMPDIR/pattern.wav" 2>/dev/null
        ;;
    romantic|chill)
        # Softer: kick-rest-snare-rest
        $FFMPEG -y -f lavfi -i "anullsrc=r=44100:cl=mono" -t "$BEAT_DUR" "$TMPDIR/rest.wav" 2>/dev/null
        $FFMPEG -y -i "$TMPDIR/kick.wav" -i "$TMPDIR/rest.wav" \
            -i "$TMPDIR/snare.wav" -i "$TMPDIR/rest.wav" \
            -filter_complex "[0:a]volume=0.5[k];[2:a]volume=0.3[s];[k][1:a][s][3:a]concat=n=4:v=0:a=1[out]" \
            -map "[out]" "$TMPDIR/pattern.wav" 2>/dev/null
        ;;
esac

# Loop pattern to full duration
PATTERN_DUR=$(python3 -c "
import subprocess
r = subprocess.run(['${FFMPEG}', '-i', '${TMPDIR}/pattern.wav', '-f', 'null', '-'],
                   capture_output=True, text=True)
import re
m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', r.stderr)
if m:
    print(f'{int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3)):.4f}')
else:
    print('2.0')
")
LOOPS=$(python3 -c "import math; print(math.ceil($DURATION / $PATTERN_DUR))")

$FFMPEG -y -stream_loop "$LOOPS" -i "$TMPDIR/pattern.wav" -t "$DURATION" \
    -af "volume=0.4" "$TMPDIR/drums.wav" 2>/dev/null

# --- Generate bass/chord layer ---
case "$STYLE" in
    upbeat)
        BASS_FREQ=110  # A2
        CHORD_FREQS="220:330:440"  # A3+E4+A4
        ;;
    romantic)
        BASS_FREQ=130  # C3
        CHORD_FREQS="262:330:392"  # C4+E4+G4
        ;;
    epic)
        BASS_FREQ=98   # G2
        CHORD_FREQS="196:247:294"  # G3+B3+D4
        ;;
    chill)
        BASS_FREQ=87   # F2
        CHORD_FREQS="175:220:262"  # F3+A3+C4
        ;;
esac

# Bass line (sine wave with volume envelope)
$FFMPEG -y -f lavfi -i "sine=frequency=${BASS_FREQ}:duration=${DURATION}" \
    -af "volume=0.25,tremolo=f=2:d=0.3" \
    "$TMPDIR/bass.wav" 2>/dev/null

# Chord pad (multiple sine waves mixed)
IFS=':' read -r F1 F2 F3 <<< "$CHORD_FREQS"
$FFMPEG -y \
    -f lavfi -i "sine=frequency=${F1}:duration=${DURATION}" \
    -f lavfi -i "sine=frequency=${F2}:duration=${DURATION}" \
    -f lavfi -i "sine=frequency=${F3}:duration=${DURATION}" \
    -filter_complex "[0:a]volume=0.08[a];[1:a]volume=0.06[b];[2:a]volume=0.05[c];[a][b][c]amix=inputs=3:duration=first[out]" \
    -map "[out]" "$TMPDIR/chords.wav" 2>/dev/null

# --- Mix all layers ---
$FFMPEG -y -i "$TMPDIR/drums.wav" -i "$TMPDIR/bass.wav" -i "$TMPDIR/chords.wav" \
    -filter_complex \
    "[0:a]volume=0.5[d];[1:a]volume=0.4[b];[2:a]volume=0.3[c];[d][b][c]amix=inputs=3:duration=first:dropout_transition=0,afade=t=in:d=0.5,afade=t=out:st=$(python3 -c "print($DURATION - 3)"):d=3,alimiter=limit=0.95[out]" \
    -map "[out]" -ar 44100 "$OUTPUT_DIR/background-music.wav" 2>/dev/null

echo "Generated: background-music.wav (${DURATION}s, ${BPM} BPM, ${STYLE})"

# --- Generate Sound Effects ---
echo "=== Generating Sound Effects ==="

# Whoosh (filtered noise sweep)
$FFMPEG -y -f lavfi -i "anoisesrc=duration=0.6:color=brown" \
    -af "highpass=f=200,lowpass=f=4000,volume=0.7,afade=t=in:d=0.15,afade=t=out:st=0.3:d=0.3" \
    -ar 44100 "$OUTPUT_DIR/whoosh.wav" 2>/dev/null
echo "Generated: whoosh.wav"

# Boom (low frequency impact)
$FFMPEG -y -f lavfi -i "sine=frequency=40:duration=0.8" \
    -af "volume=0.9,afade=t=out:st=0.1:d=0.7" \
    -ar 44100 "$OUTPUT_DIR/boom.wav" 2>/dev/null
echo "Generated: boom.wav"

# Ding (high bell tone)
$FFMPEG -y -f lavfi -i "sine=frequency=1200:duration=0.5" \
    -af "volume=0.5,afade=t=out:st=0.05:d=0.45" \
    -ar 44100 "$OUTPUT_DIR/ding.wav" 2>/dev/null
echo "Generated: ding.wav"

# Record scratch (noise with pitch bend)
$FFMPEG -y -f lavfi -i "anoisesrc=duration=0.4:color=pink" \
    -af "vibrato=f=10:d=0.5,highpass=f=500,volume=0.6,afade=t=out:st=0.1:d=0.3" \
    -ar 44100 "$OUTPUT_DIR/record-scratch.wav" 2>/dev/null
echo "Generated: record-scratch.wav"

# Match ding (pleasant two-tone)
$FFMPEG -y \
    -f lavfi -i "sine=frequency=880:duration=0.3" \
    -f lavfi -i "sine=frequency=1100:duration=0.3" \
    -filter_complex "[0:a]afade=t=out:st=0.1:d=0.2[a];[1:a]adelay=150|150,afade=t=out:st=0.15:d=0.15[b];[a][b]amix=inputs=2:duration=first,volume=0.5[out]" \
    -map "[out]" -ar 44100 "$OUTPUT_DIR/match-ding.wav" 2>/dev/null
echo "Generated: match-ding.wav"

# Heartbeat (double thump)
$FFMPEG -y \
    -f lavfi -i "sine=frequency=50:duration=0.15" \
    -f lavfi -i "sine=frequency=45:duration=0.12" \
    -filter_complex "[0:a]volume=0.8,afade=t=out:d=0.15[a];[1:a]volume=0.6,adelay=250|250,afade=t=out:d=0.12[b];[a][b]amix=inputs=2:duration=longest,apad=whole_dur=0.8[out]" \
    -map "[out]" -ar 44100 "$OUTPUT_DIR/heartbeat.wav" 2>/dev/null
echo "Generated: heartbeat.wav"

# Warm chord (pleasant resolution)
$FFMPEG -y \
    -f lavfi -i "sine=frequency=262:duration=1.0" \
    -f lavfi -i "sine=frequency=330:duration=1.0" \
    -f lavfi -i "sine=frequency=392:duration=1.0" \
    -filter_complex "[0:a]volume=0.15[a];[1:a]volume=0.12[b];[2:a]volume=0.10[c];[a][b][c]amix=inputs=3:duration=first,afade=t=in:d=0.1,afade=t=out:st=0.5:d=0.5[out]" \
    -map "[out]" -ar 44100 "$OUTPUT_DIR/warm-chord.wav" 2>/dev/null
echo "Generated: warm-chord.wav"

echo ""
echo "=== All audio assets generated in: $OUTPUT_DIR ==="
ls -la "$OUTPUT_DIR"/*.wav
