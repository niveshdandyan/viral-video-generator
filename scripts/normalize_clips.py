#!/usr/bin/env python3
"""Normalize video clips to match voiceover durations.

For each scene, extends/loops the video clip to match the voiceover duration,
scales to 1080x1920 (9:16), and normalizes to 30fps H.264.
"""

import argparse
import json
import os
import subprocess
import sys
import wave


FFMPEG = "/tmp/ffmpeg-7.0.2-amd64-static/ffmpeg"
FFPROBE = "/tmp/ffmpeg-7.0.2-amd64-static/ffprobe"


def find_ffmpeg():
    """Find ffmpeg binary."""
    global FFMPEG, FFPROBE
    if os.path.exists(FFMPEG):
        return
    # Try system ffmpeg
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.exists(path):
            FFMPEG = path
            FFPROBE = path.replace("ffmpeg", "ffprobe")
            return
    print("Error: ffmpeg not found. Run setup_tts.sh first.", file=sys.stderr)
    sys.exit(1)


def get_video_duration(path):
    """Get video duration in seconds."""
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        print(f"Warning: Could not get duration of {path}", file=sys.stderr)
        return 5.0


def get_wav_duration(path):
    """Get WAV file duration in seconds."""
    with wave.open(path, 'rb') as w:
        return w.getnframes() / w.getframerate()


def normalize_clip(clip_path, target_duration, output_path, padding=0.5):
    """Normalize a video clip to target duration.

    Args:
        clip_path: Input video file
        target_duration: Desired duration in seconds
        output_path: Output video file
        padding: Extra seconds to add for transition overlap
    """
    target = target_duration + padding

    cmd = [
        FFMPEG, "-y",
        "-stream_loop", "-1",
        "-i", clip_path,
        "-t", f"{target:.3f}",
        "-vf", ("scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
                "fps=30,format=yuv420p"),
        "-an",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error normalizing {clip_path}: {result.stderr}", file=sys.stderr)
        return False

    actual_dur = get_video_duration(output_path)
    print(f"  {os.path.basename(clip_path)} -> {os.path.basename(output_path)} "
          f"({actual_dur:.1f}s, target: {target:.1f}s)")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Normalize video clips to match voiceover durations'
    )
    parser.add_argument(
        '--clips-dir', required=True,
        help='Directory containing raw video clips'
    )
    parser.add_argument(
        '--audio-dir', required=True,
        help='Directory containing per-scene voiceover WAVs'
    )
    parser.add_argument(
        '--scene-map', required=True,
        help='Path to scene-map.json'
    )
    parser.add_argument(
        '--output-dir', required=True,
        help='Directory for normalized output clips'
    )
    parser.add_argument(
        '--padding', type=float, default=0.5,
        help='Extra padding in seconds for transition overlap (default: 0.5)'
    )

    args = parser.parse_args()
    find_ffmpeg()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load scene map
    with open(args.scene_map, 'r') as f:
        scene_data = json.load(f)

    scenes = scene_data.get('scenes', [])
    if not scenes:
        print("Error: No scenes found in scene map.", file=sys.stderr)
        sys.exit(1)

    print(f"=== Normalizing {len(scenes)} clips ===")

    success_count = 0
    for scene in scenes:
        scene_id = scene.get('id', '?')
        clip_file = scene.get('clip', '')
        vo_file = scene.get('voiceover', '')

        clip_path = os.path.join(args.clips_dir, clip_file)
        vo_path = os.path.join(args.audio_dir, vo_file)
        output_path = os.path.join(args.output_dir, f"norm-scene{scene_id}.mp4")

        if not os.path.exists(clip_path):
            print(f"  Warning: Missing clip: {clip_path}", file=sys.stderr)
            continue

        # Get target duration from voiceover
        if os.path.exists(vo_path):
            target_duration = get_wav_duration(vo_path)
        else:
            # Fallback: use original clip duration
            print(f"  Warning: Missing voiceover {vo_path}, using clip duration",
                  file=sys.stderr)
            target_duration = get_video_duration(clip_path)

        if normalize_clip(clip_path, target_duration, output_path, args.padding):
            success_count += 1

    print(f"\n=== Normalized {success_count}/{len(scenes)} clips to {args.output_dir} ===")


if __name__ == '__main__':
    main()
