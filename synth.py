# Max Janisse (c) 2026
# <mjanisse@pdx.edu>
import scipy.io.wavfile as wav
import numpy as np
import sounddevice as sd
import mido
import argparse
import random
from pprint import pprint

notes = ['C', 'D♭/C♯', 'D', 'E♭/D♯', 'E', 'F', 'G♭/F♯', 'G', 'A♭/G♯', 'A', 'B♭/A♯', 'B']

def midi_to_note(midi):
    note_idx = midi % 12
    octave = (midi // 12) - 1
    freq = midi_to_freq(midi)
    return (notes[note_idx], octave, freq, midi)

def midi_to_freq(midi): return 440 * (2 ** ((midi - 69) / 12))

def generate_sawtooth(f, t, harmonics=50):
    sawtooth_fourier = np.zeros_like(t)

    for k in range(1, harmonics + 1):
        sawtooth_fourier += ((-1)**(k+1)) * (np.sin(2 * np.pi * k * f * t) / k)

    sawtooth_fourier *= (2 / np.pi)
    return sawtooth_fourier

def main(args):
    with mido.open_input(name=args.name, virtual=True) as inport:
        print(f"Listening on '{inport.name}'....")
        for msg in inport:
            print(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Personal MIDI synthesizer")
    parser.add_argument(
        "--volume", type=int, default=-3,
        help="adjust the volume in decibels (dB). Default is -3dB."
    )
    parser.add_argument(
        "-n", "--name", type=str, default="MySynth",
        help="set the name of the MIDI port that will be opened"
    )
    parser.add_argument(
        "--midi-port", type=int,
        help="use this port number for connecting to the MIDI controller."
    )
    parser.add_argument(
        "--midi-devices", action="store_true",
        help="list available MIDI input devices to connect to and exit the program. Use associated number as argument to `--midi-port` to select device."
    )
    parser.add_argument(
        "--sine", action="store_true",
        help="use a sine wave during signal generation."
    )
    parser.add_argument(
        "--triangle", action="store_true",
        help="use a triangle wave during signal generation."
    )
    parser.add_argument(
        "--square", action="store_true",
        help="use a square wave during signal generation."
    )
    parser.add_argument(
        "--noise", action="store_true",
        help="add a source of white noise to the synth."
    )
    args = parser.parse_args()

    if [args.sine, args.square, args.triangle].count(True) > 1:
        print("Only one wave type can be enabled")
        exit(1)
    
    if args.midi_devices:
        print("MIDI Output Devices:")
        for i, a in enumerate(mido.get_input_names()):
            print(f"    [{i+1}] {a}")
        exit(0)

    if args.midi_port:
        args.name = mido.get_input_names()[args.midi_port-1]

    main(args)