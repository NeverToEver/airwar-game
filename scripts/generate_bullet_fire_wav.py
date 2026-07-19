#!/usr/bin/env python3
"""Generate the shipped ``bullet_fire`` laser SFX (P3).

Recipe follows the industry-standard sfxr/Bfxr "Laser/Shoot" family:
a harmonic-rich carrier (square/saw/triangle) with a fast exponential
downward pitch sweep, near-zero attack, exponential decay, and a short
noise transient for the attack "crack". This replaces the old steady
sine beep, whose constant pitch repeated ~7x/sec caused listening
fatigue.

Outputs (44100 Hz / 16-bit / mono) into ``airwar/assets/audio/``:

- ``bullet_fire.wav``    — base variant (start 760 Hz)
- ``bullet_fire_b.wav``  — +9% start pitch
- ``bullet_fire_c.wav``  — -8% start pitch

The runtime cycles the three variants round-robin so consecutive
shots never sound identical (anti repetition-fatigue).

Usage:
    python3 scripts/generate_bullet_fire_wav.py
    python3 scripts/generate_bullet_fire_wav.py --candidates /tmp/laser_candidates

``--candidates`` additionally writes one WAV per waveform character
(square / saw / triangle) for listening comparison; those files are
NOT shipped.
"""

from __future__ import annotations

import argparse
import os
import wave

import numpy as np

SAMPLE_RATE = 44100

# Base recipe (sfxr "Laser/Shoot" style).
BASE_START_HZ = 760.0
END_HZ = 170.0
DURATION_MS = 90
NOISE_MS = 5.0
NOISE_GAIN = 0.25
PEAK = 0.5  # normalize to -6 dBFS so overlapping shots do not clip

# Shipped variants: start-pitch multipliers for round-robin playback.
VARIANTS = {
    "bullet_fire.wav": 1.0,
    "bullet_fire_b.wav": 1.09,
    "bullet_fire_c.wav": 0.92,
}

# Audition-only characters for --candidates mode.
CANDIDATE_WAVEFORMS = ("square", "saw", "triangle")


def synth_laser_zap(
    start_hz: float,
    end_hz: float,
    duration_ms: int,
    sample_rate: int = SAMPLE_RATE,
    *,
    waveform: str = "square",
    noise_ms: float = NOISE_MS,
    noise_gain: float = NOISE_GAIN,
    peak: float = PEAK,
) -> np.ndarray:
    """Synthesize an sfxr-style laser zap as int16 PCM (mono).

    Pitch sweeps exponentially from ``start_hz`` to ``end_hz`` over the
    whole duration; the envelope is a 2ms attack followed by an
    exponential decay; a short white-noise burst adds the attack crack.
    """
    n = int(sample_rate * duration_ms / 1000)
    t = np.arange(n, dtype=np.float64) / sample_rate
    total = n / sample_rate

    # Exponential sweep: f(t) = f0 * ratio**(t/T); phase is its integral.
    ratio = end_hz / start_hz
    phase = 2.0 * np.pi * start_hz * total / np.log(ratio) * (np.power(ratio, t / total) - 1.0)
    cycles = phase / (2.0 * np.pi)

    if waveform == "square":
        wave_out = np.where(cycles % 1.0 < 0.5, 1.0, -1.0)
    elif waveform == "saw":
        wave_out = 2.0 * (cycles % 1.0) - 1.0
    elif waveform == "triangle":
        frac = cycles % 1.0
        wave_out = 4.0 * np.abs(frac - 0.5) - 1.0
    else:
        raise ValueError(f"unknown waveform: {waveform}")

    # Envelope: 2ms linear attack, exponential decay to zero.
    envelope = np.exp(-t / (total * 0.32))
    attack_n = max(1, int(sample_rate * 0.002))
    envelope[:attack_n] *= np.linspace(0.0, 1.0, attack_n)
    wave_out *= envelope

    # Noise transient for the attack crack.
    noise_n = int(sample_rate * noise_ms / 1000)
    if noise_n > 0 and noise_gain > 0:
        rng = np.random.default_rng(20260719)
        noise = rng.uniform(-1.0, 1.0, noise_n) * np.linspace(1.0, 0.0, noise_n)
        wave_out[:noise_n] += noise_gain * noise

    # Peak-normalize and convert to int16.
    max_abs = np.max(np.abs(wave_out))
    if max_abs > 0:
        wave_out = wave_out / max_abs * peak
    return (wave_out * 32767).astype(np.int16)


def write_wav(path: str, pcm: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sample_rate)
        fh.writeframes(pcm.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidates",
        metavar="DIR",
        help="also write one audition WAV per waveform character into DIR",
    )
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo_root, "airwar", "assets", "audio")

    for filename, mult in VARIANTS.items():
        pcm = synth_laser_zap(BASE_START_HZ * mult, END_HZ, DURATION_MS)
        path = os.path.join(out_dir, filename)
        write_wav(path, pcm)
        print(f"wrote {path} ({len(pcm)} samples, start {BASE_START_HZ * mult:.0f} Hz)")

    if args.candidates:
        for waveform in CANDIDATE_WAVEFORMS:
            pcm = synth_laser_zap(BASE_START_HZ, END_HZ, DURATION_MS, waveform=waveform)
            path = os.path.join(args.candidates, f"candidate_{waveform}.wav")
            write_wav(path, pcm)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
