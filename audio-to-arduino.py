from pydub import AudioSegment

def convert_mp3_to_wav(mp3_file, wav_file):
    audio = AudioSegment.from_file(mp3_file, format='mp3')
    audio.export(wav_file, format='wav')

def main():
    mp3_file = 'input.mp3'
    wav_file = 'output.wav'
    convert_mp3_to_wav(mp3_file, wav_file)

if __name__ == '__main__':
    main()
