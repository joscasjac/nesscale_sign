import test from 'node:test';
import assert from 'node:assert/strict';
import { api, upload, downloadUrl, date } from '../src/api.js';

test('API includes session credentials and CSRF protection', async (t) => {
  globalThis.window = { csrf_token: 'local-csrf' };
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    assert.equal(init.credentials, 'same-origin');
    assert.equal(init.headers['X-Frappe-CSRF-Token'], 'local-csrf');
    assert.equal(init.method, 'POST');
    return { ok: true, json: async () => ({ message: { name: 'doc' } }) };
  });
  assert.deepEqual(await api('envelope.get_envelope', { name: 'doc' }), { name: 'doc' });
});
test('server validation errors produce readable messages', async (t) => {
  globalThis.window = {};
  t.mock.method(globalThis, 'fetch', async () => ({ ok: false, json: async () => ({ _server_messages: JSON.stringify([JSON.stringify({ message: '<b>Consent</b> is required' })]) }) }));
  await assert.rejects(api('signing.submit'), /Consent is required/);
});
test('non-JSON failures are recoverable and oversized files never upload', async (t) => {
  globalThis.window = {};
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async () => { calls++; return { json: async () => { throw new Error('invalid JSON'); } }; });
  await assert.rejects(api('envelope.list_envelopes'), /Please try again/);
  await assert.rejects(upload({ size: 16 * 1024 * 1024 }), /15 MB/);
  assert.equal(calls, 1);
});
test('download tokens are encoded and missing dates stay readable', () => {
  assert.match(downloadUrl('signing.get_pdf', { token: 'a&b' }), /token=a%26b$/);
  assert.equal(date(undefined), '—');
  assert.equal(date('invalid'), '—');
});

test('calendar dates do not shift to the previous day', () => {
  assert.equal(date('2026-09-09'), 'Sep 9, 2026');
});
