using Workerd = import "/workerd/workerd.capnp";

const tests :Workerd.Config = (
  services = [
    (name = "signed-job", worker = (
      compatibilityDate = "2026-11-01",
      modules = [
        (name = "tests/worker/signed_job_cases.mjs", esModule = embed "signed_job_cases.mjs"),
        (name = "workers/paper-gateway/github-oidc.mjs", esModule = embed "../../workers/paper-gateway/github-oidc.mjs")
      ],
      globalOutbound = "offline"
    )),
    (name = "offline", worker = (
      compatibilityDate = "2026-11-01",
      modules = [(name = "offline.mjs", esModule = "export default { fetch() { throw new Error('Unexpected outbound request'); } };")]
    ))
  ]
);
