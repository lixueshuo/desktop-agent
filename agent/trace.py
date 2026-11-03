"""Local event records; excluded from Git because tool output may be private."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


class Trace:
    def __init__(self, directory, secrets=()):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:12] + '.jsonl')
        self._secrets = tuple(s for s in secrets if s)
        self._file = self.path.open('x', encoding='utf-8')

    def add(self, event):
        record = {'time': datetime.now(timezone.utc).isoformat(), 'event': event}
        text = json.dumps(record, ensure_ascii=False)
        # Redact known keys in serialized form as well as literal form.
        for secret in self._secrets:
            text = text.replace(json.dumps(secret, ensure_ascii=False)[1:-1], '[REDACTED]')
        self._file.write(text + '\n')
        self._file.flush()

    def close(self):
        self._file.close()
