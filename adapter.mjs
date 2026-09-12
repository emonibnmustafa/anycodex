import http from 'node:http';
import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const PORT = 8765;
const CODEX_DIR = path.join(os.homedir(), '.codex');
const PROVIDERS_CONFIG_PATH = path.join(CODEX_DIR, 'custom_providers.json');
const LEGACY_KEY_FILE = path.join(CODEX_DIR, 'meta_key.txt');

function loadConfig() {
  const defaults = {
    active_provider: 'meta',
    providers: {
      meta: {
        name: 'Meta Muse Spark',
        base_url: 'https://api.meta.ai',
        api_key: '',
        model: 'muse-spark-1.3-contributor',
        wire_api: 'responses'
      }
    }
  };

  try {
    if (fs.existsSync(PROVIDERS_CONFIG_PATH)) {
      const data = JSON.parse(fs.readFileSync(PROVIDERS_CONFIG_PATH, 'utf8'));
      return { ...defaults, ...data, providers: { ...defaults.providers, ...(data.providers || {}) } };
    }
  } catch (e) {}

  return defaults;
}

function getActiveProvider() {
  const cfg = loadConfig();
  const activeId = cfg.active_provider || 'meta';
  const provider = cfg.providers?.[activeId] || cfg.providers?.meta || {};

  // Support legacy single key file if meta key not yet configured in json
  if (activeId === 'meta' && !provider.api_key && fs.existsSync(LEGACY_KEY_FILE)) {
    try {
      const key = fs.readFileSync(LEGACY_KEY_FILE, 'utf8').trim();
      if (key && key.length > 5) {
        provider.api_key = key;
      }
    } catch {}
  }

  return { id: activeId, ...provider };
}

const toolRegistry = new Map();

function cleanToolName(str) {
  return (str || '').replace(/[^a-zA-Z0-9_-]/g, '_');
}

function sanitizeSchema(schema) {
  if (!schema || typeof schema !== 'object') return schema;
  if (schema.type === 'object' || schema.properties) {
    schema.type = 'object';
    if (schema.properties && typeof schema.properties === 'object') {
      const propKeys = Object.keys(schema.properties);
      if (!Array.isArray(schema.required)) {
        schema.required = [];
      }
      for (const key of propKeys) {
        if (!schema.required.includes(key)) {
          schema.required.push(key);
        }
      }
      schema.additionalProperties = false;
      for (const val of Object.values(schema.properties)) {
        sanitizeSchema(val);
      }
    } else {
      schema.properties = {};
      schema.required = [];
      schema.additionalProperties = false;
    }
  } else if (schema.type === 'array' && schema.items) {
    sanitizeSchema(schema.items);
  }
  if (Array.isArray(schema.anyOf)) schema.anyOf.forEach(sanitizeSchema);
  if (Array.isArray(schema.oneOf)) schema.oneOf.forEach(sanitizeSchema);
  if (Array.isArray(schema.allOf)) schema.allOf.forEach(sanitizeSchema);
  return schema;
}

