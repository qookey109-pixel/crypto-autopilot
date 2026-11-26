# Live Paper workflow inputs

This directory is the only repository input root accepted by the manual Live Paper Run Coordinator workflow.

Inputs must be committed JSON files using the frozen `qookey-live-paper-run-coordinator-input-v0.1` schema. Never place secrets, private exchange credentials, holdout data, or real-money order instructions here. A file in this directory is input evidence only and does not grant execution authority.

The prepared Paper gateway uses the [coordinator input registry](../../../config/live_paper_coordinator_input_registry_v0_1.json) to identify reviewed paths and their Git blob IDs. An empty list approves no inputs. To propose an input, commit its JSON and a matching registry entry together for review. Cloud CI checks the coordinator schema and the Git blob ID of the file. Approval of file content alone does not authorize dispatch or storage access. The existing manual workflow retains its own versioned authority.
