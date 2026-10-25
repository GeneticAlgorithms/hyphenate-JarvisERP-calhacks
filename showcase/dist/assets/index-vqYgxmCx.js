import{g as p}from"./gsap-SFc2wnMY.js";(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))r(e);new MutationObserver(e=>{for(const n of e)if(n.type==="childList")for(const i of n.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&r(i)}).observe(document,{childList:!0,subtree:!0});function a(e){const n={};return e.integrity&&(n.integrity=e.integrity),e.referrerPolicy&&(n.referrerPolicy=e.referrerPolicy),e.crossOrigin==="use-credentials"?n.credentials="include":e.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function r(e){if(e.ep)return;e.ep=!0;const n=a(e);fetch(e.href,n)}})();let u="new";const c=[];let S=0;const w="0000000000000000000000000000000000000000000000000000000000000000";async function A(o,t){const a=o+t,r=new TextEncoder().encode(a),e=await crypto.subtle.digest("SHA-256",r);return Array.from(new Uint8Array(e)).map(i=>i.toString(16).padStart(2,"0")).join("")}async function m(o,t,a){const r=new Date().toISOString(),e=c.length>0?c[c.length-1].hash:w,n=`${r}|${o}|${t}|${a}`,i=await A(e,n);c.push({id:++S,timestamp:r,action:o,actor:t,data:a,prevHash:e,hash:i}),b()}function b(){const o=document.getElementById("audit-log");o&&(o.innerHTML=c.map(t=>`
    <div class="audit-entry ${t.tampered?"tampered":""}" data-id="${t.id}">
      <div><strong>#${t.id}</strong> ${t.action} by ${t.actor}</div>
      <div>${t.data}</div>
      <div class="audit-entry-hash">prev: ${t.prevHash.substring(0,16)}...</div>
      <div class="audit-entry-hash">hash: ${t.hash.substring(0,16)}...</div>
    </div>
  `).join(""))}function f(){const o=document.getElementById("state-display");o&&(o.textContent=u);const t=document.getElementById("btn-ask"),a=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis");t&&(t.disabled=u!=="proposed"&&u!=="needs_info"),a&&(a.disabled=u!=="proposed"),r&&(r.disabled=u!=="proposed")}function h(o,t=!1){const a=document.getElementById("state-message");a&&(a.textContent=o,a.className=t?"state-message error":"state-message")}function T(){m("INIT","SYSTEM","Work item created");const o=document.getElementById("btn-propose"),t=document.getElementById("btn-ask"),a=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis"),e=document.getElementById("btn-tamper"),n=document.getElementById("btn-verify");o==null||o.addEventListener("click",async()=>{u="proposed",await m("PROPOSE","JarvisERP","Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44"),f(),h("Entry proposed. Awaiting Controller approval.")}),t==null||t.addEventListener("click",async()=>{u="needs_info",await m("REQUEST_INFO","JarvisERP","Unclear transaction: $350 Zelle to R Lopez, no receipt"),f(),h("Asked Controller for clarification.")}),a==null||a.addEventListener("click",async()=>{u="approved",await m("APPROVE","Controller","Approved for posting"),f(),h("Approved by Controller. Ready to post.")}),r==null||r.addEventListener("click",async()=>{await m("APPROVE_ATTEMPT","JarvisERP","Attempted self-approval"),await m("DENY","GATEWAY","HTTP 403: Agent cannot approve own work"),h("❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.",!0)}),e==null||e.addEventListener("click",()=>{c.length>=2&&(c[1].data="TAMPERED DATA - expense all to Software",c[1].tampered=!0,b(),v("",!1))}),n==null||n.addEventListener("click",async()=>{let i=!0,s=-1;for(let d=0;d<c.length;d++){const l=c[d],C=d===0?w:c[d-1].hash;if(l.prevHash!==C){i=!1,s===-1&&(s=d);break}const L=`${l.timestamp}|${l.action}|${l.actor}|${l.data}`,$=await A(l.prevHash,L);l.hash!==$?(i=!1,s===-1&&(s=d),l.tampered=!0):l.tampered=!1}b(),i?v("✓ Audit log verified. Hash chain intact.",!0):v(`❌ Chain broken at entry #${s+1}. Tampering detected.`,!1)}),x(),I(),f()}function v(o,t){const a=document.getElementById("verify-result");a&&(a.textContent=o,a.className=t?"verify-result valid":"verify-result invalid")}function x(){const o=document.querySelectorAll(".btn-challenge"),t=document.getElementById("custom-challenge"),a=document.getElementById("btn-custom-challenge"),r=document.getElementById("challenge-response"),e=document.getElementById("btn-new-evidence"),n={materiality:"Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.",simpler:"Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.",timing:"No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it's convenient. Delaying would misstate both periods."};o.forEach(i=>{i.addEventListener("click",()=>{const s=i.getAttribute("data-challenge");s&&r&&(r.innerHTML=`
          <div><strong>Challenge:</strong> ${i.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${n[s]}</div>
        `)})}),a==null||a.addEventListener("click",()=>{const i=t==null?void 0:t.value.trim();if(i&&r){let s="I understand your concern. Let me look up the relevant policy and precedent...";i.toLowerCase().includes("material")?s=n.materiality:i.toLowerCase().includes("simple")||i.toLowerCase().includes("complex")?s=n.simpler:(i.toLowerCase().includes("next")||i.toLowerCase().includes("later"))&&(s=n.timing),r.innerHTML=`
        <div><strong>Challenge:</strong> ${i}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${s}</div>
      `}}),e==null||e.addEventListener("click",async()=>{r&&(r.innerHTML=`
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `,await m("CONCEDE","JarvisERP","Withdrew entry, re-proposed, precedent added"))})}function I(){const o=document.querySelectorAll(".btn-scenario"),t=document.getElementById("scenario-output"),a={"vendor-scam":`
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
    `};o.forEach(r=>{r.addEventListener("click",()=>{const e=r.getAttribute("data-scenario");e&&t&&(t.innerHTML=a[e]||"")})})}const R=[{term:"Debit",definition:"An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger."},{term:"Credit",definition:"An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side."},{term:"Net Amount",definition:"The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits."},{term:"ERP",definition:"Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations."},{term:"General Ledger (GL)",definition:"The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements."},{term:"Reconcile",definition:"The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies."},{term:"AP (Accounts Payable)",definition:"Money the company owes to vendors and suppliers. A liability on the balance sheet until paid."},{term:"AR (Accounts Receivable)",definition:"Money customers owe to the company. An asset on the balance sheet until collected."},{term:"Accrual",definition:"Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting."},{term:"Prepaid",definition:"An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits)."},{term:"Materiality",definition:"The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification."},{term:"Chart of Accounts",definition:"The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses)."},{term:"Subledger",definition:"A detailed record supporting a GL control account, like individual vendor balances backing up the AP total."},{term:"Journal Entry (JE)",definition:"A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting."},{term:"Approval Matrix",definition:"A control defining who can approve transactions at different dollar thresholds or categories."},{term:"Precedent",definition:"A recorded decision on how similar transactions should be classified in the future, building institutional knowledge."},{term:"Audit Trail",definition:"A chronological record of all changes, showing who did what and when, enabling verification and compliance."},{term:"Hash Chain",definition:"A cryptographic structure where each record includes the hash of the previous one, making tampering detectable."}];function B(){const o=document.getElementById("glossary-grid"),t=document.getElementById("glossary-search");function a(r=""){if(!o)return;const e=R.filter(({term:n,definition:i})=>n.toLowerCase().includes(r.toLowerCase())||i.toLowerCase().includes(r.toLowerCase()));o.innerHTML=e.map(({term:n,definition:i})=>`
      <div class="glossary-term">
        <h4>${n}</h4>
        <p>${i}</p>
      </div>
    `).join("")}a(),t==null||t.addEventListener("input",r=>{a(r.target.value)})}const y=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function g(o){return"$"+o.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}function k(){const o=document.getElementById("bank-line"),t=document.getElementById("split-cards"),a=document.getElementById("balance-table");let r=!1;o==null||o.addEventListener("click",()=>{r||(r=!0,p.to(o,{duration:.5,scale:1.05,borderColor:"#ff7a1a",onComplete:()=>{e()}}))});function e(){if(!t||!a)return;t.innerHTML=y.map(s=>`
      <div class="split-card">
        <div class="split-account">${s.account}</div>
        <div class="split-name">${s.name}</div>
        <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${s.detail}</div>
        <div class="split-amount">${g(s.amount)}</div>
      </div>
    `).join(""),p.to(t,{duration:.8,opacity:1,y:0,ease:"power2.out",onComplete:()=>{n()}}),t.querySelectorAll(".split-card").forEach((s,d)=>{p.from(s,{duration:.6,delay:d*.1,opacity:0,y:30,rotationX:-20,ease:"back.out(1.7)"})})}function n(){if(!a)return;const i=y.reduce((s,d)=>s+d.amount,0);a.innerHTML=`
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          ${y.map(s=>`
            <tr>
              <td>${s.account} ${s.name}</td>
              <td>${g(s.amount)}</td>
              <td>—</td>
            </tr>
          `).join("")}
          <tr>
            <td>1010 Cash - Chase</td>
            <td>—</td>
            <td>${g(i)}</td>
          </tr>
          <tr class="total-row">
            <td>Net Amount</td>
            <td>${g(i)}</td>
            <td>${g(i)}</td>
          </tr>
        </tbody>
      </table>
      <div class="status-row">
        <strong>✓ Balanced · Awaiting Controller Approval</strong>
      </div>
    `,p.to(a,{duration:.8,opacity:1,y:0,ease:"power2.out"})}}function E(){k(),T(),B(),P(),M(),H()}function P(){const o=document.querySelectorAll(".workflow-tab"),t=document.querySelectorAll(".workflow-content");o.forEach(r=>{r.addEventListener("click",()=>{const e=r.getAttribute("data-tab");o.forEach(n=>n.classList.remove("active")),r.classList.add("active"),t.forEach(n=>{n.classList.remove("active"),n.getAttribute("data-content")===e&&n.classList.add("active")})})});const a=document.querySelectorAll(".faq-item");a.forEach(r=>{const e=r.querySelector(".faq-q");e==null||e.addEventListener("click",()=>{const n=r.classList.contains("active");a.forEach(i=>i.classList.remove("active")),n||r.classList.add("active")})}),document.querySelectorAll('a[href^="#"]').forEach(r=>{r.addEventListener("click",e=>{e.preventDefault();const n=document.querySelector(r.getAttribute("href")||"");n&&n.scrollIntoView({behavior:"smooth",block:"start"})})})}function M(){const o=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function t(e){return"$"+e.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}const a=document.getElementById("demo-splits"),r=document.getElementById("demo-table");!a||!r||(setTimeout(()=>{a.innerHTML=o.map(e=>`
      <div style="padding: 1rem; background: var(--color-gray-50); border: 1px solid var(--color-gray-200); border-radius: 8px;">
        <div style="font-size: 0.75rem; color: var(--color-gray-600); margin-bottom: 0.25rem;">${e.account}</div>
        <div style="font-weight: 600; margin-bottom: 0.25rem;">${e.name}</div>
        <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${e.detail}</div>
        <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-orange);">${t(e.amount)}</div>
      </div>
    `).join(""),a.style.opacity="1",a.style.transition="opacity 0.6s ease"},1e3),setTimeout(()=>{const e=o.reduce((n,i)=>n+i.amount,0);r.innerHTML=`
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr>
            <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--color-gray-200);">Account</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Debit</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Credit</th>
          </tr>
        </thead>
        <tbody>
          ${o.map(n=>`
            <tr>
              <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">${n.account} ${n.name}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${t(n.amount)}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            </tr>
          `).join("")}
          <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">1010 Cash - Chase</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${t(e)}</td>
          </tr>
          <tr style="font-weight: 700;">
            <td style="padding: 0.75rem; border-top: 2px solid var(--color-black);">Net Amount</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${t(e)}</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${t(e)}</td>
          </tr>
        </tbody>
      </table>
      <div style="margin-top: 1rem; text-align: center; color: var(--color-orange); font-weight: 600;">
        ✓ Balanced · Awaiting Controller Approval
      </div>
    `,r.style.opacity="1",r.style.transition="opacity 0.6s ease"},2e3))}function H(){const o=document.getElementById("hero-video"),t=document.getElementById("hero-split-card"),a=document.getElementById("hero");if(!o)return;if(window.matchMedia("(prefers-reduced-motion: reduce)").matches&&t){t.classList.add("visible"),o.pause(),o.style.display="none";return}let e=!1;const n=()=>{!e&&t&&(t.classList.add("visible"),e=!0)};o.addEventListener("ended",n),o.addEventListener("timeupdate",()=>{o.currentTime>=9&&!e&&n()}),setTimeout(n,9e3),a&&"IntersectionObserver"in window&&new IntersectionObserver(s=>{s.forEach(d=>{d.isIntersecting?o.play().catch(()=>{}):o.pause()})}).observe(a)}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",E):E();
