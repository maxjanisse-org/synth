# Synth
_Created by Max Janisse_

## Description
A personal soft synthesizer that accepts MIDI key events via a selected interface, and plays software-generated audio through the system interface. 
Several types of oscillators can be used: sawtooth (default), triangle, square, and sine. 

## Usage

### Python Environment
Run the provided script to set up and/or activate a Python environment. Use the command below to execute the script; notice that it starts with a period. This allows the activation of the Python environment to update the terminal used to execute the script.
```bash
. ./env-setup.bash
```
* If the directory hasn't been initialized, then the environment will be created, activated, and the required packages will be installed. 
* If the environment is initialized, but has not been activated, that will be taken care of.
* If the environment is initialized and activated, nothing will be done
* If you would like to remove the environment, using the `-R` argument.

### Running the Program
Use the following command to execute the program using the default configuration:
```bash
python3 synth.py
```
Configuration options are available as well (can also be seen by using `python3 synth.py -h`):
```bash
usage: synth.py [-h] [-v] [-n NAME] [--volume VOLUME] [--midi-port MIDI_PORT] [--midi-devices] [--sine] [--triangle] [--square] [--attack ATTACK] [--decay DECAY] [--sustain SUSTAIN] [--release RELEASE]

Personal MIDI synthesizer using a sawtooth wave oscillator by default and implementing a configurable ADSR envelope to further shape the synthesized sound.

options:
  -h, --help            show this help message and exit
  -v, --verbose         enable more detailed output.
  -n, --name NAME       set the name of the MIDI port that will be opened
  --volume VOLUME       adjust the volume in decibels (dB). Default is -3dB.
  --midi-port MIDI_PORT
                        use this port number for connecting to the MIDI controller.
  --midi-devices        list available MIDI input devices to connect to and exit the program. Use associated number as argument to `--midi-port` to select device.
  --sine                use a sine wave oscillator.
  --triangle            use a triangle wave oscillator.
  --square              use a square wave oscillator.
  --attack ATTACK       set the attack time of the ADSR envelope.
  --decay DECAY         set the decay time of the ADSR envelope.
  --sustain SUSTAIN     set the sustain percentage of the ADSR envelope.
  --release RELEASE     set the release time of the ADSR envelope.
```
## My Story
This assignment, much like the Aleatoric one, was very much out of my wheelhouse, so I leaned pretty heavily on internet research and conversations with _Claude AI_ to get started. I started the project by copying several things from the Aleatoric project that I knew would still be useful: a MIDI-to-frequency function, my sawtooth wave generator function, the entire MIDI device selection implementation, not to mention other common project files like my setup scripts and license.

Once I actually began to work on the assignment I quickly realized that it was going to be a much more involved task. Involved enough that I decided to go with an objected oriented solution for the three main areas of the program: a note, an envelope, and the synthesizer itself. Unsure of myself, I actually had this architecture confirmed by _Claude_, just to be certain I was taking the right approach. To be fair, it recommended some features/patterns that I hadn't considered too, such as use of the `Lock()` and the `@property` decorator to define a getter-pattern (I'd never needed to do that in Python before, so I learned something new).

I already had my MIDI input reading loop from the Aleatoric assignment in place, so the entry-point to my program was set. My `Synth` class would be responsible for handling each MIDI message that was received and determining what needed to be done: trigger a `note_on` event, trigger a `note_off` event, handling both of the "clear" `control_code` message codes `120` and `123`, or ignoring it. The primary purpose of this class is to manage a collection of MIDI notes: adding or restarting notes that are turned on, and culling notes that have completed their lifecycle.

The `Envelope` class represents the Attack-Decay-Sustain-Release (ADSR) sound envelope that each note goes through as it's being synthesized. Each instance of an envelope will need to react depending on the stage of it's lifecycle it is in. As was discussed in class, the attack and decay stages reach specific points at which they are determined to be complete and the next stage of the envelope can begin. The attack-phase increases volume from the "current" level to the peak over the amount of time determined by the `--attack` argument, once reached, it transitions to the decay-phase, lowering the volume over a span of time determined by the `--decay` argument until it reaches the volume level determined by the `--sustain` argument. The sustain-phase lasts as long as the key stays "on", only transitioning to the release-phase once a key turns "off" and the volume is decreased over a span of time determined by the `--release` argument.

The `Note` class is the representation of a currently active sound to be played. It's most interesting feature is that it handles which "voice" (or oscillator) to use when generating the waveform. By default, a Sawtooth wave oscillator is used but this can be changed by using one of the arguments: `--sine`, `--square`, or `--triangle` to switch to using the respective oscillator by it's name. 

The development of this assignment was **NOT** a very smooth experience. Since I don't have a physical MIDI device to use as an input, I opted to use VMPK as my input with the full intension of using my Aleatoric program as the input to demonstrate it working (this did not end up panning out, but I'm jumping ahead...). My initial _AI-guided_ implementation of the ADSR envelope was not very successful. The major issue being that I was inconsistently getting audio out of my speakers and wasn't sure if it was due to an issue in the code, a misconfigured MIDI input, or just a sudden system issue (you know the kind of "well... crap" feeling when everything seems like a possible root cause). I ended up adding in some `print()` statements in various places to see if I could determine where the breakdown was happening. When I didn't see _any_ of them, I determined that it must be something wrong with VMPK, which I confirmed was due to the fact that restarting my program meant that I needed to go through a tedious process of changing VMPK's configuration _away_ from (the previous instance of?) my program and then _back_ once it had been restarted.

