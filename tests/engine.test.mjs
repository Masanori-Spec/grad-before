import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {analyze,repair,LIMITS} from '../src/engine.mjs';
const original=fs.readFileSync('fixtures/original.svg','utf8'),control=fs.readFileSync('fixtures/manual-control.svg','utf8'),bytes=s=>new TextEncoder().encode(s),text=b=>new TextDecoder('utf-8',{ignoreBOM:true}).decode(b);
test('literal hand-ordered control and dependency graph match without changing a gradient or artwork byte',()=>{const result=repair(bytes(original));assert.equal(text(result.output),control);assert.deepEqual(result.report.beforeOrder,['paintA','radialLeaf','bridgeB','sharedC']);assert.deepEqual(result.report.afterOrder,['sharedC','bridgeB','paintA','radialLeaf']);assert.deepEqual(result.report.dependencies,[{id:'paintA',base:'bridgeB'},{id:'radialLeaf',base:'sharedC'},{id:'bridgeB',base:'sharedC'}]);const a=analyze(bytes(original)),b=analyze(result.output);assert.deepEqual(a.outside,b.outside);for(const [id,n]of a.byId)assert.equal(b.byId.get(id).raw,n.raw);assert.equal(b.byId.get('sharedC').children.length,3);});
test('already ordered output is byte-idempotent',()=>{const first=repair(bytes(original)),second=repair(first.output);assert.deepEqual(second.output,first.output);assert.equal(second.report.changed,false);assert.deepEqual(second.report.moved,[]);});
test('Unicode, CRLF, comments, quote choices and BOM remain exact outside and inside moved blocks',()=>{const input='\ufeff'+original.replaceAll('\n','\r\n').replace('<defs>','<!-- 日本語 🧭 é <ignored> -->\r\n  <defs>').replace('offset="0.5"',"offset='0.5'");const result=repair(bytes(input)),a=analyze(bytes(input)),b=analyze(result.output);assert.deepEqual(a.outside,b.outside);assert.equal(result.output.byteLength,bytes(input).byteLength);assert.equal(text(result.output)[0],'\ufeff');for(const n of a.gradients)assert.equal(b.byId.get(n.attrs.id).raw,n.raw);});
test('plain SVG2 href and bounded static transforms preserve their spelling',()=>{const input=original.replaceAll('xlink:href=','href=').replace('id="paintA"','id="paintA" gradientTransform="matrix(1 0 0 1 0 0)"');const result=repair(bytes(input));assert.equal(analyze(result.output).byId.get('paintA').attrs.href,'#bridgeB');assert.ok(text(result.output).includes('gradientTransform="matrix(1 0 0 1 0 0)"'));});
for(const [name,mutate]of[
 ['cycle',s=>s.replace('xlink:href="#sharedC" gradientUnits="userSpaceOnUse" x1="200"','xlink:href="#paintA" gradientUnits="userSpaceOnUse" x1="200"')],
 ['missing dependency',s=>s.replace('xlink:href="#bridgeB"','xlink:href="#missing"')],
 ['radial base',s=>s.replace('xlink:href="#bridgeB"','xlink:href="#radialLeaf"')],
 ['external gradient',s=>s.replace('xlink:href="#bridgeB"','xlink:href="https://example.invalid/x.svg#bridgeB"')],
 ['external paint',s=>s.replace('fill="url(#paintA)"','fill="url(https://example.invalid/x.svg#paintA)"')],
 ['stylesheet',s=>s.replace('<defs>','<style>linearGradient:first-child{stop-color:red}</style><defs>')],
 ['processing instruction',s=>'<?xml-stylesheet href="remote.css"?>'+s.replace(/^<\?xml[^>]+>\n/,'')],
 ['script',s=>s.replace('<defs>','<script>globalThis.BAD=1</script><defs>')],
 ['animation',s=>s.replace('<defs>','<animate attributeName="opacity" values="0;1"/><defs>')],
 ['event handler',s=>s.replace('id="panelA"','id="panelA" onload="BAD()"')],
 ['foreign XML',s=>s.replace('<defs>','<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">x</div></foreignObject><defs>')],
 ['DTD entities',s=>s.replace('<svg ','<!DOCTYPE svg [<!ENTITY bad SYSTEM "file:///etc/passwd">]><svg ')],
 ['duplicate gradient ID',s=>s.replace('id="bridgeB"','id="paintA"')],
 ['duplicate artwork/stop ID',s=>s.replace('id="panelA"','id="greenStop"')],
 ['missing gradient ID',s=>s.replace('id="paintA"','')],
 ['dual href',s=>s.replace('id="paintA"','id="paintA" href="#bridgeB"')],
 ['cross-defs reference',s=>s.replace('  <defs>','  <defs/><defs>')],
 ['unknown defs child',s=>s.replace('<defs>','<defs><filter id="f"/>')],
 ['own stops plus href',s=>s.replace('x2="180" y2="20"/>','x2="180" y2="20"><stop offset="0" stop-color="#ffffff"/></linearGradient>')],
 ['repeat spread',s=>s.replace('id="paintA"','id="paintA" spreadMethod="repeat"')],
 ['bounding-box gradient',s=>s.replace('gradientUnits="userSpaceOnUse"','gradientUnits="objectBoundingBox"')],
 ['implicit painted geometry',s=>s.replace('x1="20"','')],
 ['off-center radial focus',s=>s.replace('fx="460"','fx="450"')],
 ['radial without base',s=>s.replace('id="radialLeaf" xlink:href="#sharedC"','id="radialLeaf"')],
 ['percentage stops',s=>s.replace('offset="0.5"','offset="50%"')],
 ['unknown CSS',s=>s.replace('stop-opacity:1','stop-opacity:1;filter:url(#paintA)')],
 ['dynamic CSS',s=>s.replace('stop-color:#00ff00','stop-color:var(--paint)')],
 ['aliased href namespace',s=>s.replace('xmlns:xlink=','xmlns:other=').replaceAll('xlink:href','other:href')],
 ['XML base',s=>s.replace('<defs>','<defs xml:base="https://example.invalid/">')],
])test('reject '+name,()=>assert.throws(()=>repair(bytes(mutate(original)))));
test('invalid UTF-8, oversized input and overlong dependency chains fail closed',()=>{const invalid=Buffer.from(original);invalid[invalid.indexOf('Shared')]=255;assert.throws(()=>repair(invalid),/UTF-8/);assert.throws(()=>repair(new Uint8Array(LIMITS.bytes+1)),/1 MiB/);const chain=Array.from({length:65},(_,i)=>`<linearGradient id="G${i}" href="#G${i+1}"/>`).join('')+'<linearGradient id="G65"><stop offset="0" stop-color="#ff0000"/></linearGradient>';assert.throws(()=>repair(bytes(`<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><defs>${chain}</defs></svg>`)),/chain/);});
test('missing references and changed stops cannot satisfy the literal preservation oracle',()=>{assert.throws(()=>repair(bytes(original.replace('#bridgeB','#wrongBase'))),/Missing/);const changed=repair(bytes(original.replace('#00ff00','#ffff00')));assert.notEqual(text(changed.output),control);assert.notEqual(analyze(changed.output).byId.get('sharedC').raw,analyze(bytes(control)).byId.get('sharedC').raw);});

