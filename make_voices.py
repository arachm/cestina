"""Make every recording of the app with Microsoft Azure neural voices.

Runs on GitHub (Actions), never on the phone. The Azure key comes from the repository
secrets and is never printed. Free tier (F0): 500,000 characters a month; the whole app
is about 42,000 characters. The free tier allows 20 recordings a minute, so the script
paces itself (about 2 hours for everything). 16 kHz / 32 kbps keeps the zip small
enough to send in the chat (about 25 MB).

texts.json:  { "L1-0": ["Dobrý den!", "m"], ... }   m = Antonín (man), f = Vlasta (woman)
             an optional third value sets the speed, e.g. "+0%" for natural-speed listening
"""
import json, os, sys, time, urllib.request, urllib.error
from xml.sax.saxutils import escape

KEY, REGION = os.environ.get('KEY', '').strip(), os.environ.get('REGION', '').strip()
if not KEY or not REGION:
    sys.exit('Missing secrets: add AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in Settings → Secrets and variables → Actions.')
src, out = sys.argv[1], sys.argv[2]
limit = sys.argv[3] if len(sys.argv) > 3 else 'all'
VOICE = {'m': 'cs-CZ-AntoninNeural', 'f': 'cs-CZ-VlastaNeural'}
RATE = os.environ.get('RATE', '-5%')          # a little slower than normal speech, good for learners
FORMAT = os.environ.get('FORMAT', 'audio-16khz-32kbitrate-mono-mp3')
PAUSE = float(os.environ.get('PAUSE', '3.1'))  # seconds per recording: stays under 20 a minute
URL = f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1'
os.makedirs(out, exist_ok=True)
texts = json.load(open(src, encoding='utf-8'))
items = list(texts.items())
if limit != 'all': items = items[:int(limit)]

def speak(text, v, rate=None):
    ssml = (f"<speak version='1.0' xml:lang='cs-CZ'><voice name='{VOICE[v]}'>"
            f"<prosody rate='{rate or RATE}'>{escape(text)}</prosody></voice></speak>").encode('utf-8')
    req = urllib.request.Request(URL, data=ssml, method='POST', headers={
        'Ocp-Apim-Subscription-Key': KEY, 'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': FORMAT, 'User-Agent': 'cestina-obrazem'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

done = failed = 0
for n, (i, entry) in enumerate(items, 1):
    t0 = time.time()
    text, v = entry[0], entry[1]; rate = entry[2] if len(entry) > 2 else None
    for attempt in range(8):
        try:
            data = speak(text, v, rate)
            if len(data) < 500: raise ValueError('audio too short')
            open(os.path.join(out, i + '.mp3'), 'wb').write(data); done += 1
            break
        except urllib.error.HTTPError as e:
            if e.code == 401: sys.exit('Azure says the key or region is wrong (401). Check the two secrets.')
            wait = int(e.headers.get('Retry-After') or 0) or min(60, 5 * (attempt + 1))
            print(f'  {i}: HTTP {e.code}, waiting {wait} s'); time.sleep(wait)
        except Exception as e:
            print(f'  {i}: {type(e).__name__}, retrying'); time.sleep(5 * (attempt + 1))
    else:
        failed += 1; print(f'FAILED {i}: {text}')
    if n % 50 == 0: print(f'{n} / {len(items)} done', flush=True)
    time.sleep(max(0.0, PAUSE - (time.time() - t0)))
print(f'Finished: {done} recordings, {failed} failed.')
if failed > len(items) * 0.05: sys.exit('Too many failures.')
