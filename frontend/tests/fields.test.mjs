import test from 'node:test';
import assert from 'node:assert/strict';
import { repeatField, fieldTypes } from '../src/fields.js';
test('all original advertised fields are available', () => {
  for (const type of ['Signature','Initial','Name','Email','Date Signed','Text','Checkbox','Dropdown']) assert.ok(fieldTypes.includes(type));
});
test('repeat preserves recipient and geometry without duplicating existing pages', () => {
  let serial = 0;
  const f = { field_key: 'original', page: 2, signer_role: 'buyer', pos_x: .2, pos_y: .7, width: .3, height: .1 };
  const existing = [f];
  const copies = repeatField(f, 4, existing, () => 'id' + ++serial);
  assert.deepEqual(copies.map(f => f.page), [1,3,4]);
  assert.equal(copies[0].signer_role, 'buyer');
  assert.equal(copies[0].pos_x, .2);
  assert.equal(new Set([f,...copies].map(f => f.field_key)).size, 4);
  assert.deepEqual(repeatField(f, 4, [...existing,...copies]), []);
});
test('repeat refuses a layout over the server field limit', () => {
  const f = {page:1};
  assert.throws(() => repeatField(f, 3, Array.from({length:499}, () => ({page:1}))), /500/);
});

test('guided signing advances across pages and skips completed or optional fields', async () => {
  const { nextRequiredField } = await import('../src/fields.js');
  const fields = [{field_key:'later',page:2,pos_y:.1,pos_x:.1,required:1},{field_key:'optional',page:1,pos_y:0,pos_x:0,required:0},{field_key:'first',page:1,pos_y:.2,pos_x:.1,required:1}];
  assert.equal(nextRequiredField(fields, () => false).field_key, 'first');
  assert.equal(nextRequiredField(fields, f => f.field_key === 'first').field_key, 'later');
  assert.equal(nextRequiredField(fields, () => true), null);
  assert.equal(fields[0].field_key, 'later');
});
