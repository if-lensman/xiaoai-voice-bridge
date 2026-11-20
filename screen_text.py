"""Two bounded dialogue turns; round boundaries come from user speech, not response.created."""
from collections import deque
import secrets


class ScreenText:
    def __init__(self, greeting='你好，我是豆包。请说吧。'):
        self.session = secrets.token_hex(8)  # Display identity, not an authentication token.
        self.previous = None
        self.turn_id = 0
        self._retired_responses = deque(maxlen=128)
        self._retired_inputs = deque(maxlen=128)
        self._events = deque(maxlen=128)
        self._new_turn()
        self.current['assistant'] = greeting

    @property
    def user(self): return self.current['user']

    @property
    def assistant(self): return self.current['assistant']

    @staticmethod
    def response_key(event):
        response = event.get('response')
        value = event.get('response_id') or (response.get('id') if isinstance(response, dict) else None)
        if value: return 'response:' + str(value)
        if event.get('item_id'): return 'item:' + str(event['item_id'])
        return None

    def response_allowed(self, event):
        if self._awaiting_user: return False
        key = self.response_key(event)
        if key and key in self._retired_responses: return False
        return not event.get('item_id') or 'item:' + str(event['item_id']) not in self._retired_responses

    def _new_turn(self):
        self.turn_id += 1
        self.current = {'id': self.turn_id, 'user': '', 'assistant': '', 'status': 'listening'}
        self._response_keys = set()
        self._input_id = None
        self._asr_open = False
        self._text_open = False
        self._text_mode = None
        self._text_final = False
        self._awaiting_user = False

    @staticmethod
    def _short(text, limit, tail=False):
        text = ' '.join(text.split())
        if len(text) <= limit: return text
        return '…' + text[-limit:] if tail else text[:limit] + '…'

    def _archive(self, status=None):
        if self.user:
            self.previous = dict(self.current)
            self.previous['status'] = status or self.current['status']
            self.previous['user'] = self._short(self.user, 100)
            self.previous['assistant'] = self._short(self.assistant, 180, tail=True)
        self._retired_responses.extend(self._response_keys)
        if self._input_id: self._retired_inputs.append(self._input_id)

    def _start_user(self, item_id):
        if self._asr_open:
            if not item_id or not self._input_id or item_id == self._input_id:
                if item_id: self._input_id = item_id
                return
        if self.user:
            self._archive('complete' if self.current['status'] == 'complete' else 'interrupted')
            self._new_turn()
        else:
            # Do not put a synthetic greeting into the previous-question summary.
            self._retired_responses.extend(self._response_keys)
            self._response_keys.clear()
            self.current['assistant'] = ''
            self._text_open = False
            self._text_mode = None
            self._text_final = False
        self._awaiting_user = False
        self._asr_open = True
        self._input_id = item_id
        self.current['status'] = 'listening'

    def interrupt(self):
        if self._awaiting_user: return False
        self._archive('interrupted')
        self._new_turn()
        self._awaiting_user = True
        return True

    def complete(self):
        if not self._awaiting_user:
            self.current['status'] = 'complete'

    def event(self, event):
        kind = event.get('type', '')
        event_id = event.get('event_id')
        if event_id:
            if event_id in self._events: return False
            self._events.append(event_id)
        if 'input_audio_transcription.' in kind:
            item_id = event.get('item_id')
            if item_id and item_id in self._retired_inputs: return False
            if kind.endswith('.started'):
                self._start_user(item_id)
                return True
            if kind.endswith(('.delta', '.completed')):
                value = event.get('delta', '') if kind.endswith('.delta') else event.get('transcript', event.get('text'))
                if not isinstance(value, str) or not value: return False
                if not self._asr_open:
                    if item_id and item_id == self._input_id:
                        if kind.endswith('.delta'): return False
                        self.current['user'] = value[:1200]
                        return True
                    # Some servers only send a final ASR event. Ignore repeated finals.
                    if kind.endswith('.completed') and value == self.user and (not item_id or item_id == self._input_id): return False
                    self._start_user(item_id)
                self.current['user'] = value[:1200]
                if kind.endswith('.completed'):
                    self._asr_open = False
                    self.current['status'] = 'thinking'
                return True
            return False
        if not kind.startswith('response.') or not self.response_allowed(event): return False
        key = self.response_key(event)
        if key: self._response_keys.add(key)
        if event.get('item_id'): self._response_keys.add('item:' + str(event['item_id']))
        if kind == 'response.created':
            if self._text_final: return False
            # This event may be absent or duplicated. It is not a round boundary.
            self.current['status'] = 'responding'
            return True
        if kind == 'response.output_text.delta':
            if self._text_final: return False
            piece = event.get('delta', '')
            if not isinstance(piece, str) or not piece: return False
            if not self._text_open:
                self.current['assistant'] = piece[:4000]
                self._text_open = True
            elif self._text_mode == 'snapshot':
                self.current['assistant'] = piece[:4000]
            elif len(piece) > len(self.assistant) and piece.startswith(self.assistant):
                # Accommodate cumulative hypotheses without breaking ordinary deltas.
                self._text_mode = 'snapshot'
                self.current['assistant'] = piece[:4000]
            else:
                self.current['assistant'] = (self.assistant + piece)[:4000]
            self.current['status'] = 'responding'
            return True
        if kind == 'response.output_text.done':
            value = event.get('text')
            if isinstance(value, str) and value:
                self.current['assistant'] = value[:4000]
                self._text_open = True
            self.complete()
            self._text_final = True
            return True
        if kind == 'response.done':
            self.complete()
        return False

    def snapshot(self, state):
        return {'type': 'ui', 'state': state, 'session': self.session,
                'current': dict(self.current), 'previous': dict(self.previous) if self.previous else None,
                # Keep the old terminal compatible during the rolling update.
                'user': self.user, 'assistant': self.assistant}
