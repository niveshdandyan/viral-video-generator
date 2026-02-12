#!/usr/bin/env python3
"""Assemble final video from normalized clips, voiceover, music, and SFX.

Pipeline:
1. Iterative xfade merge of video clips (fade/slideright/slideup transitions)
2. Mix voiceover + background music + positioned SFX
3. Combine video + audio with AAC 192kbps
4. Apply movflags +faststart for web playback
"""

import argparse
import json
import os
import subprocess
import sys
import wave


FFMPEG = "/tmp/ffmpeg-7.0.2-amd64-static/ffmpeg"
FFPROBE = "/tmp/ffmpeg-7.0.2-amd64-static/ffprobe"

TRANSITIONS = ["fade", "slideright", "slideup", "slideleft", "fadeblack", "smoothleft"]
TRANSITION_DURATION = 0.3


def find_ffmpeg():
    """Find ffmpeg binary."""
    global FFMPEG, FFPROBE
    if os.path.exists(FFMPEG):
        return
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.exists(path):
            FFMPEG = path
            FFPROBE = path.replace("ffmpeg", "ffprobe")
            return
    print("Error: ffmpeg not found. Run setup_tts.sh first.", file=sys.stderr)
    sys.exit(1)


def get_duration(path):
    """Get media file duration in seconds."""
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def get_wav_duration(path):
    """Get WAV duration in seconds."""
    with wave.open(path, 'rb') as w:
        return w.getnframes() / w.getframerate()


