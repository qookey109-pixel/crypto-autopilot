// No production execution authority. The caller must choose this fixed reader
// server-side; request data must never supply a fetcher or override its policy.
import { parseUnique } from "./github-oidc.mjs";

const JWKS = "https://token.actions.githubusercontent.com/.well-known/jwks";
const MAX_BYTES = 65536;
export async function readGithubKeys({ enabled = false, fetcher = fetch } = {}) {
  if (enabled !== true) return null;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  let reader;
  try {
    const response = await fetcher(JWKS, { method: "GET", redirect: "manual", signal: controller.signal });
    if (response.status !== 200 || !response.body) return null;
    const length = response.headers.get("content-length");
    if (length !== null && (!/^[0-9]+$/.test(length) || Number(length) > MAX_BYTES)) return null;
    reader = response.body.getReader();
    let total = 0;
    const chunks = [];
    for (;;) {
      const part = await reader.read();
      if (part.done) break;
      total += part.value.byteLength;
      if (total > MAX_BYTES) return null;
      chunks.push(part.value);
    }
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const data = parseUnique(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    if (!data || typeof data !== "object" || Array.isArray(data) ||
        !Array.isArray(data.keys) || data.keys.length > 32) return null;
    return data;
  } catch { return null; }
  finally {
    clearTimeout(timer);
    if (reader) { try { await reader.cancel(); } catch {} }
  }
}
