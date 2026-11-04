/** Deterministic SVG rendering with the exact same WASM bytes on every platform. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { Resvg, initWasm } from '@resvg/resvg-wasm';

const here = path.dirname(fileURLToPath(import.meta.url));
const assets = path.resolve(here, '../../src/web/assets');
const check = process.argv.includes('--check');
const sizes = [16, 24, 32, 48, 64, 128, 256, 512];
assert.equal(process.versions.node, '24.22.2', 'Use the pinned Node.js version for reproducible icon builds');
const digest = data => createHash('sha256').update(data).digest('hex');
const canonicalText = data => Buffer.from(data.toString('utf8').replace(/\r\n/g, '\n'));
const wasm = await readFile(path.join(here, 'node_modules/@resvg/resvg-wasm/index_bg.wasm'));
await initWasm(wasm);

async function emit(name, bytes) {
  if (check) {
    const actual = await readFile(path.join(assets, name));
    assert.deepEqual(name.endsWith('.json') ? canonicalText(actual) : actual, bytes, `${name} must be regenerated`);
  } else {
    await writeFile(path.join(assets, name), bytes);
  }
}

function ico(images) {
  const header = Buffer.alloc(6 + images.length * 16);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(images.length, 4);
  let offset = header.length;
  images.forEach(({ size, png }, i) => {
    const pos = 6 + i * 16;
    header[pos] = size === 256 ? 0 : size;
    header[pos + 1] = header[pos];
    header.writeUInt16LE(1, pos + 4);
    header.writeUInt16LE(32, pos + 6);
    header.writeUInt32LE(png.length, pos + 8);
    header.writeUInt32LE(offset, pos + 12);
    offset += png.length;
  });
  return Buffer.concat([header, ...images.map(image => image.png)]);
}

const sourceHashes = {};
const fileHashes = {};
for (const base of ['icon', 'symbol']) {
  const source = await readFile(path.join(assets, `${base}.svg`));
  const svg = source.toString('utf8');
  // The supplied geometric identity is standalone: no fonts, remote/local files or scripts.
  assert(!/<(?:text|image|script|foreignObject)\b|\b(?:href|xlink:href)\s*=|<!ENTITY|<!DOCTYPE/i.test(svg));
  sourceHashes[`${base}.svg`] = digest(canonicalText(source));
  const rendered = [];
  for (const size of (base === 'icon' ? sizes : [512])) {
    const renderer = new Resvg(svg, { fitTo: { mode: 'width', value: size }, font: { loadSystemFonts: false } });
    const image = renderer.render();
    const png = Buffer.from(image.asPng());
    assert.equal(image.width, size);
    assert.equal(image.height, size);
    const name = `${base}-${size}.png`;
    await emit(name, png);
    fileHashes[name] = digest(png);
    rendered.push({ size, png });
    image.free();
    renderer.free();
  }
  if (base === 'icon') {
    const bytes = ico(rendered.filter(image => image.size <= 256));
    await emit('icon.ico', bytes);
    fileHashes['icon.ico'] = digest(bytes);
  }
}
const manifest = {
  schema: 1,
  renderer: '@resvg/resvg-wasm@2.6.2',
  node: '24.22.2',
  source_hash_format: 'UTF-8 with LF line endings',
  wasm_sha256: digest(wasm),
  generator_sha256: digest(canonicalText(await readFile(fileURLToPath(import.meta.url)))),
  package_lock_sha256: digest(canonicalText(await readFile(path.join(here, 'package-lock.json')))),
  sources: sourceHashes,
  outputs: fileHashes,
};
await emit('icons-manifest.json', Buffer.from(JSON.stringify(manifest, null, 2) + '\n'));
console.log(`${check ? 'Verified' : 'Generated'} ${Object.keys(fileHashes).length} deterministic PNG/ICO files from the supplied SVGs`);
