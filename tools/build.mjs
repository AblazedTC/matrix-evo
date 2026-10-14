// Matrix Evo build: tokenizes src/*.tib into TI-84 Evo .8xp2 programs.
// Uses tivars_lib_cpp (MIT, Adrien "Adriweb" Bertrand) compiled to WebAssembly.
//
//   node tools/build.mjs            build dist/*.8xp2 + checksums
//   node tools/build.mjs --zip      also assemble release/MATRIX_EVO_RELEASE.zip
import { readFileSync, writeFileSync, readdirSync, mkdirSync, rmSync, copyFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import TIVarsLib from './tivars/TIVarsLib.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'src');
const DIST = join(ROOT, 'dist');
const lib = await TIVarsLib({ print: () => {}, printErr: () => {} });

// Every token word the Evo OS is known to define (from tivars_lib_cpp's EvoTokens.inc).
const known = new Set(
  readFileSync(join(ROOT, 'tools', 'tivars', 'EvoTokens.inc'), 'utf8')
    .match(/0x[0-9A-Fa-f]{4}(?=,\s*")/g).map(h => parseInt(h, 16)));

// Tokens that exist in the Evo table but are documented as removed / erroring.
const REMOVED = new Map([[0xE4E5, 'Archive'], [0xE4E6, 'UnArchive']]);

const normalize = s => s.replace(/\r\n/g, '\n').replace(/[ \t]+$/gm, '').replace(/\n+$/, '');

function stripComments(text) {
  // Lines whose first non-blank characters are "//" are build-time comments and are
  // not sent to the calculator. Blank lines are dropped as well.
  return text.split(/\r?\n/).filter(l => !/^\s*\/\//.test(l) && l.trim() !== '').join('\n')
    // The tokenizer only recognizes "Pause " (with its space); a bare Pause would be
    // stored as the letters P,a,u,s,e and fail with a syntax error on the calculator.
    .replace(/Pause(?=\n|:|$)/g, 'Pause ');
}

// Outside strings, runs of letter tokens mean a command name was not recognized
// (e.g. "Pause" -> P a u s e). Lowercase letters never appear in Matrix Evo code.
function checkLetterRuns(name, words) {
  let inString = false, inName = false, inList = false, run = 0;
  for (const w of words) {
    if (w === 0xE416 && !inName) { inString = !inString; run = 0; continue; }
    if (w === 0xE41C) { inString = false; inName = false; run = 0; continue; }
    if (w === 0xE418 && !inString) { inName = false; run = 0; continue; }
    if (w === 0xE81C && !inString) { inName = true; continue; }   // prgmNAME: letters are the name
    if (inString || inName) continue;
    if (w === 0xE836) { inList = true; run = 0; continue; }          // ʟNAME: letters are the name
    if (inList && ((w >= 0xE800 && w <= 0xE819) || (w >= 0xE401 && w <= 0xE40A))) continue;
    inList = false;
    if (w >= 0x0061 && w <= 0x007A)
      throw new Error(`${name}: lowercase letter token outside a string (unrecognized command?)`);
    run = (w >= 0xE800 && w <= 0xE81A) ? run + 1 : 0;
    if (run >= 4) throw new Error(`${name}: ${run} single-letter variables in a row outside a string (unrecognized command?)`);
  }
}

function build(name, source) {
  const p = lib.TIVarFile.createNew('Program', name, '84+CE');
  p.setContentFromString(source);
  p.convertToModel('84Evo', true);
  const vpath = p.saveVarToFile('', name);
  const bytes = lib.FS.readFile(vpath);
  // Validate: reload the produced container and compare decoded text with the source.
  lib.FS.writeFile('/check.8xp2', bytes);
  const f = lib.TIVarFile.loadFromFile('/check.8xp2');
  if (!f.isEvoFormat()) throw new Error(`${name}: output is not an Evo container`);
  const info = JSON.parse(f.getReadableContent());
  if (info.name !== name) throw new Error(`${name}: name round-trip gave ${info.name}`);
  const back = normalize(info.code);
  const want = normalize(source);
  if (back !== want) {
    const a = want.split('\n'), b = back.split('\n');
    for (let i = 0; i < Math.max(a.length, b.length); i++)
      if (a[i] !== b[i]) throw new Error(`${name}: line ${i + 1} does not round-trip\n  src: ${a[i]}\n  got: ${b[i]}`);
  }
  const words = info.rawDataHex.match(/..../g).map(w => parseInt(w.slice(2) + w.slice(0, 2), 16));
  checkLetterRuns(name, words);
  for (const w of words) {
    if (!known.has(w)) throw new Error(`${name}: token 0x${w.toString(16)} is not in the Evo token table`);
    if (REMOVED.has(w)) throw new Error(`${name}: uses ${REMOVED.get(w)}, which the Evo removed`);
  }
  return { bytes, tokens: words.length };
}

rmSync(DIST, { recursive: true, force: true });
mkdirSync(DIST, { recursive: true });
const sums = [];
let total = 0;
for (const file of readdirSync(SRC).filter(f => f.endsWith('.tib')).sort()) {
  const name = file.replace(/\.tib$/, '');
  if (!/^[A-Z][A-Z0-9]{0,7}$/.test(name)) throw new Error(`${file}: invalid program name`);
  const { bytes, tokens } = build(name, stripComments(readFileSync(join(SRC, file), 'utf8')));
  writeFileSync(join(DIST, `${name}.8xp2`), bytes);
  const sha = createHash('sha256').update(bytes).digest('hex');
  sums.push(`${sha}  ${name}.8xp2`);
  total += bytes.length;
  console.log(`${name.padEnd(8)} ${String(tokens).padStart(6)} tokens ${String(bytes.length).padStart(7)} bytes`);
}
writeFileSync(join(DIST, 'SHA256SUMS'), sums.join('\n') + '\n');
console.log(`built ${sums.length} programs, ${total} bytes -> dist/`);

if (process.argv.includes('--zip')) {
  const stage = join(ROOT, 'release', 'MATRIX_EVO_RELEASE');
  rmSync(join(ROOT, 'release'), { recursive: true, force: true });
  mkdirSync(join(stage, 'source'), { recursive: true });
  mkdirSync(join(stage, 'tests'), { recursive: true });
  for (const f of readdirSync(DIST)) copyFileSync(join(DIST, f), join(stage, f));
  for (const f of readdirSync(SRC)) copyFileSync(join(SRC, f), join(stage, 'source', f));
  for (const f of readdirSync(join(ROOT, 'tests'))) if (/\.(py|md|txt)$/.test(f)) copyFileSync(join(ROOT, 'tests', f), join(stage, 'tests', f));
  copyFileSync(join(ROOT, 'tools', 'tibsim.py'), join(stage, 'tests', 'tibsim.py'));
  copyFileSync(join(ROOT, 'LICENSE'), join(stage, 'LICENSE.txt'));
  for (const f of ['INSTALL.txt', 'USER_GUIDE.md', 'COMPATIBILITY.txt'])
    if (existsSync(join(ROOT, 'docs', f))) copyFileSync(join(ROOT, 'docs', f), join(stage, f));
  const zip = join(ROOT, 'release', 'MATRIX_EVO_RELEASE.zip');
  execFileSync('python', ['-c',
    'import shutil,sys; shutil.make_archive(sys.argv[1][:-4], "zip", sys.argv[2], "MATRIX_EVO_RELEASE")',
    zip, join(ROOT, 'release')]);
  console.log(`release -> ${zip}`);
}
