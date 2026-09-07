"""Server-rendered public home page for a Grove Blossom server."""

from __future__ import annotations

from html import escape


def render_homepage(
    *,
    version: str,
    public_url: str,
    server_name: str,
    max_blob_size: int,
    supported_buds: list[str],
    service_npub: str | None,
    service_fips_ipv6_address: str | None,
) -> str:
    """Render a browser-facing server overview with escaped configuration."""

    values = {
        "version": escape(version),
        "public_url": escape(public_url),
        "server_name": escape(server_name),
        "max_blob_size": escape(_format_size(max_blob_size)),
        "supported_buds": escape(", ".join(f"BUD-{bud}" for bud in supported_buds)),
        "service_npub": escape(service_npub or "Not configured"),
        "service_fips_ipv6_address": escape(
            service_fips_ipv6_address or "Not configured"
        ),
    }

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Grove local-first Blossom blob storage">
  <meta name="color-scheme" content="light dark">
  <link rel="icon" href="/assets/grove-logo.png" type="image/png">
  <title>Grove | Local-first Blossom storage</title>
  <style>
    :root {{
      color-scheme: light;
      --page: #f7f7f1; --surface: #fff; --soft: #eef2e5;
      --ink: #1d2f22; --muted: #617064; --line: #dce2d5;
      --forest: #174d2c; --wood: #7a4a20; --green: #237a4b;
      --shadow: 0 18px 45px rgba(23, 77, 44, .09);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; background: var(--page); color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif; letter-spacing: 0;
    }}
    a {{ color: var(--forest); }}
    .shell {{
      width: min(100% - 2rem, 68rem); margin: 0 auto; padding: 1.25rem 0 3rem;
    }}
    .topbar {{
      display: flex; min-height: 2.75rem; align-items: center;
      justify-content: space-between; gap: 1rem; margin-bottom: 1rem;
    }}
    .brand {{
      display: flex; align-items: center; gap: .7rem; color: var(--forest);
      font-size: .82rem; font-weight: 760; text-transform: uppercase;
    }}
    .brand img {{ width: 2rem; height: 2rem; flex: 0 0 auto; object-fit: contain; }}
    .online {{
      display: inline-flex; align-items: center; gap: .45rem;
      color: var(--green); font-size: .82rem; font-weight: 720;
    }}
    .online::before {{
      width: .55rem; height: .55rem; border-radius: 50%; background: var(--green);
      content: ""; box-shadow: 0 0 0 .22rem rgba(35, 122, 75, .12);
    }}
    .hero {{
      display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(17rem, .65fr);
      gap: 1.5rem; align-items: stretch; padding: clamp(1.5rem, 5vw, 3.5rem);
      border: 1px solid var(--line); border-radius: 8px;
      background: var(--surface); box-shadow: var(--shadow);
    }}
    .eyebrow {{
      margin: 0 0 .8rem; color: var(--wood); font-size: .78rem;
      font-weight: 800; text-transform: uppercase;
    }}
    h1 {{
      margin: 0; color: var(--forest); font-size: clamp(3rem, 8vw, 5.4rem);
      line-height: .98; overflow-wrap: anywhere;
    }}
    .lede {{
      max-width: 39rem; margin: 1.2rem 0 1.5rem; color: var(--muted);
      font-size: clamp(1rem, 2vw, 1.18rem); line-height: 1.65;
    }}
    .server-address {{
      display: flex; max-width: 40rem; align-items: center; gap: .75rem;
      padding: .7rem .75rem .7rem 1rem; border: 1px solid var(--line);
      border-radius: 6px; background: var(--soft);
    }}
    .server-address code {{
      min-width: 0; flex: 1; overflow-wrap: anywhere;
      color: var(--forest); font-size: .86rem;
    }}
    button {{
      flex: 0 0 auto; min-height: 2.35rem; padding: .55rem .8rem; border: 0;
      border-radius: 5px; background: var(--forest); color: #fff; cursor: pointer;
      font: inherit; font-size: .78rem; font-weight: 720;
    }}
    button:focus-visible, a:focus-visible {{
      outline: 3px solid rgba(122, 74, 32, .42); outline-offset: 3px;
    }}
    .tree {{
      display: grid; min-height: 18rem; place-items: center; align-content: center;
      gap: 1rem; border-left: 1px solid var(--line); text-align: center;
    }}
    .tree img {{ width: min(13rem, 72%); height: auto; border-radius: 6px; }}
    .tree strong {{ display: block; color: var(--forest); font-size: 1.1rem; }}
    .tree span {{
      display: block; margin-top: .25rem; color: var(--muted); font-size: .84rem;
    }}
    .grid {{
      display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1rem; margin-top: 1rem;
    }}
    .panel {{
      padding: 1.35rem; border: 1px solid var(--line);
      border-radius: 8px; background: var(--surface);
    }}
    .panel h2 {{ margin: 0 0 1rem; color: var(--forest); font-size: 1rem; }}
    dl {{ margin: 0; }}
    .row {{
      display: grid; grid-template-columns: minmax(7.5rem, .4fr) minmax(0, 1fr);
      gap: 1rem; padding: .72rem 0; border-top: 1px solid var(--line);
    }}
    .row:first-child {{ padding-top: 0; border-top: 0; }}
    dt {{ color: var(--muted); font-size: .82rem; }}
    dd {{ margin: 0; overflow-wrap: anywhere; font-size: .86rem; font-weight: 650; }}
    .features {{
      display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .7rem;
      margin: 0; padding: 0; list-style: none;
    }}
    .features li {{
      display: flex; align-items: flex-start; gap: .55rem; color: var(--muted);
      font-size: .84rem; line-height: 1.45;
    }}
    .features li::before {{ color: var(--green); content: "\\2713"; font-weight: 850; }}
    .about {{
      margin-top: 1rem; padding: 1.2rem 1.35rem; border-left: .28rem solid var(--wood);
      background: #fbf5ec; color: #5f4933; font-size: .9rem; line-height: 1.6;
    }}
    .links {{
      display: flex; flex-wrap: wrap; gap: .85rem 1.25rem;
      margin-top: 1rem; padding: 0 .2rem; font-size: .82rem;
    }}
    .links a {{ font-weight: 680; text-decoration-thickness: 1px; }}
    .links .version {{ margin-left: auto; color: var(--muted); }}
    @media (max-width: 47rem) {{
      .shell {{ width: min(100% - 1.2rem, 68rem); }}
      .hero, .grid {{ grid-template-columns: 1fr; }}
      .hero {{ padding: 1.4rem; }}
      .tree {{
        min-height: auto; padding-top: 1.5rem;
        border-top: 1px solid var(--line); border-left: 0;
      }}
      .tree img {{ width: 8rem; }}
      .server-address {{ align-items: stretch; flex-direction: column; }}
      button {{ width: 100%; }}
      .links .version {{ width: 100%; margin-left: 0; }}
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        color-scheme: dark; --page: #111713; --surface: #19221c; --soft: #243027;
        --ink: #eff6ef; --muted: #b3c2b5; --line: #38463b;
        --forest: #9bc5a0; --wood: #d6a26b; --green: #76c794; --shadow: none;
      }}
      .about {{ background: #2a241d; color: #e4cfb5; }}
      button {{ background: #9bc5a0; color: #132319; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <img src="/assets/grove-logo.png" alt="Grove">
        <span>Grove Blossom server</span>
      </div>
      <div class="online">Online</div>
    </header>
    <section class="hero">
      <div>
        <p class="eyebrow">Local-first encrypted blob storage</p>
        <h1>Grove</h1>
        <p class="lede">
          A lean Blossom server that preserves opaque, content-addressed files
          without needing to understand their plaintext.
        </p>
        <div class="server-address">
          <code id="server-url">{values["public_url"]}</code>
          <button id="copy-server" type="button" aria-label="Copy server URL">
            Copy server URL
          </button>
        </div>
      </div>
      <div class="tree" aria-label="Server identity">
        <img src="/assets/grove-logo.png" alt="Grove tree logo">
        <div>
          <strong>Blossom storage</strong>
          <span>Content-addressed blob service</span>
        </div>
      </div>
    </section>
    <div class="grid">
      <section class="panel">
        <h2>Server details</h2>
        <dl>
          <div class="row"><dt>Status</dt><dd>Online</dd></div>
          <div class="row"><dt>Server</dt><dd>{values["server_name"]}</dd></div>
          <div class="row">
            <dt>Service identity</dt><dd>{values["service_npub"]}</dd>
          </div>
          <div class="row">
            <dt>FIPS IPv6 address</dt><dd>{values["service_fips_ipv6_address"]}</dd>
          </div>
          <div class="row">
            <dt>Supported BUDs</dt><dd>{values["supported_buds"]}</dd>
          </div>
          <div class="row"><dt>Maximum blob</dt><dd>{values["max_blob_size"]}</dd></div>
        </dl>
      </section>
      <section class="panel">
        <h2>What this server provides</h2>
        <ul class="features">
          <li>Content-addressed storage</li><li>Exact byte preservation</li>
          <li>Nostr-authorized uploads</li><li>Owner-scoped deletion</li>
          <li>Range requests</li><li>Local continuity</li>
        </ul>
      </section>
    </div>
    <aside class="about">
      Grove stores encrypted blobs as opaque bytes and keeps ownership policy
      at the protocol boundary. Applications such as Acorn can preserve private
      records locally while retaining standard Blossom interoperability.
    </aside>
    <nav class="links" aria-label="Server resources">
      <a href="/health">Health</a><a href="/docs">API documentation</a>
      <a href="https://trbouma.github.io/grove/">About Grove</a>
      <span class="version">Grove {values["version"]}</span>
    </nav>
  </main>
  <script>
    const button = document.getElementById("copy-server");
    button.addEventListener("click", async () => {{
      try {{
        const serverUrl = document.getElementById("server-url").textContent;
        await navigator.clipboard.writeText(serverUrl);
        button.textContent = "Copied";
      }} catch (_error) {{ button.textContent = "Select URL to copy"; }}
      window.setTimeout(() => {{ button.textContent = "Copy server URL"; }}, 1800);
    }});
  </script>
</body>
</html>"""


def _format_size(size: int) -> str:
    mebibyte = 1024 * 1024
    if size % mebibyte == 0:
        return f"{size // mebibyte} MiB"
    return f"{size:,} bytes"
