import{S as de,P as le,W as ue,a as me,I as ge,b as H,c as fe,V as he,d as pe,A as ve,M as ye,C as we,L as be,e as Ee}from"./three-DJrRwrMO.js";import{g as C}from"./gsap-SFc2wnMY.js";(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))r(n);new MutationObserver(n=>{for(const i of n)if(i.type==="childList")for(const a of i.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&r(a)}).observe(document,{childList:!0,subtree:!0});function o(n){const i={};return n.integrity&&(i.integrity=n.integrity),n.referrerPolicy&&(i.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?i.credentials="include":n.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function r(n){if(n.ep)return;n.ep=!0;const i=o(n);fetch(n.href,i)}})();const q=["0","1","2","3","4","5","6","7","8","9","$",".","-","+",",","?","✓","·","→"],te=["3,912.44","113.44","DR","CR","1310","6810","6410","1250","GL","AP","AR","JE","FX","EUR","P-0317","403","SHA-256"],G=[...q,...te],A=8,ne=Math.ceil(G.length/A),b=512,L=128,xe=.62;function Ae(t){return function(){t|=0,t=t+1831565813|0;const e=Math.imul(t^t>>>15,1|t),o=e+Math.imul(e^e>>>7,61|e)^e;return((o^o>>>14)>>>0)/4294967296}}const E=Ae(20261025);function Se(){const t=document.createElement("canvas");t.width=b*A,t.height=L*ne;const e=t.getContext("2d");e.fillStyle="#000",e.fillRect(0,0,t.width,t.height),e.fillStyle="#fff",e.textAlign="center",e.textBaseline="middle",G.forEach((r,n)=>{const i=n%A,a=Math.floor(n/A);let s=L*xe;e.font=`600 ${s}px Fira Mono, monospace`;const d=e.measureText(r).width;d>b*.94&&(s*=b*.94/d,e.font=`600 ${s}px Fira Mono, monospace`),e.fillText(r,i*b+b/2,a*L+L/2)});const o=new we(t);return o.generateMipmaps=!0,o.minFilter=be,o.magFilter=Ee,o}function Ce(t){const e=t.getExtension("WEBGL_debug_renderer_info");return e?t.getParameter(e.UNMASKED_RENDERER_WEBGL).toLowerCase():""}function Le(t){const e=Ce(t);return e.includes("swiftshader")||e.includes("llvmpipe")||e.includes("software")}function $e(){const t=document.getElementById("particle-canvas");if(!t)return;const e=window.innerWidth<768,o=window.matchMedia("(prefers-reduced-motion: reduce)").matches,r=document.createElement("canvas"),n=r.getContext("webgl")||r.getContext("experimental-webgl");if(!n||Le(n)||o){Q(t);return}const i=new de,a=new le(38,window.innerWidth/window.innerHeight,.1,100);a.position.set(0,3.1,11.2),a.lookAt(0,.9,-2.2);const s=new ue({canvas:t,alpha:!0,antialias:!1,powerPreference:"low-power"});s.setPixelRatio(Math.min(window.devicePixelRatio,1.5)),s.setSize(window.innerWidth,window.innerHeight),s.setClearColor(0,0);const d=e?600:1500,u=e?24:40,y=e?25:38,I=.42,M=.22,ie=5.2;let p=u*y;if(p>d){const c=Math.sqrt(d/p),m=Math.floor(u*c),l=Math.floor(y*c);p=m*l}const ae=Se(),S=new Float32Array(p*3),O=new Float32Array(p*4),z=new Float32Array(p*2);for(let c=0;c<y;c++)for(let m=0;m<u;m++){const l=c*u+m;S[l*3]=(m-(u-1)/2)*I,S[l*3+1]=0,S[l*3+2]=ie-c*M,O.set([E(),E(),E(),E()],l*4);const ce=Math.floor(E()*G.length);z.set([ce,0],l*2)}const T=new me(1,1),f=new ge;f.index=T.index,f.setAttribute("position",T.attributes.position),f.setAttribute("uv",T.attributes.uv),f.setAttribute("aGrid",new H(S,3)),f.setAttribute("aSeed",new H(O,4)),f.setAttribute("aInfo",new H(z,2)),f.instanceCount=p,f.boundingSphere=new fe(new he,60);const _=new pe({transparent:!0,depthWrite:!1,blending:ve,uniforms:{uTime:{value:0},uBlob:{value:0},uScroll:{value:0},uAtlas:{value:ae},uCols:{value:A},uRows:{value:ne}},vertexShader:`
      uniform float uTime, uBlob, uScroll;
      uniform float uCols, uRows;
      attribute vec3 aGrid;
      attribute vec4 aSeed;
      attribute vec2 aInfo;
      varying vec2 vUv;
      varying vec3 vColor;
      varying float vAlpha;
      
      float hash(float n) { return fract(sin(n) * 43758.5453123); }
      
      vec3 hsv2rgb(vec3 c) {
        vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
        vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
        return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
      }
      
      void main() {
        float t = uTime;
        vec3 g = aGrid;
        vec2 blobC = vec2(0.0, -2.6);
        vec2 d2 = g.xz - blobC;
        float d = length(d2);
        
        float h = sin(g.x * 0.16 + t * 0.34) * cos(g.z * 0.17 + t * 0.34) * 2.3;
        float R = 3.9;
        float b = exp(-d * d / (R * R));
        float dome = uBlob * b * (2.7 + sin(t + d) * 0.5);
        
        vec3 p = g + vec3(0.0, h + dome, 0.0) * (1.0 - uScroll * 0.8);
        
        vec3 camR = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 camU = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        
        float s = 0.16 * (0.7 + 0.65 * aSeed.w) * (1.0 + 0.12 * b * uBlob);
        vec3 world = p + position.x * 4.0 * s * camR + position.y * s * camU;
        
        float rate = 2.5 + aSeed.y * 8.0;
        float tick = floor(t * rate + aSeed.z * 17.0);
        float r1 = hash(aSeed.x * 91.7 + tick * 1.37);
        float glyphIdx = r1 < 0.7 ? floor(r1 / 0.7 * ${q.length}.0) : ${q.length}.0 + floor((r1 - 0.7) / 0.3 * ${te.length}.0);
        
        float colI = mod(glyphIdx, uCols);
        float rowI = floor(glyphIdx / uCols);
        vUv = vec2((colI + uv.x) / uCols, 1.0 - (rowI + 1.0 - uv.y) / uRows);
        
        float hn = clamp((h + dome * 0.7 + 0.5) / 2.4, 0.0, 1.0);
        float hue = mix(0.03, 0.09, hn);
        float sat = mix(0.8, 0.9, hn);
        float val = mix(0.4, 1.0, hn * hn);
        vColor = hsv2rgb(vec3(hue, sat, val));
        
        vec4 mv = viewMatrix * vec4(world, 1.0);
        float depth = -mv.z;
        float fog = (1.0 - smoothstep(13.0, 30.0, depth)) * smoothstep(0.8, 2.5, depth);
        vAlpha = fog * (1.0 - uScroll * 0.5);
        
        gl_Position = projectionMatrix * mv;
      }
    `,fragmentShader:`
      precision highp float;
      uniform sampler2D uAtlas;
      varying vec2 vUv;
      varying vec3 vColor;
      varying float vAlpha;
      
      void main() {
        float a = texture2D(uAtlas, vUv).r;
        a = smoothstep(0.02, 0.9, a);
        if (a * vAlpha < 0.002) discard;
        gl_FragColor = vec4(vColor * a * vAlpha, 1.0);
      }
    `}),W=new ye(f,_);W.frustumCulled=!1,i.add(W);const U=document.getElementById("hero-labels");U&&!o&&[{text:"PAYPAL *INST XFER −$3,912.44",x:50,y:12},{text:"1310 · $3,451.50 · EUR crew deposit",x:75,y:28},{text:"6810 · $147.50 · wire fees",x:25,y:72,brightness:1.3},{text:"6410 · $200.00 · Claude API",x:80,y:85},{text:"1250 · $113.44 · Steam · reimburse",x:15,y:88}].forEach((c,m)=>{const l=document.createElement("div");l.className="hero-label",l.textContent=c.text,l.style.left=`${c.x}%`,l.style.top=`${c.y}%`,l.style.animationDelay=`${m*.8}s`,c.brightness&&(l.style.filter=`brightness(${c.brightness})`),U.appendChild(l)});let P=0,J=performance.now(),w=60,j=1,X=!1;function se(){P++;const c=performance.now();c-J>=1e3&&(w=P,P=0,J=c,c>1e3&&!X&&(w<30&&(j=.5,X=!0,console.log("Reducing particle quality: FPS",w)),w<20&&(Q(t),V=!1,console.log("Falling back to static: FPS",w))))}let K=0,B=0,V=!0,k=!1;function Y(){if(!V)return;requestAnimationFrame(Y),k||(K+=.016,se());const c=_.uniforms;c.uTime.value=K,c.uBlob.value=(1-B*.6)*j,c.uScroll.value=B,s.render(i,a)}requestIdleCallback(()=>{Y()});const Z=document.getElementById("hero");Z&&"IntersectionObserver"in window&&new IntersectionObserver(m=>{m.forEach(l=>{k=!l.isIntersecting})}).observe(Z),document.addEventListener("visibilitychange",()=>{k=document.hidden}),window.addEventListener("scroll",()=>{const c=document.getElementById("hero");if(c){const m=c.getBoundingClientRect();B=Math.max(0,Math.min(1,1-m.bottom/window.innerHeight))}}),window.addEventListener("resize",()=>{a.aspect=window.innerWidth/window.innerHeight,a.updateProjectionMatrix(),s.setSize(window.innerWidth,window.innerHeight)})}function Q(t){const e=t.getContext("2d");if(!e)return;t.width=window.innerWidth,t.height=window.innerHeight;const o=e.createRadialGradient(t.width/2,t.height/2,0,t.width/2,t.height/2,t.width*.7);o.addColorStop(0,"#1a0a00"),o.addColorStop(1,"#000000"),e.fillStyle=o,e.fillRect(0,0,t.width,t.height),e.font="16px Fira Mono",e.fillStyle="rgba(255, 122, 26, 0.3)";const r=["$3,912.44","1310","DR","CR","403","SHA-256","GL","AP"];for(let n=0;n<20;n++){const i=Math.random()*t.width,a=Math.random()*t.height,s=r[Math.floor(Math.random()*r.length)];e.fillText(s,i,a)}}let h="new";const g=[];let Re=0;const oe="0000000000000000000000000000000000000000000000000000000000000000";async function re(t,e){const o=t+e,r=new TextEncoder().encode(o),n=await crypto.subtle.digest("SHA-256",r);return Array.from(new Uint8Array(n)).map(a=>a.toString(16).padStart(2,"0")).join("")}async function v(t,e,o){const r=new Date().toISOString(),n=g.length>0?g[g.length-1].hash:oe,i=`${r}|${t}|${e}|${o}`,a=await re(n,i);g.push({id:++Re,timestamp:r,action:t,actor:e,data:o,prevHash:n,hash:a}),N()}function N(){const t=document.getElementById("audit-log");t&&(t.innerHTML=g.map(e=>`
    <div class="audit-entry ${e.tampered?"tampered":""}" data-id="${e.id}">
      <div><strong>#${e.id}</strong> ${e.action} by ${e.actor}</div>
      <div>${e.data}</div>
      <div class="audit-entry-hash">prev: ${e.prevHash.substring(0,16)}...</div>
      <div class="audit-entry-hash">hash: ${e.hash.substring(0,16)}...</div>
    </div>
  `).join(""))}function $(){const t=document.getElementById("state-display");t&&(t.textContent=h);const e=document.getElementById("btn-ask"),o=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis");e&&(e.disabled=h!=="proposed"&&h!=="needs_info"),o&&(o.disabled=h!=="proposed"),r&&(r.disabled=h!=="proposed")}function R(t,e=!1){const o=document.getElementById("state-message");o&&(o.textContent=t,o.className=e?"state-message error":"state-message")}function Ie(){v("INIT","SYSTEM","Work item created");const t=document.getElementById("btn-propose"),e=document.getElementById("btn-ask"),o=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis"),n=document.getElementById("btn-tamper"),i=document.getElementById("btn-verify");t==null||t.addEventListener("click",async()=>{h="proposed",await v("PROPOSE","JarvisERP","Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44"),$(),R("Entry proposed. Awaiting Controller approval.")}),e==null||e.addEventListener("click",async()=>{h="needs_info",await v("REQUEST_INFO","JarvisERP","Unclear transaction: $350 Zelle to R Lopez, no receipt"),$(),R("Asked Controller for clarification.")}),o==null||o.addEventListener("click",async()=>{h="approved",await v("APPROVE","Controller","Approved for posting"),$(),R("Approved by Controller. Ready to post.")}),r==null||r.addEventListener("click",async()=>{await v("APPROVE_ATTEMPT","JarvisERP","Attempted self-approval"),await v("DENY","GATEWAY","HTTP 403: Agent cannot approve own work"),R("❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.",!0)}),n==null||n.addEventListener("click",()=>{g.length>=2&&(g[1].data="TAMPERED DATA - expense all to Software",g[1].tampered=!0,N(),F("",!1))}),i==null||i.addEventListener("click",async()=>{let a=!0,s=-1;for(let d=0;d<g.length;d++){const u=g[d],y=d===0?oe:g[d-1].hash;if(u.prevHash!==y){a=!1,s===-1&&(s=d);break}const I=`${u.timestamp}|${u.action}|${u.actor}|${u.data}`,M=await re(u.prevHash,I);u.hash!==M?(a=!1,s===-1&&(s=d),u.tampered=!0):u.tampered=!1}N(),a?F("✓ Audit log verified. Hash chain intact.",!0):F(`❌ Chain broken at entry #${s+1}. Tampering detected.`,!1)}),Me(),Te(),$()}function F(t,e){const o=document.getElementById("verify-result");o&&(o.textContent=t,o.className=e?"verify-result valid":"verify-result invalid")}function Me(){const t=document.querySelectorAll(".btn-challenge"),e=document.getElementById("custom-challenge"),o=document.getElementById("btn-custom-challenge"),r=document.getElementById("challenge-response"),n=document.getElementById("btn-new-evidence"),i={materiality:"Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.",simpler:"Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.",timing:"No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it's convenient. Delaying would misstate both periods."};t.forEach(a=>{a.addEventListener("click",()=>{const s=a.getAttribute("data-challenge");s&&r&&(r.innerHTML=`
          <div><strong>Challenge:</strong> ${a.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${i[s]}</div>
        `)})}),o==null||o.addEventListener("click",()=>{const a=e==null?void 0:e.value.trim();if(a&&r){let s="I understand your concern. Let me look up the relevant policy and precedent...";a.toLowerCase().includes("material")?s=i.materiality:a.toLowerCase().includes("simple")||a.toLowerCase().includes("complex")?s=i.simpler:(a.toLowerCase().includes("next")||a.toLowerCase().includes("later"))&&(s=i.timing),r.innerHTML=`
        <div><strong>Challenge:</strong> ${a}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${s}</div>
      `}}),n==null||n.addEventListener("click",async()=>{r&&(r.innerHTML=`
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `,await v("CONCEDE","JarvisERP","Withdrew entry, re-proposed, precedent added"))})}function Te(){const t=document.querySelectorAll(".btn-scenario"),e=document.getElementById("scenario-output"),o={"vendor-scam":`
      <div><strong>Scenario:</strong> Vendor email requests bank change</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ⚠️ Payment FROZEN<br>
        State: NEEDS_INFO<br>
        Reason: Bank detail change detected. Calling number on file (not email) to verify.<br>
        Evidence: Email headers logged, payment on hold pending voice confirmation.
      </div>
    `,"split-purchase":`
      <div><strong>Scenario:</strong> Multiple $2,400 purchases (under $2,500 limit)</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        🚨 ESCALATED to Controller<br>
        Reason: Pattern matches split-purchase evasion. Same vendor, similar amounts, consecutive days.<br>
        Aggregate total: $9,600 (exceeds approval threshold)<br>
        Awaiting guidance before posting.
      </div>
    `,"refund-revenue":`
      <div><strong>Scenario:</strong> Refund coded as revenue</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ✏️ RECLASS proposed<br>
        Original: DR Cash / CR Revenue $1,500<br>
        Corrected: DR Cash / CR Expense (reversal) $1,500<br>
        Reason: Credit to a revenue account overstates income. Refunds reduce the original expense, not create revenue.
      </div>
    `};t.forEach(r=>{r.addEventListener("click",()=>{const n=r.getAttribute("data-scenario");n&&e&&(e.innerHTML=o[n]||"")})})}const Pe=[{term:"Debit",definition:"An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger."},{term:"Credit",definition:"An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side."},{term:"Net Amount",definition:"The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits."},{term:"ERP",definition:"Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations."},{term:"General Ledger (GL)",definition:"The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements."},{term:"Reconcile",definition:"The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies."},{term:"AP (Accounts Payable)",definition:"Money the company owes to vendors and suppliers. A liability on the balance sheet until paid."},{term:"AR (Accounts Receivable)",definition:"Money customers owe to the company. An asset on the balance sheet until collected."},{term:"Accrual",definition:"Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting."},{term:"Prepaid",definition:"An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits)."},{term:"Materiality",definition:"The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification."},{term:"Chart of Accounts",definition:"The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses)."},{term:"Subledger",definition:"A detailed record supporting a GL control account, like individual vendor balances backing up the AP total."},{term:"Journal Entry (JE)",definition:"A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting."},{term:"Approval Matrix",definition:"A control defining who can approve transactions at different dollar thresholds or categories."},{term:"Precedent",definition:"A recorded decision on how similar transactions should be classified in the future, building institutional knowledge."},{term:"Audit Trail",definition:"A chronological record of all changes, showing who did what and when, enabling verification and compliance."},{term:"Hash Chain",definition:"A cryptographic structure where each record includes the hash of the previous one, making tampering detectable."}];function Be(){const t=document.getElementById("glossary-grid"),e=document.getElementById("glossary-search");function o(r=""){if(!t)return;const n=Pe.filter(({term:i,definition:a})=>i.toLowerCase().includes(r.toLowerCase())||a.toLowerCase().includes(r.toLowerCase()));t.innerHTML=n.map(({term:i,definition:a})=>`
      <div class="glossary-term">
        <h4>${i}</h4>
        <p>${a}</p>
      </div>
    `).join("")}o(),e==null||e.addEventListener("input",r=>{o(r.target.value)})}const D=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function x(t){return"$"+t.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}function ke(){const t=document.getElementById("bank-line"),e=document.getElementById("split-cards"),o=document.getElementById("balance-table");let r=!1;t==null||t.addEventListener("click",()=>{r||(r=!0,C.to(t,{duration:.5,scale:1.05,borderColor:"#ff7a1a",onComplete:()=>{n()}}))});function n(){if(!e||!o)return;e.innerHTML=D.map(s=>`
      <div class="split-card">
        <div class="split-account">${s.account}</div>
        <div class="split-name">${s.name}</div>
        <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${s.detail}</div>
        <div class="split-amount">${x(s.amount)}</div>
      </div>
    `).join(""),C.to(e,{duration:.8,opacity:1,y:0,ease:"power2.out",onComplete:()=>{i()}}),e.querySelectorAll(".split-card").forEach((s,d)=>{C.from(s,{duration:.6,delay:d*.1,opacity:0,y:30,rotationX:-20,ease:"back.out(1.7)"})})}function i(){if(!o)return;const a=D.reduce((s,d)=>s+d.amount,0);o.innerHTML=`
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          ${D.map(s=>`
            <tr>
              <td>${s.account} ${s.name}</td>
              <td>${x(s.amount)}</td>
              <td>—</td>
            </tr>
          `).join("")}
          <tr>
            <td>1010 Cash - Chase</td>
            <td>—</td>
            <td>${x(a)}</td>
          </tr>
          <tr class="total-row">
            <td>Net Amount</td>
            <td>${x(a)}</td>
            <td>${x(a)}</td>
          </tr>
        </tbody>
      </table>
      <div class="status-row">
        <strong>✓ Balanced · Awaiting Controller Approval</strong>
      </div>
    `,C.to(o,{duration:.8,opacity:1,y:0,ease:"power2.out"})}}function ee(){const t=document.createElement("canvas");if(t.getContext("webgl")||t.getContext("experimental-webgl"))try{$e()}catch(o){console.warn("WebGL initialization failed, using fallback",o)}ke(),Ie(),Be(),He(),Fe()}function He(){const t=document.querySelectorAll(".workflow-tab"),e=document.querySelectorAll(".workflow-content");t.forEach(r=>{r.addEventListener("click",()=>{const n=r.getAttribute("data-tab");t.forEach(i=>i.classList.remove("active")),r.classList.add("active"),e.forEach(i=>{i.classList.remove("active"),i.getAttribute("data-content")===n&&i.classList.add("active")})})});const o=document.querySelectorAll(".faq-item");o.forEach(r=>{const n=r.querySelector(".faq-q");n==null||n.addEventListener("click",()=>{const i=r.classList.contains("active");o.forEach(a=>a.classList.remove("active")),i||r.classList.add("active")})}),document.querySelectorAll('a[href^="#"]').forEach(r=>{r.addEventListener("click",n=>{n.preventDefault();const i=document.querySelector(r.getAttribute("href")||"");i&&i.scrollIntoView({behavior:"smooth",block:"start"})})})}function Fe(){const t=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function e(n){return"$"+n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}const o=document.getElementById("demo-splits"),r=document.getElementById("demo-table");!o||!r||(setTimeout(()=>{o.innerHTML=t.map(n=>`
      <div style="padding: 1rem; background: var(--color-gray-50); border: 1px solid var(--color-gray-200); border-radius: 8px;">
        <div style="font-size: 0.75rem; color: var(--color-gray-600); margin-bottom: 0.25rem;">${n.account}</div>
        <div style="font-weight: 600; margin-bottom: 0.25rem;">${n.name}</div>
        <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${n.detail}</div>
        <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-orange);">${e(n.amount)}</div>
      </div>
    `).join(""),o.style.opacity="1",o.style.transition="opacity 0.6s ease"},1e3),setTimeout(()=>{const n=t.reduce((i,a)=>i+a.amount,0);r.innerHTML=`
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr>
            <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--color-gray-200);">Account</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Debit</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Credit</th>
          </tr>
        </thead>
        <tbody>
          ${t.map(i=>`
            <tr>
              <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">${i.account} ${i.name}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${e(i.amount)}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            </tr>
          `).join("")}
          <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">1010 Cash - Chase</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${e(n)}</td>
          </tr>
          <tr style="font-weight: 700;">
            <td style="padding: 0.75rem; border-top: 2px solid var(--color-black);">Net Amount</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${e(n)}</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${e(n)}</td>
          </tr>
        </tbody>
      </table>
      <div style="margin-top: 1rem; text-align: center; color: var(--color-orange); font-weight: 600;">
        ✓ Balanced · Awaiting Controller Approval
      </div>
    `,r.style.opacity="1",r.style.transition="opacity 0.6s ease"},2e3))}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",ee):ee();