def xfade_merge(clips, output_dir, transition_duration=0.3):
    """Iteratively merge clips with xfade transitions.

    Returns path to merged video file.
    """
    if not clips:
        print("Error: No clips to merge.", file=sys.stderr)
        sys.exit(1)

    if len(clips) == 1:
        return clips[0]

    print(f"=== Merging {len(clips)} clips with xfade ===")

    current = clips[0]

    for i in range(1, len(clips)):
        next_clip = clips[i]
        output = os.path.join(output_dir, f"merge-{i+1}.mp4")

        # Get duration of current merged video
        dur = get_duration(current)
        offset = dur - transition_duration

        if offset <= 0:
            offset = 0.1

        # Pick transition
        transition = TRANSITIONS[i % len(TRANSITIONS)]

        cmd = [
            FFMPEG, "-y",
            "-i", current,
            "-i", next_clip,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition={transition}:duration={transition_duration}:offset={offset:.3f}[v]",
            "-map", "[v]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            output
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Error merging clip {i+1}: {result.stderr[-200:]}", file=sys.stderr)
            # Try without transition as fallback
            cmd_fallback = [
                FFMPEG, "-y",
                "-i", current, "-i", next_clip,
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                "-map", "[v]", "-c:v", "libx264", "-preset", "fast",
                "-crf", "23", "-pix_fmt", "yuv420p", output
            ]
            subprocess.run(cmd_fallback, capture_output=True, text=True)

        merged_dur = get_duration(output)
        print(f"  + Scene {i+1} ({transition}) -> {merged_dur:.1f}s")
        current = output

    final_dur = get_duration(current)
    print(f"  Total merged: {final_dur:.1f}s")
    return current


def mix_audio(voiceover, music, sfx_dir, scene_map, output, total_duration):
    """Mix voiceover, background music, and SFX into a single audio track.

    Args:
        voiceover: Path to full voiceover WAV
        music: Path to background music WAV
        sfx_dir: Directory containing SFX files
        scene_map: Parsed scene map dict
        output: Output WAV path
        total_duration: Total video duration for music fade
    """
    print("=== Mixing Audio ===")

    inputs = []
    filter_parts = []
    stream_labels = []
    input_idx = 0

    # Voiceover
    inputs.extend(["-i", voiceover])
    filter_parts.append(f"[{input_idx}:a]aresample=44100,volume=1.3[vo]")
    stream_labels.append("[vo]")
    input_idx += 1

    # Background music
    if music and os.path.exists(music):
        inputs.extend(["-i", music])
        fade_out_start = max(0, total_duration - 3)
        filter_parts.append(
            f"[{input_idx}:a]volume=0.12,"
            f"afade=t=in:d=0.5,"
            f"afade=t=out:st={fade_out_start:.1f}:d=3[bg]"
        )
        stream_labels.append("[bg]")
        input_idx += 1

    # SFX from scene map
    scenes = scene_map.get('scenes', [])
    cumulative_time = 0.0
    sfx_count = 0

    for scene in scenes:
        vo_file = scene.get('voiceover', '')
        vo_path = os.path.join(os.path.dirname(voiceover), vo_file) if vo_file else ''

        scene_sfx_list = scene.get('sfx', [])
        for sfx_entry in scene_sfx_list:
            sfx_type = sfx_entry.get('type', '')
            sfx_offset = sfx_entry.get('offset', 0)

            # Find SFX file
            sfx_file = os.path.join(sfx_dir, f"{sfx_type}.wav")
            if not os.path.exists(sfx_file):
                continue

            delay_ms = int((cumulative_time + sfx_offset) * 1000)
            inputs.extend(["-i", sfx_file])
            label = f"sfx{sfx_count}"
            filter_parts.append(
                f"[{input_idx}:a]aresample=44100,volume=0.25,"
                f"adelay={delay_ms}|{delay_ms}[{label}]"
            )
            stream_labels.append(f"[{label}]")
            input_idx += 1
            sfx_count += 1

        # Advance cumulative time
        if vo_path and os.path.exists(vo_path):
            try:
                cumulative_time += get_wav_duration(vo_path) + 0.4
            except Exception:
                cumulative_time += 5.0
        else:
            cumulative_time += 5.0

    # Build amix
    n_inputs = len(stream_labels)
    mix_input = "".join(stream_labels)
    filter_parts.append(
        f"{mix_input}amix=inputs={n_inputs}:duration=first"
        f":dropout_transition=0,alimiter=limit=0.95[aout]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        "-ar", "44100",
        output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Audio mix error: {result.stderr[-300:]}", file=sys.stderr)
        # Fallback: just use voiceover + music
        print("  Falling back to voiceover + music only...")
        cmd_simple = [
            FFMPEG, "-y",
            "-i", voiceover, "-i", music,
            "-filter_complex",
            f"[0:a]aresample=44100,volume=1.3[vo];"
            f"[1:a]volume=0.12[bg];"
            f"[vo][bg]amix=inputs=2:duration=first,alimiter=limit=0.95[aout]",
            "-map", "[aout]", "-c:a", "pcm_s16le", "-ar", "44100", output
        ]
        subprocess.run(cmd_simple, capture_output=True, text=True)

    print(f"  Mixed audio: {output} ({get_duration(output):.1f}s, {sfx_count} SFX)")


def combine_video_audio(video, audio, output):
    """Combine video and audio into final MP4."""
    print("=== Final Assembly ===")

    cmd = [
        FFMPEG, "-y",
        "-i", video,
        "-i", audio,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error: {result.stderr[-200:]}", file=sys.stderr)
        sys.exit(1)

    dur = get_duration(output)
    size_mb = os.path.getsize(output) / (1024 * 1024)
    print(f"  Output: {output}")
    print(f"  Duration: {dur:.1f}s | Size: {size_mb:.1f}MB")
    print(f"  Format: 1080x1920 H.264 + AAC 192kbps")


def main():
    parser = argparse.ArgumentParser(
        description='Assemble final video from clips, voiceover, music, and SFX'
    )
    parser.add_argument('--video-dir', required=True,
                       help='Directory with normalized video clips')
    parser.add_argument('--voiceover', required=True,
                       help='Path to full voiceover WAV')
    parser.add_argument('--music', default=None,
                       help='Path to background music WAV')
    parser.add_argument('--sfx-dir', default=None,
                       help='Directory containing SFX WAV files')
    parser.add_argument('--scene-map', required=True,
                       help='Path to scene-map.json')
    parser.add_argument('--output', required=True,
                       help='Output MP4 file path')
    parser.add_argument('--transition-duration', type=float, default=0.3,
                       help='Crossfade duration in seconds (default: 0.3)')

    args = parser.parse_args()
    find_ffmpeg()

    global TRANSITION_DURATION
    TRANSITION_DURATION = args.transition_duration

    # Load scene map
    with open(args.scene_map, 'r') as f:
        scene_data = json.load(f)

    scenes = scene_data.get('scenes', [])

    # Collect normalized clips in order
    clips = []
    for scene in scenes:
        scene_id = scene.get('id', len(clips) + 1)
        clip_path = os.path.join(args.video_dir, f"norm-scene{scene_id}.mp4")
        if os.path.exists(clip_path):
            clips.append(clip_path)
        else:
            print(f"Warning: Missing normalized clip: {clip_path}", file=sys.stderr)

    if not clips:
        print("Error: No normalized clips found.", file=sys.stderr)
        sys.exit(1)

    # Create temp directory for intermediate files
    output_dir = os.path.dirname(args.output) or '.'
    tmp_dir = os.path.join(output_dir, 'tmp-assembly')
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        # Step 1: Merge video clips
        merged_video = xfade_merge(clips, tmp_dir, TRANSITION_DURATION)

        # Step 2: Mix audio
        total_duration = get_duration(merged_video)
        mixed_audio = os.path.join(tmp_dir, "mixed-audio.wav")

        sfx_dir = args.sfx_dir or os.path.dirname(args.music or '')

        mix_audio(
            args.voiceover, args.music, sfx_dir,
            scene_data, mixed_audio, total_duration
        )

        # Step 3: Combine video + audio
        combine_video_audio(merged_video, mixed_audio, args.output)

    finally:
        # Cleanup temp files
        import shutil
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

    print("\n=== Video assembly complete! ===")


if __name__ == '__main__':
    main()