function buildMetaTools(rawTools, rawInputs) {
  const allRaw = Array.isArray(rawTools) ? [...rawTools] : [];
  if (Array.isArray(rawInputs)) {
    for (const item of rawInputs) {
      if (item && item.type === 'additional_tools' && Array.isArray(item.tools)) {
        allRaw.push(...item.tools);
      }
    }
  }

  const seenNames = new Set();
  const metaTools = [];

  function addTool(tool) {
    if (!tool || !tool.name || seenNames.has(tool.name)) return;
    seenNames.add(tool.name);
    metaTools.push(tool);
  }

  for (const t of allRaw) {
    if (!t) continue;
    if (t.type === 'namespace' && Array.isArray(t.tools)) {
      const origNs = t.name || '';
      let cleanNs = origNs;
      if (cleanNs.startsWith('mcp__')) {
        cleanNs = cleanNs.slice(5);
      }
      cleanNs = cleanToolName(cleanNs);
      const codexNs = origNs.startsWith('mcp__') ? origNs : (origNs ? `mcp__${origNs}` : '');

      for (const inner of t.tools) {
        if (!inner || !inner.name) continue;
        if (inner.name === 'exec') {
          toolRegistry.set('exec', { name: 'exec', namespace: undefined });
          addTool({
            type: 'function',
            name: 'exec',
            description: inner.description || 'Run JavaScript code to orchestrate/compose tool calls.\nNested tools are available on the global tools object, for example await tools.exec_command(...).\nAccepts raw JavaScript source text.',
            parameters: {
              type: 'object',
              properties: {
                code: {
                  type: 'string',
                  description: 'Raw JavaScript code to execute, e.g. const r = await tools.exec_command({cmd: "..."}); text(r.output);'
                }
              },
              required: ['code'],
              additionalProperties: false
            },
            strict: true
          });
        } else {
          const innerClean = cleanToolName(inner.name);
          const metaName = cleanNs ? `${cleanNs}__${innerClean}` : innerClean;
          toolRegistry.set(metaName, {
            name: inner.name,
            namespace: codexNs
          });

          let desc = inner.description || inner.name || 'tool function';
          if (inner.name === 'js' && (cleanNs === 'cua_repl' || origNs.includes('cua_repl'))) {
            desc = 'UI automation through a persistent JavaScript session using the initialized CUA API.\n' +
              'Controls macOS desktop apps, real mouse clicks, typing, window management, screen inspection, and Chrome browser tabs.\n' +
              'Entry points: await cua.getState(), let app = await cua.getApp("App Name"), let tab = await cua.createBrowserTab("chrome", url), let tab = await cua.getTab(tabId, { browser: browserId }).';
          }

          addTool({
            type: 'function',
            name: metaName,
            description: desc,
            parameters: sanitizeSchema(inner.parameters || { type: 'object', properties: {} }),
            strict: true
          });
        }
      }
    } else if (t.name === 'exec') {
      toolRegistry.set('exec', { name: 'exec', namespace: undefined });
      addTool({
        type: 'function',
        name: 'exec',
        description: t.description || 'Run JavaScript code to orchestrate/compose tool calls.\nNested tools are available on the global tools object, for example await tools.exec_command(...).\nAccepts raw JavaScript source text.',
        parameters: {
          type: 'object',
          properties: {
            code: {
              type: 'string',
              description: 'Raw JavaScript code to execute, e.g. const r = await tools.exec_command({cmd: "..."}); text(r.output);'
            }
          },
          required: ['code'],
          additionalProperties: false
        },
        strict: true
      });
    } else {
      const cleanName = cleanToolName(t.name || 'tool');
      toolRegistry.set(cleanName, {
        name: t.name,
        namespace: undefined
      });
      addTool({
        type: 'function',
        name: cleanName,
        description: t.description || t.name || 'tool function',
        parameters: sanitizeSchema(t.parameters || { type: 'object', properties: {} }),
        strict: true
      });
    }
  }
  return metaTools;
}

function extractText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content.map(c => {
      if (typeof c === 'string') return c;
      if (c && typeof c === 'object') {
        return c.text || c.output_text || c.input_text || '';
      }
      return '';
    }).join('');
  }
  return '';
}

