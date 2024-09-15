from pydub import AudioSegment
import librosa
import numpy as np
import os
import sys
import tempfile

def convert_mp3_to_wav(mp3_file, wav_file):
    try:
        audio = AudioSegment.from_file(mp3_file, format='mp3')
        audio.export(wav_file, format='wav')
    except Exception as e:
        print(f"Error converting MP3 to WAV: {e}")
        sys.exit(1)

def extract_pitches(wav_file):
    # Load the audio as a waveform `y`
    # Store the sampling rate as `sr`
    y, sr = librosa.load(wav_file, sr=None) # Preserve original sampling rate
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr,
            frame_length=2048,
            hop_length=256
        )
    except Exception as e:
        print(f"Error extracting pitches: {e}")
        sys.exit(1)
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
    if len(times) > 1:
        last_duration = times[-1] - times[-2]
    else:
        last_duration = times[0]
    durations = np.append(np.diff(times), last_duration)
    return durations

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

def group_notes(midi_notes, durations):
    grouped_melody = []
    grouped_durations = []
    current_note = midi_notes[0]
    current_duration = durations[0]

    for note, duration in zip(midi_notes[1:], durations[1:]):
        if note == current_note:
            current_duration += duration
        else:
            grouped_melody.append(current_note)
            grouped_durations.append(current_duration)
            current_note = note
            current_duration = duration

    # Append the last note
    grouped_melody.append(current_note)
    grouped_durations.append(current_duration)

    return grouped_melody, grouped_durations

def cleanup(temp_file):
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except Exception as e:
            print(f"Error deleting temporary file: {e}")

def limit_array_size(melody, durations, max_size, method='truncate'):
    if max_size == None:
        return melody, durations

    if len(melody) <= max_size:
        return melody, durations

    if method == 'truncate':
        # Truncate the arrays to the maximum size
        return melody[:max_size], durations[:max_size]
    elif method == 'downsample':
        # Downsample the arrays to fit within the maximum size
        factor = len(melody) / max_size
        indices = [int(i * factor) for i in range(max_size)]
        limited_melody = [melody[int(i)] for i in indices]
        limited_durations = [durations[int(i)] for i in indices]
        return limited_melody, limited_durations
    else:
        raise ValueError("Invalid method for limiting array size.")

def process_mp3_file(file_path, tempo, max_size, method):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav_file:
        wav_file = temp_wav_file.name
    convert_mp3_to_wav(file_path, wav_file)
    pitches, times = extract_pitches(wav_file)
    cleanup(wav_file)

    if len(pitches) == 0:
        print("No pitches detected!")
        return

    midi_notes = [frequency_to_midi_note(freq) for freq in pitches]
    durations = calculate_durations(times)
    grouped_melody, grouped_durations = group_notes(midi_notes, durations)
    quantized_durations = quantize_durations(grouped_durations, tempo)

    limited_melody, limited_durations = limit_array_size(
        grouped_melody, quantized_durations, max_size, method
    )

    generate_arduino_arrays(limited_melody, limited_durations)

def get_file_extension(file_path):
    return os.path.splitext(file_path)[1].lower()

def main():
    if len(sys.argv) < 2:
        print("Usage: python audio_to_arduino.py <input_file> [options]")
        print("Options:")
        print("  --tempo <tempo>                 Set the tempo (default: 120 BPM)")
        print("  --max-size <max_size>           Maximum number of notes in the output")
        print("  --method <truncate|downsample>  Method to limit array size (default: truncate)")
        return

    input_file = sys.argv[1]
    tempo = 120 # Default tempo
    max_size = None  # No limit by default
    method = 'truncate'  # Default method
    
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--tempo':
            i += 1
            tempo = float(args[i])
        elif args[i] == '--max-size':
            i += 1
            max_size = int(args[i])
        elif args[i] == '--method':
            i += 1
            method = args[i]
        i += 1

    file_extension = get_file_extension(input_file)
    if file_extension == '.mp3':
        process_mp3_file(input_file, tempo, max_size, method)
    else:
        print("Unsupported file type. Please provide an MP3 file!")

if __name__ == '__main__':
    main()
