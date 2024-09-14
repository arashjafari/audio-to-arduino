from pydub import AudioSegment
import librosa
import numpy as np

def convert_mp3_to_wav(mp3_file, wav_file):
    audio = AudioSegment.from_file(mp3_file, format='mp3')
    audio.export(wav_file, format='wav')

def extract_pitches(wav_file):
    # Load the audio as a waveform `y`
    # Store the sampling rate as `sr`
    y, sr = librosa.load(wav_file)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C7'),
        sr=sr,
        frame_length=2048,
        hop_length=256
    )
    times = librosa.times_like(f0, sr=sr, hop_length=256)
    # Filter out unvoiced frames
    pitches = f0[~np.isnan(f0)]
    times = times[~np.isnan(f0)]
    return pitches, times

def frequency_to_midi_note(frequency):
    return int(round(librosa.hz_to_midi(frequency)))

def midi_note_to_arduino_constant(midi_note):
    note_names = ['C', 'CS', 'D', 'DS', 'E', 'F', 'FS', 'G', 'GS', 'A', 'AS', 'B']
    octave = (midi_note // 12) - 1
    note_index = midi_note % 12
    note_name = note_names[note_index]
    return f'NOTE_{note_name}{octave}'

def calculate_durations(times):
    return np.diff(times, prepend=times[0])

def quantize_durations(durations, tempo):
    beat_duration = 60 / tempo  # Duration of a beat in seconds
    quantized_durations = []
    for duration in durations:
        beats = duration / beat_duration
        if beats >= 1.5:
            quantized_duration = 1  # Whole note
        elif beats >= 1.0:
            quantized_duration = 2  # Half note
        elif beats >= 0.5:
            quantized_duration = 4  # Quarter note
        elif beats >= 0.25:
            quantized_duration = 8  # Eighth note
        else:
            quantized_duration = 16  # Sixteenth note
        quantized_durations.append(quantized_duration)
    return quantized_durations

def generate_arduino_arrays(melody, durations):
    melody_constants = [midi_note_to_arduino_constant(note) for note in melody]
    melody_array = ', '.join(melody_constants)
    durations_array = ', '.join(str(int(d)) for d in durations)

    print('int melody[] = {')
    print(f'  {melody_array}')
    print('};\n')

    print('int durations[] = {')
    print(f'  {durations_array}')
    print('};')

def main():
    mp3_file = 'input.mp3'
    wav_file = 'output.wav'
    convert_mp3_to_wav(mp3_file, wav_file)
    pitches, times = extract_pitches(wav_file)

    midi_notes = [frequency_to_midi_note(freq) for freq in pitches]
    durations = calculate_durations(times)
    quantized_durations = quantize_durations(durations, 120)

    generate_arduino_arrays(midi_notes, quantized_durations)


if __name__ == '__main__':
    main()
