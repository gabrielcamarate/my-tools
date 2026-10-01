// Protocol discovery only: no browser, credential, application or model request.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const source = resolve(process.argv[2]);
const { Client } = await import(pathToFileURL(resolve(source, 'node_modules/@modelcontextprotocol/client/dist/index.mjs')).href);
const { StdioClientTransport } = await import(pathToFileURL(resolve(source, 'node_modules/@modelcontextprotocol/client/dist/stdio.mjs')).href);
const client = new Client({ name: 'my-tools-discovery', version: '1' });
try {
 await client.connect(new StdioClientTransport({command:process.execPath,args:[resolve(source,'dist/mcp-stdio.js')],stderr:'pipe'}));
 const names=(await client.listTools()).tools.map(t=>t.name);
 for(const name of ['browser_run','browser_goto','browser_assert','browser_snapshot','browser_close']) assert.ok(names.includes(name), `Missing ${name}`);
 console.log(JSON.stringify({tools:names.length,required_tools:true}));
} finally {await client.close();}