function translateInputs(inputs) {
  if (!Array.isArray(inputs)) return inputs;
  const cleanInputs = [];
  for (const item of inputs) {
    if (!item) continue;
    const itype = item.type;
    if (
      itype === 'additional_tools' ||
      itype === 'compacted_history' ||
      itype === 'reasoning' ||
      itype === 'tool_search_call' ||
      itype === 'tool_search_output' ||
      itype === 'context_compaction' ||
      itype === 'compaction' ||
      itype === 'compaction_trigger' ||
      itype === 'configuration_update' ||
      itype === 'sub_agent_activity' ||
      itype === 'subAgentActivity' ||
      itype === 'collab_agent_tool_call' ||
      itype === 'collabAgentToolCall' ||
      itype === 'image_view' ||
      itype === 'imageView'
    ) {
      continue;
    }

    const cleanItem = { ...item };
    delete cleanItem.encrypted_content;
    delete cleanItem.internal_chat_message_metadata_passthrough;

    if (itype === 'user_message' || (itype === 'message' && cleanItem.role === 'user')) {
      cleanInputs.push({
        type: 'message',
        role: 'user',
        content: cleanItem.content
      });
    } else if (itype === 'agent_message' || (itype === 'message' && cleanItem.role === 'assistant')) {
      const textContent = extractText(cleanItem.content);
      cleanInputs.push({
        type: 'message',
        role: 'assistant',
        content: textContent
      });
    } else if (itype === 'custom_tool_call') {
      cleanInputs.push({
        type: 'function_call',
        id: cleanItem.id || cleanItem.call_id,
        call_id: cleanItem.call_id,
        name: 'exec',
        arguments: JSON.stringify({ code: cleanItem.input || '' })
      });
    } else if (itype === 'custom_tool_call_output') {
      cleanInputs.push({
        type: 'function_call_output',
        call_id: cleanItem.call_id,
        output: typeof cleanItem.output === 'string' ? cleanItem.output : JSON.stringify(cleanItem.output || '')
      });
    } else if (itype === 'local_shell_call') {
      cleanInputs.push({
        type: 'function_call',
        id: cleanItem.id || cleanItem.call_id,
        call_id: cleanItem.call_id,
        name: 'exec',
        arguments: JSON.stringify({ code: cleanItem.command || cleanItem.input || '' })
      });
    } else if (itype === 'function_call') {
      if (cleanItem.arguments && typeof cleanItem.arguments === 'object') {
        cleanItem.arguments = JSON.stringify(cleanItem.arguments);
      }
      if (cleanItem.namespace) {
        let ns = cleanItem.namespace;
        if (ns.startsWith('mcp__')) {
          ns = ns.slice(5);
        }
        cleanItem.name = `${cleanToolName(ns)}__${cleanToolName(cleanItem.name)}`;
        delete cleanItem.namespace;
      }
      cleanInputs.push(cleanItem);
    } else if (itype === 'mcp_tool_call') {
      const server = cleanToolName(cleanItem.server || '');
      const tool = cleanToolName(cleanItem.tool || '');
      const callName = server ? `${server}__${tool}` : tool;
      cleanInputs.push({
        type: 'function_call',
        id: cleanItem.id || cleanItem.call_id,
        call_id: cleanItem.call_id,
        name: callName,
        arguments: typeof cleanItem.arguments === 'string' ? cleanItem.arguments : JSON.stringify(cleanItem.arguments || {})
      });
    } else if (itype === 'mcp_tool_call_output') {
      let outStr = '';
      if (cleanItem.result && Array.isArray(cleanItem.result.content)) {
        outStr = cleanItem.result.content.map(c => c.text || JSON.stringify(c)).join('\n');
      } else if (cleanItem.output) {
        outStr = typeof cleanItem.output === 'string' ? cleanItem.output : JSON.stringify(cleanItem.output);
      }
      cleanInputs.push({
        type: 'function_call_output',
        call_id: cleanItem.call_id,
        output: outStr
      });
    } else {
      cleanInputs.push(cleanItem);
    }
  }
  return cleanInputs;
}

function transformItem(item) {
  if (!item || typeof item !== 'object') return;
  if (item.name === 'exec' || (typeof item.name === 'string' && item.name.endsWith('__exec'))) {
    item.type = 'custom_tool_call';
    item.name = 'exec';
    delete item.namespace;
    if (item.arguments !== undefined) {
      try {
        const parsed = JSON.parse(item.arguments);
        item.input = parsed.code || item.arguments;
      } catch {
        item.input = item.arguments;
      }
      delete item.arguments;
    } else if (item.input === undefined) {
      item.input = '';
    }
    return;
  }

  if (typeof item.name === 'string') {
    if (toolRegistry.has(item.name)) {
      const entry = toolRegistry.get(item.name);
      item.name = entry.name;
      if (entry.namespace) {
        item.namespace = entry.namespace;
      } else {
        delete item.namespace;
      }
      return;
    }

    if (item.name.includes('__')) {
      const idx = item.name.lastIndexOf('__');
      let ns = item.name.slice(0, idx);
      const name = item.name.slice(idx + 2);
      if (!ns.startsWith('mcp__')) {
        ns = 'mcp__' + ns;
      }
      item.namespace = ns;
      item.name = name;
    }
  }
}