Once I figured that issue out, and I started seeing debug messages, I encountered the next issue which was that the sound being generated was _absolutely terrible_. Static-y, garbled, crunchy, noise that also seemed to have the capacity to peter out to nothing and then, without interacting with VMPK, come flooding back in a cacophony of noise. Very strange. My debug outputs did confirm one thing for me, and that was the fact that the attack-phase was never transitioning to the decay-phase, but the release-phase was being properly triggered. At the very least, I had the base requirement of an Attack-Release envelope, as required by the assignment. I added many, many more debug statements in to try and get an idea of why the math wasn't working out the way I expected it to. It turned out that what I thought to be a clever way of handling things was actually preventing the logic from ever reaching that tipping point where the peak volume was reached, thus triggering the next stage to begin in the following cycle. This same, flawed approach, was done for the decay-phase as well, just going the opposite direction, so a similar fix was made there as well. One other thing I was noticing about my debug statements was that, although I was eventually seeing the transitions from attack to decay to sustain, once it entered the release-phase I wasn't seeing my "note finished" cleanup message, which would signify that the release-phase had completed successfully, transitioning it back to it's idle-phase and allowing it to be culled from memory. This lead me to discover that the threshold for release-phase to complete was so incredibly small that it was continuing to generate frequencies that couldn't even be heard, so I adjusted the threshold such that once values were less than $0.0001$, to just go to 0 and move on. Based on my debug messages, this seemed to be timed well with, at least my, ability to hear it. I was treated to the fact that by fixing the envelope logic, the very strange behavior of the generated audio was also resolved. Notes were now fully transitioning through the ADSR envelope and stopping as expected.

At this point, I knew that, at the very least, I had successfully completed the **basic** requirements for the assignment with the extra feature of a functional ADSR envelope implemented. I could have _theoretically_ stopped here and used VMPK to demonstrate that it works and call it "good enough"... but where's the fun in that?

### Further Development Efforts
I next decided that I wanted to see how my synthesizer would handle something more intense. I went and a downloaded a couple MIDI files from [FreeMIDI.org](https://freemidi.org/): "Hotel California" by The Eagles and "Piano Man" by Billy Joel. I was looking for monophonic files but couldn't find any kind of filter for that so I just grabbed files for songs that I know and like. I piped them into my program using a MIDI player on my machine (Drumstick). The result was an absolute mess of notes starting and stopping randomly with the melody periodically _barely_ peaking through before falling back into chaos and garbled silence. I assumed that the root cause of this issue was because both MIDI files were actually _polyphonic_ and, while I thought my design supported polyphony, something wasn't right. Sadly, after a few hours of debugging, I wasn't able to plainly _see_ what my problem was, so I had decided to have a conversation with _Claude_ and get their take on my problem. Using a previous chat about this assignment for context, I asked it about how I would go about implementing polyphony in a synthesizer and it's response was something along the lines of, "make sure each note has it's own instance of ADSR envelope information." I probably re-read that a couple times before going back into the code because I knew, I already knew, that that was where I had messed up. Sure enough, I had only a single instance of `Envelope` as a member of my `Synth` class, and passed that single object reference to each and every `Note` instance that was created. After a brief and painless refactor, I now had each `Note` initializing their own instance of an `Envelope`. 

With that refactor complete, I tried playing "Piano Man" again and, this time, it was clear as a bell and full of crisp polyphony; very satisfying. Even "Hotel California" sounded pretty good (for being a MIDI rendition) and took me back to the days of ringtone, GeoCities, and early MySpace pages. I mentioned earlier that I had decided against using my Aleatoric assignment as part of my final demonstration and the reason is that, simply put, I don't think I implemented MIDI output correctly at all so, in the interest of having a _mildly_ enjoyable experience watching my video(s), I'm going to go with playing the MIDI files.

> My video submissions for this assignment are the `SYNTH.mp4` and `SYNTH-BONUS.mp4` files. They are both consecutive 5 second chunks from the Billy Joel song "Piano Man". The `SYNTH.mp4` file recorded the default settings of the program while `SYNTH-BONUS.mp4` was recorded using the `--square` argument. Both videos show the configuration options used when starting the program and can be found at the top of the terminal window.

### What's Next?
There are definitely a few improvements that could be made to this codebase. Obviously, there are a couple "extra" items that I did not implement: `--noise` and handling `control_change` MIDI events (other than the two I _do_ support). I think using an exponential equation during the different stages of the ADSR envelope would help prevent the pops-and-clicks artifacts that can sometimes happen when they are interrupted mid-transition.

During one conversation with _Claude_ it generated code for the various oscillators this synthesizer supports where there was an `Oscillator` base class with Python's equivalence of a "virtual" function allowing each derived class to implement their own custom logic on how to generate their particular waveform, allowing for `SineOscillator`, `SquareOscillator`, and so on. I feel that this would really be a code cleanup task and not particularly impactful.

