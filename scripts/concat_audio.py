#!/usr/bin/env python3
"""Concatenate multiple WAV files with configurable silence gaps between them."""

import argparse
import struct
import wave
import sys
import os


def get_wav_duration(path):
    """Get duration of a WAV file in seconds."""
    with wave.open(path, 'rb') as w:
        return w.getnframes() / w.getframerate()


def concat_wavs(files, output, silence=0.4):
    """Concatenate WAV files with silence gaps between them.

    Args:
        files: List of WAV file paths to concatenate
        output: Output WAV file path
        silence: Silence duration in seconds between files
    """
    if not files:
        print("Error: No input files provided.", file=sys.stderr)
        sys.exit(1)

    # Read params from first file
    with wave.open(files[0], 'rb') as w:
        params = w.getparams()
        sample_rate = w.getframerate()
        channels = w.getnchannels()
        sampwidth = w.getsampwidth()

    # Generate silence frames
    silence_samples = int(sample_rate * silence)
    silence_data = struct.pack(
        '<' + ('h' * silence_samples * channels),
        *([0] * silence_samples * channels)
    )

    # Concatenate all files
    with wave.open(output, 'wb') as out:
        out.setparams(params)

        for i, filepath in enumerate(files):
            if not os.path.exists(filepath):
                print(f"Warning: Skipping missing file: {filepath}", file=sys.stderr)
                continue

            with wave.open(filepath, 'rb') as w:
                # Verify compatible format
                if w.getframerate() != sample_rate or w.getnchannels() != channels:
                    print(f"Warning: {filepath} has different format "
                          f"(sr={w.getframerate()}, ch={w.getnchannels()}), "
                          f"expected (sr={sample_rate}, ch={channels}). Skipping.",
                          file=sys.stderr)
                    continue
                out.writeframes(w.readframes(w.getnframes()))

            # Add silence between files (not after the last one)
            if i < len(files) - 1:
                out.writeframes(silence_data)

    total_duration = get_wav_duration(output)
    print(f"Output: {output} ({total_duration:.1f}s)")

    # Print per-file durations for scene mapping
    cumulative = 0.0
    for i, filepath in enumerate(files):
        if os.path.exists(filepath):
            dur = get_wav_duration(filepath)
            print(f"  Scene {i+1}: {os.path.basename(filepath)} "
                  f"({dur:.1f}s, starts at {cumulative:.1f}s)")
            cumulative += dur + (silence if i < len(files) - 1 else 0)


def main():
    parser = argparse.ArgumentParser(
        description='Concatenate WAV files with silence gaps'
    )
    parser.add_argument(
        'files', nargs='+',
        help='WAV files to concatenate (in order)'
    )
    parser.add_argument(
        '--silence', type=float, default=0.4,
        help='Silence duration between files in seconds (default: 0.4)'
    )
    parser.add_argument(
        '--output', '-o', required=True,
        help='Output WAV file path'
    )

    args = parser.parse_args()

    # Validate inputs exist
    missing = [f for f in args.files if not os.path.exists(f)]
    if missing:
        print(f"Warning: Missing files: {missing}", file=sys.stderr)

    existing = [f for f in args.files if os.path.exists(f)]
    if not existing:
        print("Error: No valid input files found.", file=sys.stderr)
        sys.exit(1)

    concat_wavs(existing, args.output, args.silence)


if __name__ == '__main__':
    main()
