#!/usr/bin/env python3
"""Main orchestrator for the viral video generator pipeline.

Generates a complete short-form vertical video from a text prompt:
1. Writes a scene-by-scene script
2. Generates video clips (Veo 3.1), voiceover (Piper TTS), and music (ffmpeg)
3. Normalizes clips, merges with xfade, mixes audio
4. Outputs final 1080x1920 MP4

Usage:
    python3 generate_video.py --prompt "A capybara builds a dating website" --style meme --output ./outputs/video.mp4
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# Tool paths
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
FFMPEG = "/tmp/ffmpeg-7.0.2-amd64-static/ffmpeg"
FFPROBE = "/tmp/ffmpeg-7.0.2-amd64-static/ffprobe"
PIPER = "/home/node/.local/bin/piper"
PIPER_MODEL = "/tmp/piper-voices/en_US-amy-medium.onnx"
VIDEO_SDK = os.path.expanduser("~/.claude/skills/generate-video/scripts/generate_video_sdk.js")


def check_dependencies():
    """Verify all required tools are installed."""
    missing = []

    if not os.path.exists(FFMPEG):
        missing.append(f"ffmpeg ({FFMPEG})")
    if not os.path.exists(PIPER):
        missing.append(f"piper ({PIPER})")
    if not os.path.exists(PIPER_MODEL):
        missing.append(f"piper voice model ({PIPER_MODEL})")
    if not os.path.exists(VIDEO_SDK):
        missing.append(f"generate-video SDK ({VIDEO_SDK})")
    if not os.environ.get("AI_GATEWAY_API_KEY"):
        missing.append("AI_GATEWAY_API_KEY environment variable")

    if missing:
        print("Missing dependencies:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print(f"\nRun: bash {os.path.join(SCRIPTS_DIR, 'setup_tts.sh')}", file=sys.stderr)
        sys.exit(1)


def generate_clip(prompt, output_path, duration=5, timeout=300):
    """Generate a single video clip using Veo 3.1.

    Args:
        prompt: Visual description for the scene
        output_path: Where to save the MP4
        duration: Clip duration in seconds
        timeout: Generation timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    models = [
        "google/veo-3.1-fast-generate-preview",
        "google/veo-3.1-generate-preview",
    ]

    for model in models:
        cmd = [
            "node", VIDEO_SDK,
            prompt,
            "--model", model,
            "--duration", str(duration),
            "--aspect-ratio", "9:16",
            "--output", output_path,
            "--timeout", str(timeout)
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 30
            )
            if result.returncode == 0 and os.path.exists(output_path):
                size = os.path.getsize(output_path)
                if size > 10000:  # > 10KB means real video
                    print(f"  Generated: {os.path.basename(output_path)} ({size/1024:.0f}KB)")
                    return True
        except subprocess.TimeoutExpired:
            print(f"  Timeout with model {model}", file=sys.stderr)
        except Exception as e:
            print(f"  Error with model {model}: {e}", file=sys.stderr)

    return False


def generate_voiceover(text, output_path, length_scale=1.0, sentence_silence=0.3):
    """Generate voiceover using Piper TTS.

    Args:
        text: Narration text
        output_path: Where to save the WAV
        length_scale: Speed factor (>1 = slower, <1 = faster)
        sentence_silence: Silence between sentences in seconds

    Returns:
        Duration of generated audio in seconds
    """
    cmd = [
        PIPER,
        "--model", PIPER_MODEL,
        "--output_file", output_path,
        "--length_scale", str(length_scale),
        "--sentence_silence", str(sentence_silence)
    ]

    result = subprocess.run(
        cmd, input=text, capture_output=True, text=True
    )

    if result.returncode != 0 or not os.path.exists(output_path):
        print(f"  TTS error: {result.stderr}", file=sys.stderr)
        return 0.0

    with wave.open(output_path, 'rb') as w:
        duration = w.getnframes() / w.getframerate()

    return duration


