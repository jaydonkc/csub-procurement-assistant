"""Small Lambda-hosted fallback UI.

The standalone Vite application is the primary frontend. This page remains for
direct Lambda smoke tests and rollback access.
"""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CSUB Procurement Assistant</title>
  <style>
    :root{color-scheme:light;--navy:#102a43;--blue:#1565c0;--gold:#f5b700;--ink:#1f2933;--muted:#627d98;--line:#d9e2ec;--bg:#f5f8fb;--card:#fff}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    header{background:var(--navy);color:#fff;padding:18px 24px;border-bottom:4px solid var(--gold)}header h1{font-size:21px;margin:0}header p{margin:3px 0 0;color:#d9e2ec;font-size:13px}
    main{width:min(980px,100%);margin:0 auto;padding:22px;display:grid;grid-template-columns:250px 1fr;gap:18px;min-height:calc(100vh - 88px)}
    aside,.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 24px rgba(16,42,67,.06)}aside{padding:18px;align-self:start}aside h2{font-size:14px;margin:0 0 10px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
    .roles,.starters{display:grid;gap:8px}.role,.starter{border:1px solid var(--line);background:#fff;border-radius:9px;padding:10px;text-align:left;cursor:pointer;color:var(--ink)}.role.active{border-color:var(--blue);background:#eaf4ff;color:#0b4f8a;font-weight:650}.starter:hover,.role:hover{border-color:var(--blue)}
    .notice{margin-top:16px;padding:10px;border-radius:8px;background:#fff8dd;color:#664d03;font-size:12px}.panel{display:flex;flex-direction:column;min-height:640px;overflow:hidden}.messages{padding:20px;display:flex;flex:1;flex-direction:column;gap:14px;overflow:auto}
    .msg{max-width:85%;padding:12px 14px;border-radius:12px;white-space:pre-wrap}.assistant{background:#edf2f7;align-self:flex-start}.user{background:var(--blue);color:#fff;align-self:flex-end}.sources{margin-top:8px;border-top:1px solid var(--line);padding-top:8px;font-size:12px;color:var(--muted)}.source{margin:4px 0}
    form{display:flex;gap:10px;padding:14px;border-top:1px solid var(--line);background:#fff}textarea{flex:1;resize:none;min-height:48px;max-height:140px;border:1px solid #bcccdc;border-radius:10px;padding:12px;font:inherit}button[type=submit]{border:0;border-radius:10px;background:var(--blue);color:#fff;font-weight:700;padding:0 20px;cursor:pointer}button:disabled{opacity:.5;cursor:wait}
    @media(max-width:760px){main{grid-template-columns:1fr;padding:12px}.panel{min-height:620px}aside{order:2}.msg{max-width:94%}}
  </style>
</head>
<body>
  <header><h1>CSUB Procurement Assistant</h1><p>Public guidance · source-grounded answers · no system transactions</p></header>
  <main>
    <aside>
      <h2>Your role</h2>
      <div class="roles">
        <button class="role" data-role="requester">Faculty / staff requester</button>
        <button class="role" data-role="vendor">Vendor / supplier</button>
        <button class="role" data-role="internal_staff">Internal support staff</button>
      </div>
      <h2 style="margin-top:20px">Guided starts</h2>
      <div class="starters">
        <button class="starter">I need to buy software or a subscription.</button>
        <button class="starter">I need help with a new supplier.</button>
        <button class="starter">How do I create or change a requisition?</button>
        <button class="starter">I need invoice or payment guidance.</button>
      </div>
      <div class="notice">This assistant cannot submit, approve, edit, or look up live transactions. Choosing a role changes guidance wording but does not unlock internal procedures.</div>
    </aside>
    <section class="panel">
      <div id="messages" class="messages"><div class="msg assistant">Choose your role, then describe what you are trying to accomplish. I’ll ask for missing procurement context and provide a source-backed path.</div></div>
      <form id="chat"><textarea id="input" maxlength="4000" placeholder="Ask a procurement question…" required></textarea><button id="send" type="submit">Send</button></form>
    </section>
  </main>
  <script>
    let role="",history=[];const messages=document.getElementById("messages"),input=document.getElementById("input"),send=document.getElementById("send");
    document.querySelectorAll(".role").forEach(b=>b.onclick=()=>{document.querySelectorAll(".role").forEach(x=>x.classList.remove("active"));b.classList.add("active");role=b.dataset.role;input.focus()});
    document.querySelectorAll(".starter").forEach(b=>b.onclick=()=>{input.value=b.textContent;input.focus()});
    function add(text,kind,sources=[]){const box=document.createElement("div");box.className=`msg ${kind}`;box.textContent=text;if(sources.length){const wrap=document.createElement("div");wrap.className="sources";wrap.textContent="Sources";sources.forEach(s=>{const row=document.createElement("div");row.className="source";row.textContent=`• [${s.id}] ${s.path}${s.timestamp?` · ${s.timestamp}`:""}`;wrap.appendChild(row)});box.appendChild(wrap)}messages.appendChild(box);messages.scrollTop=messages.scrollHeight}
    document.getElementById("chat").onsubmit=async e=>{e.preventDefault();const message=input.value.trim();if(!message)return;if(!role){add("Please choose requester, vendor, or internal support staff first.","assistant");return}const prior=history.slice(-6);add(message,"user");history.push({role:"user",text:message});input.value="";send.disabled=true;
      try{const response=await fetch(location.href,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({message,role,history:prior})});const data=await response.json();if(!response.ok)throw new Error(data.error||"Request failed");add(data.answer,"assistant",data.sources||[]);history.push({role:"assistant",text:data.answer})}catch(err){add(`The service could not answer: ${err.message}`,"assistant")}finally{send.disabled=false;input.focus()}}
    input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();document.getElementById("chat").requestSubmit()}});
  </script>
</body>
</html>"""
