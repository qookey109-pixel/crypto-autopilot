(() => {
  const SOURCE = "./data/current-operations.json";

  function text(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function validate(payload) {
    if (!payload || payload.schema !== "qookey-current-operations-web-v0.3") return false;
    if (payload.authority !== false || payload.mode !== "PAPER_AND_LIVE_PAPER_ONLY") return false;
    if (payload.repositoryAuthority !== "RESOLVE_MAIN_LIVE_AT_READ_TIME") return false;
    if (payload.evidenceBasisIsLatestMainClaim !== false) return false;
    if (payload.historyStatus !== "COMPLETE" || payload.historyCompleteShards !== 10 || payload.historyTotalShards !== 10) return false;
    if (payload.trainingStatus !== "COMPLETED_PASS") return false;
    if (payload.modelQualityStatus !== "REJECT") return false;
    if (payload.thresholdChangeSupported !== false) return false;
    if (payload.pionexValidationStatus !== "COMPLETE_PASS") return false;
    if (payload.holdoutState !== "FROZEN_UNOPENED") return false;
    if (payload.pionexMaterializationRunId !== 35054729471) return false;
    if (payload.publicLiveMarketDataAuthorized !== true || payload.livePaperSimulationAuthorized !== true) return false;
    if (payload.sourceSwitchAuthorized !== false || payload.liveTradingAuthorized !== false || payload.liveRealTradingAuthorized !== false) return false;
    return true;
  }

  function apply(payload) {
    text("home-history-state", "10/10 分片 · COMPLETE");
    text(
      "home-history-detail",
      `Core100 歷史資料已完成；Training run ${payload.trainingRunId} 已完成。Model Quality REJECT 不會自動重啟歷史資料取得。`
    );
    const source = document.getElementById("home-history-source");
    if (source) {
      source.href = "https://github.com/qookey109-pixel/crypto-autopilot/blob/main/CURRENT_STATUS.md";
      source.textContent = "查看 Current Status ↗";
    }

    text("home-research-state", "Model Quality REJECT");
    text(
      "home-research-detail",
      `Threshold replay run ${payload.thresholdReplayRunId} 已完成；0.50–0.55 沒有 supported threshold change，configured threshold 保持不變。`
    );

    text("readiness-heading", `${payload.updatedDate} 目前作業狀態`);
  }

  window.addEventListener("DOMContentLoaded", async () => {
    try {
      const response = await fetch(SOURCE, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (!validate(payload)) throw new Error("current operations projection rejected");
      apply(payload);
    } catch (error) {
      console.warn("Current operations projection unavailable", error);
    }
  });
})();