def generate_scene_assets(scene, clips_dir, audio_dir, clip_timeout=300):
    """Generate video clip and voiceover for a single scene.

    Returns:
        dict with clip and voiceover info
    """
    scene_id = scene['id']
    clip_file = f"scene{scene_id}.mp4"
    vo_file = f"scene{scene_id}-vo.wav"
    clip_path = os.path.join(clips_dir, clip_file)
    vo_path = os.path.join(audio_dir, vo_file)

    result = {
        'id': scene_id,
        'clip': clip_file,
        'voiceover': vo_file,
        'clip_ok': False,
        'vo_ok': False,
        'vo_duration': 0.0
    }

    # Generate video clip
    visual_prompt = scene.get('visual_prompt', '')
    if visual_prompt:
        result['clip_ok'] = generate_clip(
            visual_prompt, clip_path,
            duration=scene.get('duration', 5),
            timeout=clip_timeout
        )

    # Generate voiceover
    vo_text = scene.get('voiceover', '')
    if vo_text:
        duration = generate_voiceover(vo_text, vo_path)
        result['vo_ok'] = duration > 0
        result['vo_duration'] = duration

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Generate a complete short-form vertical video from a text prompt'
    )
    parser.add_argument('--prompt', required=True,
                       help='Video concept/prompt')
    parser.add_argument('--style', default='meme',
                       choices=['meme', 'promo', 'story', 'educational'],
                       help='Video style (default: meme)')
    parser.add_argument('--output', required=True,
                       help='Output MP4 file path')
    parser.add_argument('--scenes', type=str, default=None,
                       help='Path to pre-written scene-map.json (skip script generation)')
    parser.add_argument('--work-dir', default=None,
                       help='Working directory for intermediate files')
    parser.add_argument('--music-style', default='upbeat',
                       choices=['upbeat', 'romantic', 'epic', 'chill'],
                       help='Background music style (default: upbeat)')
    parser.add_argument('--music-bpm', type=int, default=None,
                       help='Background music BPM (default: auto from style)')
    parser.add_argument('--parallel-clips', type=int, default=3,
                       help='Max parallel video clip generations (default: 3)')
    parser.add_argument('--clip-timeout', type=int, default=300,
                       help='Timeout per clip generation in seconds (default: 300)')
    parser.add_argument('--skip-clips', action='store_true',
                       help='Skip clip generation (use existing clips)')
    parser.add_argument('--skip-music', action='store_true',
                       help='Skip music generation (use existing music)')

    args = parser.parse_args()
    check_dependencies()

    # Setup working directory
    if args.work_dir:
        work_dir = args.work_dir
    else:
        work_dir = tempfile.mkdtemp(prefix="viral-video-")

    clips_dir = os.path.join(work_dir, "clips")
    audio_dir = os.path.join(work_dir, "audio")
    norm_dir = os.path.join(work_dir, "normalized")

    for d in [clips_dir, audio_dir, norm_dir]:
        os.makedirs(d, exist_ok=True)

    print(f"=== Viral Video Generator ===")
    print(f"Prompt: {args.prompt}")
    print(f"Style: {args.style}")
    print(f"Work dir: {work_dir}")
    print()

    # Step 1: Load or expect scene map
    if args.scenes:
        scene_map_path = args.scenes
        with open(scene_map_path, 'r') as f:
            scene_data = json.load(f)
        print(f"Loaded {len(scene_data['scenes'])} scenes from {scene_map_path}")
    else:
        print("ERROR: --scenes (scene-map.json) is required.")
        print("Write your script first using the scene map format, then pass it here.")
        print("See references/script-templates.md for the scene structure.")
        sys.exit(1)

    scenes = scene_data['scenes']
    scene_map_path = os.path.join(work_dir, "scene-map.json")
    with open(scene_map_path, 'w') as f:
        json.dump(scene_data, f, indent=2)

    # Step 2: Generate assets
    start_time = time.time()

    # 2a: Generate video clips (parallel)
    if not args.skip_clips:
        print(f"\n--- Generating {len(scenes)} video clips (max {args.parallel_clips} parallel) ---")
        with ThreadPoolExecutor(max_workers=args.parallel_clips) as executor:
            futures = {}
            for scene in scenes:
                future = executor.submit(
                    generate_clip,
                    scene['visual_prompt'],
                    os.path.join(clips_dir, f"scene{scene['id']}.mp4"),
                    scene.get('duration', 5),
                    args.clip_timeout
                )
                futures[future] = scene['id']

            for future in as_completed(futures):
                scene_id = futures[future]
                try:
                    ok = future.result()
                    status = "OK" if ok else "FAILED"
                except Exception as e:
                    status = f"ERROR: {e}"
                print(f"  Scene {scene_id}: {status}")

    # 2b: Generate voiceovers
    print(f"\n--- Generating voiceovers ---")
    vo_files = []
    for scene in scenes:
        vo_text = scene.get('voiceover', scene.get('vo_text', ''))
        vo_file = f"scene{scene['id']}-vo.wav"
        vo_path = os.path.join(audio_dir, vo_file)

        if vo_text:
            dur = generate_voiceover(vo_text, vo_path)
            print(f"  Scene {scene['id']}: {dur:.1f}s - \"{vo_text[:50]}...\"")
            vo_files.append(vo_path)
            scene['voiceover'] = vo_file  # Update scene map

    # Concatenate voiceovers
    if vo_files:
        full_vo = os.path.join(audio_dir, "voiceover-full.wav")
        concat_script = os.path.join(SCRIPTS_DIR, "concat_audio.py")
        cmd = [sys.executable, concat_script] + vo_files + [
            "--silence", "0.4", "--output", full_vo
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        print(f"  Full voiceover: {full_vo}")

    # 2c: Generate music
    if not args.skip_music:
        print(f"\n--- Generating background music ({args.music_style}) ---")
        music_script = os.path.join(SCRIPTS_DIR, "generate_music.sh")
        music_cmd = [
            "bash", music_script,
            "--style", args.music_style,
            "--duration", "90",
            "--output-dir", audio_dir
        ]
        if args.music_bpm:
            music_cmd.extend(["--bpm", str(args.music_bpm)])
        subprocess.run(music_cmd, capture_output=True, text=True)

    # Save updated scene map
    with open(scene_map_path, 'w') as f:
        json.dump(scene_data, f, indent=2)

    # Step 3: Normalize clips
    print(f"\n--- Normalizing video clips ---")
    normalize_script = os.path.join(SCRIPTS_DIR, "normalize_clips.py")
    subprocess.run([
        sys.executable, normalize_script,
        "--clips-dir", clips_dir,
        "--audio-dir", audio_dir,
        "--scene-map", scene_map_path,
        "--output-dir", norm_dir
    ], capture_output=False)

    # Step 4: Assemble final video
    print(f"\n--- Assembling final video ---")
    assemble_script = os.path.join(SCRIPTS_DIR, "assemble_video.py")

    music_path = os.path.join(audio_dir, "background-music.wav")
    vo_full_path = os.path.join(audio_dir, "voiceover-full.wav")

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)

    subprocess.run([
        sys.executable, assemble_script,
        "--video-dir", norm_dir,
        "--voiceover", vo_full_path,
        "--music", music_path,
        "--sfx-dir", audio_dir,
        "--scene-map", scene_map_path,
        "--output", args.output
    ], capture_output=False)

    elapsed = time.time() - start_time

    if os.path.exists(args.output):
        size_mb = os.path.getsize(args.output) / (1024 * 1024)
        print(f"\n=== DONE ===")
        print(f"Output: {args.output} ({size_mb:.1f}MB)")
        print(f"Elapsed: {elapsed:.0f}s")
    else:
        print(f"\nError: Output file not created.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
