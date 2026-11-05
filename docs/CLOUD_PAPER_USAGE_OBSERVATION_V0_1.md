# Cloud Paper post-run usage observation V0.1

The prepared `run_observed_slot` wrapper runs the V0.5 composition and returns
the unmodified immutable Paper report plus a separate in-process observation.
On an exception it raises a fixed error carrying redacted partial observations;
it never retries storage or exposes raw error text. It checks for a pristine
runtime before installing the observer and remains disabled when activation is
false.

The observation distinguishes R2 SDK PUT/GET/LIST invocations, conservative R2
Class A/B and payload-byte reservations, provider request reservations, D1
transport attempts, and prepaid ticket debits. An SDK invocation or transport
attempt is not necessarily a request received or billed by a provider. D1 rows
read/written remain unknown. A successful observation links to the report
digest after the existing result readback and settlement.

This is not an independently attested identity, durable receipt, complete
account-wide usage or cost evidence. Its counters are process-local; a process
crash can lose them. It does not include the cost of any future artifact upload
or external evidence storage. The future controlled-main entrypoint must
separately define bounded persistence, account for its own cost, reconcile
provider-side usage and protect against bypass before claiming operational
acceptance. The current code creates no workflow, schedule, credentials, R2 or
D1 operation and grants no execution authority.
