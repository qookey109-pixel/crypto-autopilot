const PUBLIC_PATHS = new Set(["/healthz", "/openapi.json", "/v0/capabilities"]);
const POST_PATHS = new Set(["/v0/indicators", "/v0/strategy", "/v0/risk", "/v0/backtest"]);
const MAX_REQUEST_BYTES = 2_000_000;

function jsonResponse(status, payload, requestId) {
  const headers = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-qookey-request-id": requestId,
  });
  return new Response(JSON.stringify(payload), { status, headers });
}

function bearerToken(request) {
  const header = request.headers.get("authorization") || "";
  return header.startsWith("Bearer ") ? header.slice(7) : "";
}

function normalizedOrigin(value) {
  const origin = String(value || "").trim().replace(/\/$/, "");
  if (!origin.startsWith("https://") && !origin.startsWith("http://")) {
    throw new Error("TOOLKIT_ORIGIN must be an absolute http(s) URL");
  }
  return origin;
}

async function proxy(request, env, requestId) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/$/, "") || "/";
  const isPublic = PUBLIC_PATHS.has(path);
  const isPost = POST_PATHS.has(path);

  if (!isPublic && !isPost) {
    return jsonResponse(404, { status: "ERROR", error: { code: "NOT_FOUND" } }, requestId);
  }
  if (isPost && request.method !== "POST") {
    return jsonResponse(405, { status: "ERROR", error: { code: "METHOD_NOT_ALLOWED" } }, requestId);
  }
  if (isPublic && request.method !== "GET") {
    return jsonResponse(405, { status: "ERROR", error: { code: "METHOD_NOT_ALLOWED" } }, requestId);
  }

  if (isPost) {
    if (!env.EDGE_API_TOKEN || !env.ORIGIN_API_TOKEN) {
      return jsonResponse(
        503,
        { status: "ERROR", error: { code: "EDGE_NOT_CONFIGURED" } },
        requestId,
      );
    }
    if (bearerToken(request) !== env.EDGE_API_TOKEN) {
      return jsonResponse(401, { status: "ERROR", error: { code: "UNAUTHORIZED" } }, requestId);
    }
  }

  let body;
  if (request.method === "POST") {
    const declaredLength = Number(request.headers.get("content-length") || "0");
    if (declaredLength > MAX_REQUEST_BYTES) {
      return jsonResponse(413, { status: "ERROR", error: { code: "PAYLOAD_TOO_LARGE" } }, requestId);
    }
    body = await request.arrayBuffer();
    if (body.byteLength > MAX_REQUEST_BYTES) {
      return jsonResponse(413, { status: "ERROR", error: { code: "PAYLOAD_TOO_LARGE" } }, requestId);
    }
  }

  let origin;
  try {
    origin = normalizedOrigin(env.TOOLKIT_ORIGIN);
  } catch (_error) {
    return jsonResponse(503, { status: "ERROR", error: { code: "ORIGIN_NOT_CONFIGURED" } }, requestId);
  }

  const upstreamUrl = new URL(`${origin}${path}${url.search}`);
  const headers = new Headers();
  headers.set("accept", "application/json");
  headers.set("x-qookey-request-id", requestId);
  if (request.headers.get("content-type")) {
    headers.set("content-type", request.headers.get("content-type"));
  }
  if (isPost) {
    headers.set("authorization", `Bearer ${env.ORIGIN_API_TOKEN}`);
  }

  const upstream = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body,
    redirect: "manual",
  });
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.set("cache-control", "no-store");
  responseHeaders.set("x-content-type-options", "nosniff");
  responseHeaders.set("referrer-policy", "no-referrer");
  responseHeaders.set("x-qookey-request-id", requestId);
  responseHeaders.delete("set-cookie");
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export default {
  async fetch(request, env) {
    const requestId = crypto.randomUUID();
    try {
      return await proxy(request, env, requestId);
    } catch (_error) {
      return jsonResponse(
        502,
        { status: "ERROR", error: { code: "UPSTREAM_FAILURE" } },
        requestId,
      );
    }
  },
};
