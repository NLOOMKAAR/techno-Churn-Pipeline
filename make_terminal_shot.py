import sys, html, json, subprocess
from pathlib import Path

def render(txt_path, out_png, base_url="http://localhost:8000"):
    lines = Path(txt_path).read_text().splitlines()
    method_line = lines[0]
    status_line = lines[1]
    status_code = status_line.split(":")[1].strip()
    body = "\n".join(lines[3:])
    ok = status_code.startswith("2")
    color = "#4ec9b0" if ok else "#f48771"
    esc_body = html.escape(body)
    esc_method = html.escape(method_line)
    tmpl = f"""
    <html><head><meta charset="utf-8"><style>
      body {{ margin:0; background:#1e1e1e; font-family:'Courier New',monospace; }}
      .win {{ border-radius:10px; overflow:hidden; box-shadow:0 4px 18px rgba(0,0,0,.5); }}
      .bar {{ background:#323233; padding:9px 14px; display:flex; align-items:center; }}
      .dot {{ width:11px; height:11px; border-radius:50%; margin-right:7px; display:inline-block; }}
      .r {{background:#ff5f56;}} .y {{background:#ffbd2e;}} .g {{background:#27c93f;}}
      .title {{ color:#ccc; font-size:12px; margin-left:10px; }}
      .body {{ padding:16px 18px; color:#d4d4d4; font-size:14px; line-height:1.55; }}
      .req {{ color:#569cd6; font-weight:bold; }}
      .status {{ color:{color}; font-weight:bold; }}
      pre {{ margin:6px 0 0 0; white-space:pre-wrap; color:#ce9178; }}
    </style></head>
    <body>
      <div class="win">
        <div class="bar"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
          <span class="title">curl - Telco Churn API test - {base_url}</span></div>
        <div class="body">
          <div class="req">$ curl -i {base_url}{esc_method.split(' ',1)[1] if ' ' in esc_method else ''}</div>
          <div class="status">HTTP/1.1 {status_code}</div>
          <pre>{esc_body}</pre>
        </div>
      </div>
    </body></html>
    """
    tmp_html = Path("/tmp/_shot.html")
    tmp_html.write_text(tmpl)
    subprocess.run(["wkhtmltoimage", "--width", "760", "--quality", "92",
                     str(tmp_html), str(out_png)], check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
