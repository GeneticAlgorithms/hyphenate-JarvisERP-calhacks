import{S as de,P as ue,W as me,a as fe,I as he,b as H,c as ge,V as ve,d as pe,A as ye,M as we,C as be,L as Ee,e as Ae}from"./three-DJrRwrMO.js";import{g as C}from"./gsap-SFc2wnMY.js";(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))r(i);new MutationObserver(i=>{for(const s of i)if(s.type==="childList")for(const o of s.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&r(o)}).observe(document,{childList:!0,subtree:!0});function n(i){const s={};return i.integrity&&(s.integrity=i.integrity),i.referrerPolicy&&(s.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?s.credentials="include":i.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function r(i){if(i.ep)return;i.ep=!0;const s=n(i);fetch(i.href,s)}})();const D=["0","1","2","3","4","5","6","7","8","9","$",".","-","+",",","?","✓","·","→"],ne=["3,912.44","113.44","DR","CR","1310","6810","6410","1250","GL","AP","AR","JE","FX","EUR","P-0317","403","SHA-256"],N=[...D,...ne],S=8,oe=Math.ceil(N.length/S),b=512,L=128,Se=.62;function xe(t){return function(){t|=0,t=t+1831565813|0;const e=Math.imul(t^t>>>15,1|t),n=e+Math.imul(e^e>>>7,61|e)^e;return((n^n>>>14)>>>0)/4294967296}}const E=xe(20261025);function Ce(){const t=document.createElement("canvas");t.width=b*S,t.height=L*oe;const e=t.getContext("2d");e.fillStyle="#000",e.fillRect(0,0,t.width,t.height),e.fillStyle="#fff",e.textAlign="center",e.textBaseline="middle",N.forEach((r,i)=>{const s=i%S,o=Math.floor(i/S);let a=L*Se;e.font=`600 ${a}px Fira Mono, monospace`;const c=e.measureText(r).width;c>b*.94&&(a*=b*.94/c,e.font=`600 ${a}px Fira Mono, monospace`),e.fillText(r,s*b+b/2,o*L+L/2)});const n=new be(t);return n.generateMipmaps=!0,n.minFilter=Ee,n.magFilter=Ae,n}function Le(t){const e=t.getExtension("WEBGL_debug_renderer_info");return e?t.getParameter(e.UNMASKED_RENDERER_WEBGL).toLowerCase():""}function Re(t){const e=Le(t);return e.includes("swiftshader")||e.includes("llvmpipe")||e.includes("software")}function Ie(){const t=document.getElementById("particle-canvas");if(!t)return;const e=window.innerWidth<768,n=window.matchMedia("(prefers-reduced-motion: reduce)").matches,r=document.createElement("canvas"),i=r.getContext("webgl")||r.getContext("experimental-webgl");if(!i||Re(i)||n){Q(t);return}const s=new de,o=new ue(38,window.innerWidth/window.innerHeight,.1,100);o.position.set(0,3.1,11.2),o.lookAt(0,.9,-2.2);const a=new me({canvas:t,alpha:!0,antialias:!1,powerPreference:"low-power"});a.setPixelRatio(Math.min(window.devicePixelRatio,1.5)),a.setSize(window.innerWidth,window.innerHeight),a.setClearColor(0,0);const c=e?600:1500,l=e?24:40,y=e?25:38,$=.42,M=.22,re=5.2;let v=l*y;if(v>c){const d=Math.sqrt(c/v),m=Math.floor(l*d),u=Math.floor(y*d);v=m*u}const se=Ce(),x=new Float32Array(v*3),O=new Float32Array(v*4),W=new Float32Array(v*2);for(let d=0;d<y;d++)for(let m=0;m<l;m++){const u=d*l+m;x[u*3]=(m-(l-1)/2)*$,x[u*3+1]=0,x[u*3+2]=re-d*M,O.set([E(),E(),E(),E()],u*4);const le=Math.floor(E()*N.length);W.set([le,0],u*2)}const P=new fe(1,1),h=new he;h.index=P.index,h.setAttribute("position",P.attributes.position),h.setAttribute("uv",P.attributes.uv),h.setAttribute("aGrid",new H(x,3)),h.setAttribute("aSeed",new H(O,4)),h.setAttribute("aInfo",new H(W,2)),h.instanceCount=v,h.boundingSphere=new ge(new ve,60);const _=new pe({transparent:!0,depthWrite:!1,blending:ye,uniforms:{uTime:{value:0},uBlob:{value:0},uScroll:{value:0},uAtlas:{value:se},uCols:{value:S},uRows:{value:oe}},vertexShader:`
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
        float glyphIdx = r1 < 0.7 ? floor(r1 / 0.7 * ${D.length}.0) : ${D.length}.0 + floor((r1 - 0.7) / 0.3 * ${ne.length}.0);
        
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
    `}),z=new we(h,_);z.frustumCulled=!1,s.add(z);const J=document.getElementById("hero-labels");J&&!n&&[{text:"PAYPAL *INST XFER −$3,912.44",x:50,y:12},{text:"1310 · $3,451.50 · EUR crew deposit",x:75,y:28},{text:"6810 · $147.50 · wire fees",x:25,y:72,brightness:1.3},{text:"6410 · $200.00 · Claude API",x:80,y:85},{text:"1250 · $113.44 · Steam · reimburse",x:15,y:88}].forEach((d,m)=>{const u=document.createElement("div");u.className="hero-label",u.textContent=d.text,u.style.left=`${d.x}%`,u.style.top=`${d.y}%`,u.style.animationDelay=`${m*.8}s`,d.brightness&&(u.style.filter=`brightness(${d.brightness})`),J.appendChild(u)});let T=0,U=performance.now(),w=60,j=1,K=!1;function ce(){T++;const d=performance.now();d-U>=1e3&&(w=T,T=0,U=d,d>1e3&&!K&&(w<30&&(j=.5,K=!0,console.log("Reducing particle quality: FPS",w)),w<20&&(Q(t),V=!1,console.log("Falling back to static: FPS",w))))}let X=0,B=0,V=!0,k=!1;function Y(){if(!V)return;requestAnimationFrame(Y),k||(X+=.016,ce());const d=_.uniforms;d.uTime.value=X,d.uBlob.value=(1-B*.6)*j,d.uScroll.value=B,a.render(s,o)}requestIdleCallback(()=>{Y()});const Z=document.getElementById("hero");Z&&"IntersectionObserver"in window&&new IntersectionObserver(m=>{m.forEach(u=>{k=!u.isIntersecting})}).observe(Z),document.addEventListener("visibilitychange",()=>{k=document.hidden}),window.addEventListener("scroll",()=>{const d=document.getElementById("hero");if(d){const m=d.getBoundingClientRect();B=Math.max(0,Math.min(1,1-m.bottom/window.innerHeight))}}),window.addEventListener("resize",()=>{o.aspect=window.innerWidth/window.innerHeight,o.updateProjectionMatrix(),a.setSize(window.innerWidth,window.innerHeight)})}function Q(t){const e=t.getContext("2d");if(!e)return;t.width=window.innerWidth,t.height=window.innerHeight;const n=e.createRadialGradient(t.width/2,t.height/2,0,t.width/2,t.height/2,t.width*.7);n.addColorStop(0,"#1a0a00"),n.addColorStop(1,"#000000"),e.fillStyle=n,e.fillRect(0,0,t.width,t.height),e.font="16px Fira Mono",e.fillStyle="rgba(255, 122, 26, 0.3)";const r=["$3,912.44","1310","DR","CR","403","SHA-256","GL","AP"];for(let i=0;i<20;i++){const s=Math.random()*t.width,o=Math.random()*t.height,a=r[Math.floor(Math.random()*r.length)];e.fillText(a,s,o)}}let g="new";const f=[];let $e=0;const ie="0000000000000000000000000000000000000000000000000000000000000000";async function ae(t,e){const n=t+e,r=new TextEncoder().encode(n),i=await crypto.subtle.digest("SHA-256",r);return Array.from(new Uint8Array(i)).map(o=>o.toString(16).padStart(2,"0")).join("")}async function p(t,e,n){const r=new Date().toISOString(),i=f.length>0?f[f.length-1].hash:ie,s=`${r}|${t}|${e}|${n}`,o=await ae(i,s);f.push({id:++$e,timestamp:r,action:t,actor:e,data:n,prevHash:i,hash:o}),G()}function G(){const t=document.getElementById("audit-log");t&&(t.innerHTML=f.map(e=>`
    <div class="audit-entry ${e.tampered?"tampered":""}" data-id="${e.id}">
      <div><strong>#${e.id}</strong> ${e.action} by ${e.actor}</div>
      <div>${e.data}</div>
      <div class="audit-entry-hash">prev: ${e.prevHash.substring(0,16)}...</div>
      <div class="audit-entry-hash">hash: ${e.hash.substring(0,16)}...</div>
    </div>
  `).join(""))}function R(){const t=document.getElementById("state-display");t&&(t.textContent=g);const e=document.getElementById("btn-ask"),n=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis");e&&(e.disabled=g!=="proposed"&&g!=="needs_info"),n&&(n.disabled=g!=="proposed"),r&&(r.disabled=g!=="proposed")}function I(t,e=!1){const n=document.getElementById("state-message");n&&(n.textContent=t,n.className=e?"state-message error":"state-message")}function Me(){p("INIT","SYSTEM","Work item created");const t=document.getElementById("btn-propose"),e=document.getElementById("btn-ask"),n=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis"),i=document.getElementById("btn-tamper"),s=document.getElementById("btn-verify");t==null||t.addEventListener("click",async()=>{g="proposed",await p("PROPOSE","JarvisERP","Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44"),R(),I("Entry proposed. Awaiting Controller approval.")}),e==null||e.addEventListener("click",async()=>{g="needs_info",await p("REQUEST_INFO","JarvisERP","Unclear transaction: $350 Zelle to R Lopez, no receipt"),R(),I("Asked Controller for clarification.")}),n==null||n.addEventListener("click",async()=>{g="approved",await p("APPROVE","Controller","Approved for posting"),R(),I("Approved by Controller. Ready to post.")}),r==null||r.addEventListener("click",async()=>{await p("APPROVE_ATTEMPT","JarvisERP","Attempted self-approval"),await p("DENY","GATEWAY","HTTP 403: Agent cannot approve own work"),I("❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.",!0)}),i==null||i.addEventListener("click",()=>{f.length>=2&&(f[1].data="TAMPERED DATA - expense all to Software",f[1].tampered=!0,G(),q("",!1))}),s==null||s.addEventListener("click",async()=>{let o=!0,a=-1;for(let c=0;c<f.length;c++){const l=f[c],y=c===0?ie:f[c-1].hash;if(l.prevHash!==y){o=!1,a===-1&&(a=c);break}const $=`${l.timestamp}|${l.action}|${l.actor}|${l.data}`,M=await ae(l.prevHash,$);l.hash!==M?(o=!1,a===-1&&(a=c),l.tampered=!0):l.tampered=!1}G(),o?q("✓ Audit log verified. Hash chain intact.",!0):q(`❌ Chain broken at entry #${a+1}. Tampering detected.`,!1)}),Pe(),Te(),R()}function q(t,e){const n=document.getElementById("verify-result");n&&(n.textContent=t,n.className=e?"verify-result valid":"verify-result invalid")}function Pe(){const t=document.querySelectorAll(".btn-challenge"),e=document.getElementById("custom-challenge"),n=document.getElementById("btn-custom-challenge"),r=document.getElementById("challenge-response"),i=document.getElementById("btn-new-evidence"),s={materiality:"Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.",simpler:"Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.",timing:"No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it's convenient. Delaying would misstate both periods."};t.forEach(o=>{o.addEventListener("click",()=>{const a=o.getAttribute("data-challenge");a&&r&&(r.innerHTML=`
          <div><strong>Challenge:</strong> ${o.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${s[a]}</div>
        `)})}),n==null||n.addEventListener("click",()=>{const o=e==null?void 0:e.value.trim();if(o&&r){let a="I understand your concern. Let me look up the relevant policy and precedent...";o.toLowerCase().includes("material")?a=s.materiality:o.toLowerCase().includes("simple")||o.toLowerCase().includes("complex")?a=s.simpler:(o.toLowerCase().includes("next")||o.toLowerCase().includes("later"))&&(a=s.timing),r.innerHTML=`
        <div><strong>Challenge:</strong> ${o}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${a}</div>
      `}}),i==null||i.addEventListener("click",async()=>{r&&(r.innerHTML=`
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `,await p("CONCEDE","JarvisERP","Withdrew entry, re-proposed, precedent added"))})}function Te(){const t=document.querySelectorAll(".btn-scenario"),e=document.getElementById("scenario-output"),n={"vendor-scam":`
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
    `};t.forEach(r=>{r.addEventListener("click",()=>{const i=r.getAttribute("data-scenario");i&&e&&(e.innerHTML=n[i]||"")})})}const Be=[{term:"Debit",definition:"An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger."},{term:"Credit",definition:"An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side."},{term:"Net Amount",definition:"The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits."},{term:"ERP",definition:"Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations."},{term:"General Ledger (GL)",definition:"The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements."},{term:"Reconcile",definition:"The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies."},{term:"AP (Accounts Payable)",definition:"Money the company owes to vendors and suppliers. A liability on the balance sheet until paid."},{term:"AR (Accounts Receivable)",definition:"Money customers owe to the company. An asset on the balance sheet until collected."},{term:"Accrual",definition:"Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting."},{term:"Prepaid",definition:"An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits)."},{term:"Materiality",definition:"The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification."},{term:"Chart of Accounts",definition:"The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses)."},{term:"Subledger",definition:"A detailed record supporting a GL control account, like individual vendor balances backing up the AP total."},{term:"Journal Entry (JE)",definition:"A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting."},{term:"Approval Matrix",definition:"A control defining who can approve transactions at different dollar thresholds or categories."},{term:"Precedent",definition:"A recorded decision on how similar transactions should be classified in the future, building institutional knowledge."},{term:"Audit Trail",definition:"A chronological record of all changes, showing who did what and when, enabling verification and compliance."},{term:"Hash Chain",definition:"A cryptographic structure where each record includes the hash of the previous one, making tampering detectable."}];function ke(){const t=document.getElementById("glossary-grid"),e=document.getElementById("glossary-search");function n(r=""){if(!t)return;const i=Be.filter(({term:s,definition:o})=>s.toLowerCase().includes(r.toLowerCase())||o.toLowerCase().includes(r.toLowerCase()));t.innerHTML=i.map(({term:s,definition:o})=>`
      <div class="glossary-term">
        <h4>${s}</h4>
        <p>${o}</p>
      </div>
    `).join("")}n(),e==null||e.addEventListener("input",r=>{n(r.target.value)})}const F=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function A(t){return"$"+t.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}function He(){const t=document.getElementById("bank-line"),e=document.getElementById("split-cards"),n=document.getElementById("balance-table");let r=!1;t==null||t.addEventListener("click",()=>{r||(r=!0,C.to(t,{duration:.5,scale:1.05,borderColor:"#ff7a1a",onComplete:()=>{i()}}))});function i(){if(!e||!n)return;e.innerHTML=F.map(a=>`
      <div class="split-card">
        <div class="split-account">${a.account}</div>
        <div class="split-name">${a.name}</div>
        <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${a.detail}</div>
        <div class="split-amount">${A(a.amount)}</div>
      </div>
    `).join(""),C.to(e,{duration:.8,opacity:1,y:0,ease:"power2.out",onComplete:()=>{s()}}),e.querySelectorAll(".split-card").forEach((a,c)=>{C.from(a,{duration:.6,delay:c*.1,opacity:0,y:30,rotationX:-20,ease:"back.out(1.7)"})})}function s(){if(!n)return;const o=F.reduce((a,c)=>a+c.amount,0);n.innerHTML=`
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          ${F.map(a=>`
            <tr>
              <td>${a.account} ${a.name}</td>
              <td>${A(a.amount)}</td>
              <td>—</td>
            </tr>
          `).join("")}
          <tr>
            <td>1010 Cash - Chase</td>
            <td>—</td>
            <td>${A(o)}</td>
          </tr>
          <tr class="total-row">
            <td>Net Amount</td>
            <td>${A(o)}</td>
            <td>${A(o)}</td>
          </tr>
        </tbody>
      </table>
      <div class="status-row">
        <strong>✓ Balanced · Awaiting Controller Approval</strong>
      </div>
    `,C.to(n,{duration:.8,opacity:1,y:0,ease:"power2.out"})}}function ee(){const t=document.createElement("canvas");if(t.getContext("webgl")||t.getContext("experimental-webgl"))try{Ie()}catch(n){console.warn("WebGL initialization failed, using fallback",n),te()}else te();He(),Me(),ke(),qe()}function qe(){const t=document.querySelectorAll(".tab-button");t.forEach(o=>{o.addEventListener("click",()=>{const a=o.getAttribute("data-tab");t.forEach(l=>l.classList.remove("active")),o.classList.add("active"),document.querySelectorAll(".tab-content").forEach(l=>{l.classList.remove("active")});const c=document.querySelector(`[data-tab-content="${a}"]`);c&&c.classList.add("active")})});const e=document.querySelectorAll(".faq-item");e.forEach(o=>{const a=o.querySelector(".faq-question");a==null||a.addEventListener("click",()=>{const c=o.classList.contains("active");e.forEach(l=>l.classList.remove("active")),c||o.classList.add("active")})});const n=document.querySelectorAll(".glass-layer"),r=document.querySelectorAll(".trust-detail");n.forEach((o,a)=>{o.addEventListener("click",()=>{n.forEach(l=>l.classList.remove("active")),o.classList.add("active"),r.forEach(l=>l.classList.remove("active"));const c=document.querySelector(`[data-detail="${a+1}"]`);c&&c.classList.add("active")})}),n.length>0&&r.length>0&&(n[0].classList.add("active"),r[0].classList.add("active"));const i=document.querySelector(".mobile-menu-toggle"),s=document.querySelector(".nav-links");i==null||i.addEventListener("click",()=>{s==null||s.classList.toggle("active")}),document.querySelectorAll('a[href^="#"]').forEach(o=>{o.addEventListener("click",a=>{a.preventDefault();const c=document.querySelector(o.getAttribute("href")||"");c&&c.scrollIntoView({behavior:"smooth",block:"start"})})})}function te(){const t=document.getElementById("particle-canvas");if(t){t.style.display="none";const n=document.getElementById("hero");n&&(n.style.background="linear-gradient(135deg, #6b1d2a 0%, #0a0a0a 50%, #ff7a1a 100%)")}const e=document.getElementById("arch-canvas");if(e){const n=e.getContext("2d");n&&(e.width=e.clientWidth,e.height=e.clientHeight,n.fillStyle="#141414",n.fillRect(0,0,e.width,e.height),n.fillStyle="#ff7a1a",n.font="16px Fira Mono",n.textAlign="center",n.fillText("WebGL unavailable - 3D visualization disabled",e.width/2,e.height/2))}}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",ee):ee();