function transformPayload(payload) {
  if (!payload || typeof payload !== 'object') return;
  if (payload.item) {
    transformItem(payload.item);
  }
  if (payload.response && Array.isArray(payload.response.output)) {
    for (const item of payload.response.output) {
      transformItem(item);
    }
  }
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && (req.url === '/health' || req.url === '/')) {
    const provider = getActiveProvider();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'anycodex-adapter', active_provider: provider.name || provider.id }));
    return;
  }

  if (req.method !== 'POST') {
    res.writeHead(405);
    res.end();
    return;
  }

  const chunks = [];
  req.on('data', chunk => chunks.push(chunk));
  req.on('end', () => {
    try {
      const body = Buffer.concat(chunks).toString('utf8');
      const provider = getActiveProvider();

      const targetUrl = new URL(provider.base_url || 'https://api.meta.ai');
      const isHttps = targetUrl.protocol === 'https:';
      const client = isHttps ? https : http;
      const targetPort = targetUrl.port || (isHttps ? 443 : 80);

      const forwardPath = req.url.startsWith('/v1') ? req.url : `/v1${req.url}`;

      // If request body is not JSON (e.g. multipart audio/realtime boundary), pass through directly
      if (!body.trim().startsWith('{')) {
        const proxyReq = client.request(
          {
            hostname: targetUrl.hostname,
            port: targetPort,
            path: forwardPath,
            method: req.method,
            headers: {
              ...req.headers,
              host: targetUrl.hostname,
              authorization: `Bearer ${provider.api_key || ''}`
            }
          },
          proxyRes => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
          }
        );
        proxyReq.on('error', err => {
          res.writeHead(502, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: { message: err.message, type: 'upstream_error' } }));
        });
        proxyReq.write(Buffer.concat(chunks));
        proxyReq.end();
        return;
      }

      const data = JSON.parse(body);

      // Set target provider model
      if (provider.model) {
        data.model = provider.model;
      }

      data.tools = buildMetaTools(data.tools, data.input);
      data.input = translateInputs(data.input);

      const modifiedPayload = JSON.stringify(data);
      const headers = {
        'content-type': 'application/json',
        'content-length': Buffer.byteLength(modifiedPayload),
        'authorization': `Bearer ${provider.api_key || ''}`
      };

      const proxyReq = client.request(
        {
          hostname: targetUrl.hostname,
          port: targetPort,
          path: forwardPath,
          method: 'POST',
          headers: headers
        },
        proxyRes => {
          const isOk = proxyRes.statusCode >= 200 && proxyRes.statusCode < 300;
          if (!isOk) {
            res.writeHead(proxyRes.statusCode, {
              'content-type': proxyRes.headers['content-type'] || 'application/json',
              'cache-control': 'no-cache'
            });
            proxyRes.pipe(res);
            return;
          }

          const contentType = proxyRes.headers['content-type'] || '';
          if (!contentType.includes('text/event-stream')) {
            const resChunks = [];
            proxyRes.on('data', c => resChunks.push(c));
            proxyRes.on('end', () => {
              try {
                const resBody = Buffer.concat(resChunks).toString('utf8');
                const parsed = JSON.parse(resBody);
                transformPayload(parsed);
                const outStr = JSON.stringify(parsed);
                res.writeHead(proxyRes.statusCode, {
                  ...proxyRes.headers,
                  'content-length': Buffer.byteLength(outStr)
                });
                res.end(outStr);
              } catch {
                res.writeHead(proxyRes.statusCode, proxyRes.headers);
                res.end(Buffer.concat(resChunks));
              }
            });
            return;
          }

          res.writeHead(proxyRes.statusCode, {
            'content-type': 'text/event-stream; charset=utf-8',
            'cache-control': 'no-cache',
            'connection': 'keep-alive'
          });

          let buffer = '';
          proxyRes.on('data', chunk => {
            buffer += chunk.toString('utf8');
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (let line of lines) {
              const trimmed = line.trimEnd();
              const isData = trimmed.startsWith('data:') || trimmed.startsWith('data: ');
              if (isData && !trimmed.startsWith('data: [DONE]')) {
                const dataSlice = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed.slice(5);
                try {
                  const payload = JSON.parse(dataSlice);
                  transformPayload(payload);
                  res.write(`data: ${JSON.stringify(payload)}\n\n`);
                  continue;
                } catch (err) {}
              }
              res.write(line + '\n');
            }
          });

          proxyRes.on('end', () => {
            if (buffer) {
              const trimmed = buffer.trimEnd();
              const isData = trimmed.startsWith('data:') || trimmed.startsWith('data: ');
              if (isData && !trimmed.startsWith('data: [DONE]')) {
                const dataSlice = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed.slice(5);
                try {
                  const payload = JSON.parse(dataSlice);
                  transformPayload(payload);
                  res.write(`data: ${JSON.stringify(payload)}\n\n`);
                } catch {
                  res.write(buffer + '\n');
                }
              } else {
                res.write(buffer + '\n');
              }
            }
            res.end();
          });
        }
      );

      proxyReq.on('error', err => {
        console.error('Upstream error:', err);
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { message: err.message, type: 'upstream_error' } }));
      });

      proxyReq.write(modifiedPayload);
      proxyReq.end();
    } catch (e) {
      console.error('Adapter error:', e);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: { message: e.message, type: 'adapter_error' } }));
    }
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`AnyCodex Gateway running on http://127.0.0.1:${PORT}`);
});
