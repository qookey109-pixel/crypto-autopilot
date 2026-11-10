// GitHub-only bounded diagnostic. No Cloudflare or exchange credentials.
// A successful diagnostic is not a production identity or budget authority.
import { parseUnique, verifyGithubJob } from "../../workers/paper-gateway/github-oidc.mjs";
import { readGithubKeys } from "../../workers/paper-gateway/github-keys.mjs";
import { readJobMetadata } from "../../workers/paper-gateway/github-metadata-reader.mjs";
import { checkJobMetadata } from "../../workers/paper-gateway/github-metadata.mjs";

const REPO = "qookey109-pixel/crypto-autopilot";
const FILE = "cloud-paper-github-identity-diagnostic-v0-2.yml";
const PATH = ".github/workflows/" + FILE;
const AUDIENCE = "qookey-cloud-paper-github-identity-diagnostic-v0-2";
const MAX = 131072;
const id = value => typeof value === "string" && /^[1-9][0-9]{0,15}$/.test(value);

async function readJson(fetcher, url, headers) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  let reader;
  try {
    const response = await fetcher(url, { method: "GET", redirect: "manual", signal: controller.signal, headers });
    if (response.status !== 200 || !response.body) return null;
    const length = response.headers.get("content-length");
    if (length !== null && (!/^[0-9]+$/.test(length) || Number(length) > MAX)) return null;
    reader = response.body.getReader();
    const chunks = []; let total = 0;
    for (;;) {
      const part = await reader.read();
      if (part.done) break;
      total += part.value.byteLength;
      if (total > MAX) return null;
      chunks.push(part.value);
    }
    const bytes = new Uint8Array(total); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const data = parseUnique(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    return data && typeof data === "object" && !Array.isArray(data) ? data : null;
  } catch { return null; }
  finally { clearTimeout(timer); if (reader) { try { await reader.cancel(); } catch {} } }
}

export async function runDiagnostic({ enabled = false, env = {}, fetcher = fetch, clock = Date.now } = {}) {
  if (enabled !== true) return { status: "DISABLED" };
  try {
    const runId = env.GITHUB_RUN_ID, repoId = env.GITHUB_REPOSITORY_ID, sha = env.GITHUB_SHA;
    let tokenUrl = null;
    try { tokenUrl = new URL(env.ACTIONS_ID_TOKEN_REQUEST_URL); } catch {}
    const checks = {
      event: env.GITHUB_EVENT_NAME === "workflow_dispatch",
      ref: env.GITHUB_REF === "refs/heads/main",
      repository: env.GITHUB_REPOSITORY === REPO,
      attempt: env.GITHUB_RUN_ATTEMPT === "1",
      confirmation: env.CONFIRM_DIAGNOSTIC === "true",
      run_id: id(runId),
      repository_id: id(repoId),
      sha: typeof sha === "string" && /^[a-f0-9]{40}$/.test(sha),
      github_token: typeof env.GITHUB_TOKEN === "string" && /^[A-Za-z0-9_-]{1,512}$/.test(env.GITHUB_TOKEN),
      oidc_request_token: typeof env.ACTIONS_ID_TOKEN_REQUEST_TOKEN === "string" &&
        /^[A-Za-z0-9_.-]{1,8192}$/.test(env.ACTIONS_ID_TOKEN_REQUEST_TOKEN),
      oidc_request_url: tokenUrl !== null && tokenUrl.protocol === "https:" && !tokenUrl.port &&
        !tokenUrl.username && !tokenUrl.password &&
        /^[a-z0-9-]+(?:\.[a-z0-9-]+)*\.actions\.githubusercontent\.com$/.test(tokenUrl.hostname),
      dependencies: typeof fetcher === "function" && typeof clock === "function",
    };
    const failed = Object.keys(checks).filter(key => checks[key] !== true);
    if (failed.length) return { status: "BLOCKED_CONTEXT", failed };
    const githubHeaders = { Authorization: "Bearer " + env.GITHUB_TOKEN, Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28" };
    const historyUrl = "https://api.github.com/repos/" + REPO + "/actions/workflows/" + FILE +
      "/runs?event=workflow_dispatch&per_page=2";
    const history = await readJson(fetcher, historyUrl, githubHeaders);
    const row = history?.workflow_runs?.[0];
    if (history?.total_count !== 1 || history.workflow_runs?.length !== 1 ||
        String(row?.id) !== runId || row?.run_attempt !== 1 || row?.event !== "workflow_dispatch" ||
        row?.head_sha !== sha || row?.head_branch !== "main" || row?.status !== "in_progress" ||
        !Number.isSafeInteger(row?.workflow_id) || row.workflow_id <= 0)
      return { status: "BLOCKED_HISTORY" };
    const now = clock();
    if (!Number.isSafeInteger(now) || now < 0) return { status: "BLOCKED_CLOCK" };
    tokenUrl.searchParams.set("audience", AUDIENCE);
    const response = await readJson(fetcher, tokenUrl.toString(),
      { Authorization: "Bearer " + env.ACTIONS_ID_TOKEN_REQUEST_TOKEN });
    if (typeof response?.value !== "string") return { status: "REVIEW_REQUIRED" };
    const identity = await verifyGithubJob(response.value, { enabled: true, now: Math.floor(now / 1000),
      policy: { audience: AUDIENCE, subject: "repo:" + REPO + ":ref:refs/heads/main",
        repository: REPO, repositoryId: repoId, workflowRef: REPO + "/" + PATH + "@refs/heads/main",
        workflowSha: sha, sha },
      fetchKeys: () => readGithubKeys({ enabled: true, fetcher }) });
    if (!identity || identity.runId !== runId || identity.eventName !== "workflow_dispatch")
      return { status: "REVIEW_REQUIRED" };
    const metadata = await readJobMetadata({ enabled: true, repository: REPO, identity,
      token: env.GITHUB_TOKEN, fetcher });
    const after = clock();
    if (!metadata || metadata.main?.commit?.sha !== sha || !Number.isSafeInteger(after) ||
        after < now || Math.floor(after / 1000) >= identity.expiresAt ||
        !checkJobMetadata(identity, metadata.run, metadata.job, { repositoryId: repoId,
          workflowId: String(row.workflow_id), workflowPath: PATH, sha, jobName: "diagnostic",
          maxAgeSeconds: 300, allowedEvents: ["workflow_dispatch"] }, after))
      return { status: "REVIEW_REQUIRED" };
    return { status: "IDENTITY_CORRELATION_OBSERVED" };
  } catch { return { status: "REVIEW_REQUIRED" }; }
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  const report = await runDiagnostic({ enabled: true, env: process.env });
  // Fixed status and failed check names only; never log tokens, headers, URLs, claims, or responses.
  process.stdout.write(JSON.stringify(report) + "\n");
  if (report.status !== "IDENTITY_CORRELATION_OBSERVED") process.exitCode = 1;
}
