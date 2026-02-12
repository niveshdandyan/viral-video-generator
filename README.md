# Viral Video Generator

End-to-end AI video production pipeline for short-form vertical videos (Instagram Reels, TikTok, YouTube Shorts).

## What It Does

Takes a text prompt and produces a complete 30-60 second vertical video with:
- **AI-generated video clips** (Google Veo 3.1)
- **Neural text-to-speech voiceover** (ElevenLabs / Piper TTS)
- **Background music + sound effects** (ElevenLabs Sound Generation / ffmpeg synthesis)
- **Professional assembly** with crossfade transitions, audio mixing, and proper encoding

```
Prompt -> Script -> [Parallel Generation] -> Assembly -> Final Video
                    |-- Video Clips (Veo 3.1)
                    |-- Voiceover (ElevenLabs / Piper TTS)
                    |-- Music + SFX
```

## Requirements

- **Python 3.10+**
- **ffmpeg** (auto-installed via `scripts/setup_tts.sh`)
- **AI_GATEWAY_API_KEY** env var (for Veo 3.1 video generation)
- **ELEVENLABS_API_KEY** env var (optional, for high-quality TTS and SFX)
- **generate-video skill** at `~/.claude/skills/generate-video/` (for Veo 3.1 SDK)

## Quick Start

```bash
# 1. Setup TTS and ffmpeg
bash scripts/setup_tts.sh

# 2. Generate a complete video
python3 scripts/generate_video.py \
  --prompt "A capybara uses AI to build a dating website" \
  --style meme \
  --output ./outputs/my-video.mp4
```

## Manual Workflow

For more control, run each step individually:

### Step 1: Write a Script

Create a `scene-map.json` using the templates in `references/script-templates.md`:

```json
{
  "scenes": [
    {
      "id": 1,
      "clip": "scene1.mp4",
      "voiceover": "scene1-vo.wav",
      "vo_text": "Monday morning. Cappy opens the laptop. One prompt. Deploy.",
      "visual_prompt": "Animated capybara at a desk with a glowing laptop...",
      "transition": "fade",
      "sfx": [{"type": "whoosh", "offset": 0}]
    }
  ]
}
```

### Step 2: Generate Assets (in Parallel)

**Video Clips:**
```bash
node ~/.claude/skills/generate-video/scripts/generate_video_sdk.js \
  "VISUAL_PROMPT" \
  --model "google/veo-3.1-fast-generate-preview" \
  --duration 6 --aspect-ratio "9:16" \
  --output scene1.mp4
```

**Voiceover (ElevenLabs):**
```python
import requests
r = requests.post(
    f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}',
    headers={'xi-api-key': API_KEY, 'Content-Type': 'application/json'},
    json={'text': 'Your narration', 'model_id': 'eleven_multilingual_v2'}
)
```

**Voiceover (Piper TTS - free fallback):**
```bash
echo "Your narration" | piper \
  --model /tmp/piper-voices/en_US-amy-medium.onnx \
  --output_file scene1-vo.wav
```

**Background Music + SFX:**
```bash
bash scripts/generate_music.sh --style upbeat --duration 60 --bpm 130 --output-dir ./assets/audio/
```

### Step 3: Normalize Clips

Loop/extend each video clip to match its voiceover duration:
```bash
python3 scripts/normalize_clips.py \
  --clips-dir ./assets/video-clips/ \
  --audio-dir ./assets/audio/ \
  --scene-map scene-map.json \
  --output-dir ./assets/normalized/
```

### Step 4: Assemble Final Video

Merge clips with transitions, mix audio layers, and encode:
```bash
python3 scripts/assemble_video.py \
  --video-dir ./assets/normalized/ \
  --voiceover ./assets/audio/voiceover-full.wav \
  --music ./assets/audio/background-music.wav \
  --sfx-dir ./assets/audio/ \
  --scene-map scene-map.json \
  --output ./output/final.mp4
```

## Output Specs

| Property | Value |
|----------|-------|
| Resolution | 1080x1920 (9:16 vertical) |
| Video codec | H.264 (libx264) |
| Frame rate | 30 fps |
| Audio codec | AAC 192kbps, 44.1kHz |
| Format | MP4 with faststart |

## Scripts

| Script | Purpose |
|--------|---------|
| `setup_tts.sh` | Install Piper TTS, voice model, and ffmpeg |
| `generate_video.py` | Main orchestrator (parallel clip gen + assembly) |
| `concat_audio.py` | Concatenate WAV files with silence gaps |
| `generate_music.sh` | Synthesize background music + SFX with ffmpeg |
| `normalize_clips.py` | Loop/extend clips to match voiceover durations |
| `assemble_video.py` | xfade merge + audio mixing + final encoding |

## Music Styles

| Style | BPM | Vibe |
|-------|-----|------|
| `upbeat` | 130 | Energetic meme/promo |
| `romantic` | 100 | Dating/love story |
| `epic` | 140 | Dramatic reveal |
| `chill` | 90 | Casual/explainer |

## SFX Types

`whoosh`, `boom`, `ding`, `record-scratch`, `match-ding`, `heartbeat`, `warm-chord`

When using ElevenLabs, SFX are generated from text descriptions for cinematic quality. The ffmpeg fallback synthesizes them from sine waves and noise.

## Tips for Viral Content

- **Hook in 2 seconds**: First scene must grab attention immediately
- **Short sentences**: Punchy narration. Comedic pauses. Dry humor.
- **Relatable problems**: Start with pain points the audience knows
- **Show, don't tell**: Visual storytelling over text walls
- **Emotional payoff**: End with a feel-good moment before CTA
- **Under 60s**: Instagram favors 30-60s; TikTok up to 90s

## License

MIT
