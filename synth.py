# Max Janisse (c) 2026
# <mjanisse@pdx.edu>
import numpy as np
import sounddevice as sd
import mido
import argparse
import threading
from enum import Enum

DEFAULT_VOICE = "sawtooth"
SAMPLE_RATE = 48000
BLOCKSIZE = 512

def midi_to_freq(midi): return 440 * (2 ** ((midi - 69) / 12))

def generate_sine(frequency, sample_count, phase, sample_rate):
    if frequency == 0.0:
        return np.zeros(sample_count, dtype=np.float32)

    phase_increment = frequency / sample_rate
    phases = (phase + np.arange(sample_count) * phase_increment) % 1.0
    new_phase = (phase + sample_count * phase_increment) % 1.0

    wave = np.sin(2.0 * np.pi * phases)

    return wave, new_phase

def generate_triangle(frequency, sample_count, phase, sample_rate):
    if frequency == 0.0:
        return np.zeros(sample_count, dtype=np.float32)

    phase_increment = frequency / sample_rate
    phases = (phase + np.arange(sample_count) * phase_increment) % 1.0
    new_phase = (phase + sample_count * phase_increment) % 1.0

    wave = 1.0 - 4.0 * np.abs(phases - 0.5)

    return wave, new_phase

def generate_square(frequency, sample_count, phase, sample_rate):
    if frequency == 0.0:
        return np.zeros(sample_count, dtype=np.float32)
    
    phase_increment = frequency / sample_rate
    phases = (phase + np.arange(sample_count) * phase_increment) % 1.0
    new_phase = (phase + sample_count * phase_increment) % 1.0
    
    wave = np.where(phases < 0.5, 1.0, -1.0)
    
    return wave, new_phase

def generate_sawtooth(frequency, sample_count, phase, sample_rate, harmonics=50):
    t = (np.arange(sample_count) / sample_rate) + phase / (2 * np.pi * frequency)

    wave = np.zeros(sample_count, dtype=np.float32)
    for k in range(1, harmonics + 1):
        wave += ((-1)**(k+1)) * (np.sin(2 * np.pi * k * frequency * t) / k)
    wave *= (2 / np.pi)

    new_phase = (2 * np.pi * frequency * sample_count / sample_rate + phase) % (2 * np.pi)

    return wave, new_phase

class Note:
    def __init__(self, midi, voice, envelope, sample_rate):
        self.freq = midi_to_freq(midi.note)
        self.velocity = midi.velocity
        self.phase = 0.0
        self.sample_rate = sample_rate
        self.voice = voice
        self.envelope = envelope
        self.envelope.on(self.velocity)

    @property
    def finished(self):
        return self.envelope.finished
    
    def off(self):
        self.envelope.off()

    def render(self, sample_count):
        wave, self.phase = None, self.phase
        match self.voice:
            case "sine":     wave, self.phase = generate_sine(self.freq, sample_count, self.phase, self.sample_rate)
            case "square":   wave, self.phase = generate_square(self.freq, sample_count, self.phase, self.sample_rate)
            case "triangle": wave, self.phase = generate_triangle(self.freq, sample_count, self.phase, self.sample_rate)
            case "sawtooth": wave, self.phase = generate_sawtooth(self.freq, sample_count, self.phase, self.sample_rate)
            case _: raise ValueError(f"unable to render note in unrecognized voice: {self.voice}")
        envelope = self.envelope.render(sample_count)
        return wave * envelope

class ADSR(Enum):
    IDLE     = 0
    ATTACK   = 1
    DECAY    = 2
    SUSTAIN  = 3
    RELEASE  = 4

class Envelope:
    def __init__(self, attack, decay, sustain, release, sample_rate):
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.sample_rate = sample_rate
        self._stage = ADSR.IDLE
        self.peak = 1.0
        self.level = 0.0

    @property
    def finished(self):
        return self._stage == ADSR.IDLE
    
    def on(self, velocity):
        self.peak = velocity / 127.0
        self._stage = ADSR.ATTACK

    def off(self):
        print("envelope turning off from: ", self._stage)
        if self._stage != ADSR.IDLE:
            self._stage = ADSR.RELEASE

    def render(self, sample_count):
        result = np.empty(sample_count)

        i = 0
        while i < sample_count:
            remaining = sample_count - i
            chunk = []
            match self._stage:
                case ADSR.ATTACK:  chunk = self._attack(remaining)
                case ADSR.DECAY:   chunk = self._decay(remaining)
                case ADSR.SUSTAIN: chunk = self._sustain(remaining)
                case ADSR.RELEASE: chunk = self._release(remaining)
                case _:            chunk = self._idle(remaining)
            
            result[i:i+len(chunk)] = chunk
            i += len(chunk)

        return result

    def _idle(self, remaining): return [0.0] * remaining

    def _attack(self, remaining):
        print("attack")
        rate = self.peak / max(self.attack * self.sample_rate, 1)
        steps = min(remaining, int(np.ceil((self.peak - self.level) / rate)))
        chunk = np.linspace(self.level, self.level + rate * steps, steps, endpoint=False)

        self.level += rate * steps
        if self.level >= self.peak:
            self.level = self.peak
            self._stage = ADSR.DECAY
        return chunk

    def _decay(self, remaining):
        print("decay")
        target = self.sustain * self.peak
        rate   = (self.peak - target) / max(self.decay * self.sample_rate, 1)
        steps  = min(remaining, int(np.ceil((self.level - target) / max(rate, 1e-9))))
        chunk  = np.linspace(self.level, self.level - rate * steps, steps, endpoint=False)

        self.level -= rate * steps
        if self.level <= target:
            self.level = target
            self._stage = ADSR.SUSTAIN
        return chunk

    def _sustain(self, remaining):
        print("sustain")
        return [self.level] * remaining

    def _release(self, remaining):
        print("release")
        rate  = self.level / max(self.release * self.sample_rate, 1)
        steps = min(remaining, int(np.ceil(self.level / max(rate, 1e-9))))
        chunk = np.linspace(self.level, max(0.0, self.level - rate * steps), steps, endpoint=False)
        
        self.level = float(chunk[-1]) if len(chunk) and float(chunk[-1]) > 1e-3 else 0.0
        if self.level <= 0.0:
            self.level = 0.0
            if (remaining - len(chunk)) > 0:
                chunk[i:] = 0.0
            self._stage = ADSR.IDLE
        return chunk

