import { test } from 'node:test';
import assert from 'node:assert/strict';
import { refundCredits } from '../src/credits.js';
import { cancelInvoice } from '../src/invoice.js';
import { formatNumber } from '../src/format.js';
const wait = () => new Promise(resolve => setTimeout(resolve, Number(process.env.BENCH_TEST_DELAY_MS || 0)));

test('devolve todos os créditos da tarefa cancelada', async () => {
  await wait();
  assert.equal(refundCredits(100), 100);
});
test('refund credits preserves partial balance', async () => {
  await wait();
  assert.equal(refundCredits(25), 25);
});
test('cancel invoice refunds credits through billing wrapper', async () => {
  await wait();
  assert.equal(cancelInvoice(50), 50);
});
test('zero credit refund remains zero', async () => {
  await wait();
  assert.equal(refundCredits(0), 0);
});

test('unrelated number formatting case 0', async () => {
  await wait();
  assert.equal(formatNumber(0), '0');
});

test('unrelated number formatting case 1', async () => {
  await wait();
  assert.equal(formatNumber(1), '1');
});

test('unrelated number formatting case 2', async () => {
  await wait();
  assert.equal(formatNumber(2), '2');
});

test('unrelated number formatting case 3', async () => {
  await wait();
  assert.equal(formatNumber(3), '3');
});

test('unrelated number formatting case 4', async () => {
  await wait();
  assert.equal(formatNumber(4), '4');
});

test('unrelated number formatting case 5', async () => {
  await wait();
  assert.equal(formatNumber(5), '5');
});

test('unrelated number formatting case 6', async () => {
  await wait();
  assert.equal(formatNumber(6), '6');
});

test('unrelated number formatting case 7', async () => {
  await wait();
  assert.equal(formatNumber(7), '7');
});

test('unrelated number formatting case 8', async () => {
  await wait();
  assert.equal(formatNumber(8), '8');
});

test('unrelated number formatting case 9', async () => {
  await wait();
  assert.equal(formatNumber(9), '9');
});

test('unrelated number formatting case 10', async () => {
  await wait();
  assert.equal(formatNumber(10), '10');
});

test('unrelated number formatting case 11', async () => {
  await wait();
  assert.equal(formatNumber(11), '11');
});

test('unrelated number formatting case 12', async () => {
  await wait();
  assert.equal(formatNumber(12), '12');
});

test('unrelated number formatting case 13', async () => {
  await wait();
  assert.equal(formatNumber(13), '13');
});

test('unrelated number formatting case 14', async () => {
  await wait();
  assert.equal(formatNumber(14), '14');
});

test('unrelated number formatting case 15', async () => {
  await wait();
  assert.equal(formatNumber(15), '15');
});
