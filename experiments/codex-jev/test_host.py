"""Real Code Mode host protocol and JavaScript execution; no model or credentials."""
import argparse
import json
import os
from pathlib import Path
import queue
import signal
import struct
import subprocess
import tempfile
import threading

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path)
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix='codex-jev-host-') as tmp:
    env = {**os.environ, 'HOME': tmp, 'CODEX_HOME': tmp}
    process = subprocess.Popen([args.source / 'target/release/codex-code-mode-host'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
    messages = queue.Queue()
    nested_calls = []

    def read():
        try:
            while True:
                header = process.stdout.read(4)
                if not header:
                    break
                length = struct.unpack('<I', header)[0]
                if length > 64 * 1024 * 1024:
                    raise RuntimeError('Invalid host frame length')
                messages.put(json.loads(process.stdout.read(length)))
        except Exception as exc:
            messages.put(exc)

    threading.Thread(target=read, daemon=True).start()

    def send(message):
        payload = json.dumps(message).encode()
        process.stdin.write(struct.pack('<I', len(payload)) + payload)
        process.stdin.flush()

    def receive():
        value = messages.get(timeout=20)
        if isinstance(value, Exception):
            raise value
        return value

    def dispatch(response):
        if response.get('type') == 'delegate/request':
            request = response['request']
            assert request['type'] == 'tool/invoke'
            assert request['invocation']['tool_name']['name'] == 'pwd'
            result = subprocess.run(['pwd'], cwd=tmp, text=True, capture_output=True, check=True)
            assert result.stdout.strip() == tmp
            nested_calls.append('pwd')
            send({'type': 'delegate/response', 'id': response['id'], 'result': {'status': 'ok', 'value': {'type': 'tool/result', 'result': {'cwd': result.stdout.strip()}}}})
            return True
        return False

    def operation(identifier, request):
        send({'type': 'operation/request', 'id': identifier, 'request': request})
        for _ in range(50):
            response = receive()
            if dispatch(response):
                continue
            if response.get('type') == 'operation/response' and response.get('id') == identifier:
                result = response['result']
                if result['status'] != 'ok':
                    raise RuntimeError('Synthetic host operation failed: ' + str(result.get('message')))
                return result['value']
        raise RuntimeError('Host operation did not finish')

    try:
        send({'type': 'connection/hello', 'supportedVersions': [1], 'requiredCapabilities': [], 'optionalCapabilities': []})
        assert receive()['type'] == 'connection/ready'
        operation(1, {'method': 'session/open', 'sessionId': 'synthetic-host'})
        tool = {'name': 'pwd', 'tool_name': {'name': 'pwd', 'namespace': None}, 'description': 'Read the owned temporary cwd', 'kind': 'function', 'input_schema': {'type': 'object', 'properties': {}}, 'output_schema': None}
        execution = operation(2, {'method': 'session/execute', 'sessionId': 'synthetic-host', 'request': {'tool_call_id': 'synthetic-call', 'enabled_tools': [tool], 'source': 'text(6 * 7); text(await tools.pwd({}));', 'yield_time_ms': None, 'max_output_tokens': 100}})
        result = None
        for _ in range(50):
            response = receive()
            if dispatch(response):
                continue
            if response.get('type') == 'execute/initialResponse' and response.get('id') == 2:
                assert response['result']['status'] == 'ok'
                result = response['result']['value']
                break
        assert result is not None, 'Execution response missing'
        assert '42' in json.dumps(result), 'JavaScript output missing'
        assert 'error_text": null' in json.dumps(result), 'JavaScript execution failed'
        assert nested_calls == ['pwd'], 'Nested tool did not run exactly once'
        operation(4, {'method': 'session/shutdown', 'sessionId': 'synthetic-host'})
        print(json.dumps({'host_handshake': True, 'session_open': True, 'javascript_result': 42, 'nested_pwd': True, 'model_calls': 0}))
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
