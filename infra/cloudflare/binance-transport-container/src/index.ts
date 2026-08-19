import { Container, ContainerProxy } from "@cloudflare/containers";

export { ContainerProxy };

export class BinanceTransportContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "1m";
  enableInternet = false;
  allowedHosts = ["fapi.binance.com"];
}

type Env = {
  BINANCE_TRANSPORT: DurableObjectNamespace;
  DIAGNOSTIC_TOKEN?: string;
};

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname !== "/check") {
      return new Response("not found", { status: 404 });
    }

    const expected = env.DIAGNOSTIC_TOKEN;
    const supplied = request.headers.get("authorization");
    if (!expected || supplied !== `Bearer ${expected}`) {
      return new Response("unauthorized", { status: 401 });
    }

    const container = env.BINANCE_TRANSPORT.getByName("binance-public-transport-v0-3");
    const upstreamRequest = new Request("https://container.internal/check", {
      method: "GET",
      headers: { "cache-control": "no-store" },
    });
    return container.fetch(upstreamRequest);
  },
};