for(const d of ['M 1e9999,20 L 180,20','M 1e,20 L 180,20','M 1000001,0 L 10,10','M 0,0 L 1','M 0,0,,L 1,1','M 0,0 A 1 1 0 2 0 2 2','L 0 0'])test('reject malformed or unbounded path '+d,()=>assert.throws(()=>repair(bytes(original.replace('M 20,20 L 180,20 L 180,180 L 20,180 Z',d)))));
test('compact valid path numbers, curves and separated arc flags remain byte-preserved',()=>{const input=original.replace('M 20,20 L 180,20 L 180,180 L 20,180 Z','M2e1,20L180 20H170V180C150 150 50 150 20 180Q10 100 20 20A10 10 0 0 1 20 20Z');assert.ok(text(repair(bytes(input)).output).includes('M2e1,20L180'));});
test('direct and indirect inherited-only gradient transforms reject, explicit painted override stays intact',()=>{assert.throws(()=>repair(bytes(original.replace('id="bridgeB"','id="bridgeB" gradientTransform="translate(5 0)"'))),/Inherited/);assert.throws(()=>repair(bytes(original.replace('id="sharedC"','id="sharedC" gradientTransform="translate(5 0)"'))),/Inherited/);const input=original.replace('id="bridgeB"','id="bridgeB" gradientTransform="translate(5 0)"').replace('id="paintA"','id="paintA" gradientTransform="matrix(1 0 0 1 0 0)"');assert.ok(repair(bytes(input)).report.changed);});