class Synth:
    def __init__(self, voice, envelope, sample_rate, volume):
        self._notes = {}
        self._voice = voice
        self._envelope = envelope
        self._sample_rate = sample_rate
        self._volume = volume
        self._stream = None
        self._lock = threading.Lock()
    
    def _note_on(self, midi_msg):
        if midi_msg.velocity == 0:
            self._note_off(midi_msg)
            return
        with self._lock:
            self._notes[midi_msg.note] = Note(
                midi_msg, 
                self._voice, 
                self._envelope, 
                self._sample_rate
            )

    def _note_off(self, midi_msg):
        with self._lock:
            if midi_msg.note in self._notes:
                print("turning off", midi_msg.note)
                self._notes[midi_msg.note].off()

    def _all_off(self):
        with self._lock:
            for note in self._notes.values():
                note.off()

    def _clear(self):
        with self._lock:
            self._notes.clear()

    def handle(self, msg):
        match msg.type:
            case "note_on":  self._note_on(msg)
            case "note_off": self._note_off(msg)

        if msg.is_cc():
            if msg.control == 120 or msg.control == 123:
                self._all_off()
                self._clear()

    def start(self):
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            channels=1,
            dtype="float32",
            callback=self._callback
        )
        self._stream.start()
        print(f"Synthesizer started {SAMPLE_RATE} sample/sec, {BLOCKSIZE}")

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print(f"Synthesizer stopped")

    def _callback(self, outdata, frames, time_info, status):
        with self._lock:
            if not self._notes:
                outdata[:] = 0
                return
            mix = np.zeros(frames, dtype=np.float32)
            finished = []
            for midi, note in self._notes.items():
                mix += note.render(frames)
                if note.finished:
                    finished.append(midi)
            for midi in finished:
                print("finished", finished)
                del self._notes[midi]

        mix = np.tanh(mix * self._volume)
        outdata[:] = mix.reshape(-1, 1)

def determine_amplitude(db): return 10 ** (db / 20)

def main(args):
    envelope = Envelope(
        attack=args.attack,
        decay=args.decay,
        sustain=args.sustain,
        release=args.release,
        sample_rate=SAMPLE_RATE
    )
    synth = Synth(
        voice=args.voice,
        envelope=envelope,
        sample_rate=SAMPLE_RATE,
        volume=determine_amplitude(args.volume)
    )
    synth.start()
    with mido.open_input(name=args.name, virtual=True) as port:
        print(f"Listening on '{port.name}'....")
        for msg in port:
            print(msg)
            synth.handle(msg)
    print("Exiting...")

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
    parser.add_argument(
        "--attack", type=float, default=0.01,
        help="set the attack time of the ASDR envelope in milliseconds."
    )
    parser.add_argument(
        "--decay", type=float, default=0.015,
        help="set the decay time of the ASDR envelope in milliseconds."
    )
    parser.add_argument(
        "--sustain", type=float, default=0.7,
        help="set the sustain time of the ASDR envelope in milliseconds."
    )
    parser.add_argument(
        "--release", type=float, default=0.01,
        help="set the release time of the ASDR envelope in milliseconds."
    )
    args = parser.parse_args()

    args.voice = DEFAULT_VOICE
    
    if [args.sine, args.square, args.triangle].count(True) > 1:
        print("Only one wave type can be enabled")
        exit(1)
    elif args.sine:     args.voice = "sine"
    elif args.square:   args.voice = "square"
    elif args.triangle: args.voice = "triangle"
    
    if args.midi_devices:
        print("MIDI Output Devices:")
        for i, a in enumerate(mido.get_input_names()):
            print(f"    [{i+1}] {a}")
        exit(0)

    if args.midi_port:
        args.name = mido.get_input_names()[args.midi_port-1]

    main(args)