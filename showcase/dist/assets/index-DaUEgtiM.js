import{g as p}from"./gsap-SFc2wnMY.js";(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const t of document.querySelectorAll('link[rel="modulepreload"]'))n(t);new MutationObserver(t=>{for(const o of t)if(o.type==="childList")for(const i of o.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&n(i)}).observe(document,{childList:!0,subtree:!0});function a(t){const o={};return t.integrity&&(o.integrity=t.integrity),t.referrerPolicy&&(o.referrerPolicy=t.referrerPolicy),t.crossOrigin==="use-credentials"?o.credentials="include":t.crossOrigin==="anonymous"?o.credentials="omit":o.credentials="same-origin",o}function n(t){if(t.ep)return;t.ep=!0;const o=a(t);fetch(t.href,o)}})();let m="new";const c=[];let S=0;const w="0000000000000000000000000000000000000000000000000000000000000000";async function A(r,e){const a=r+e,n=new TextEncoder().encode(a),t=await crypto.subtle.digest("SHA-256",n);return Array.from(new Uint8Array(t)).map(i=>i.toString(16).padStart(2,"0")).join("")}async function u(r,e,a){const n=new Date().toISOString(),t=c.length>0?c[c.length-1].hash:w,o=`${n}|${r}|${e}|${a}`,i=await A(t,o);c.push({id:++S,timestamp:n,action:r,actor:e,data:a,prevHash:t,hash:i}),b()}function b(){const r=document.getElementById("audit-log");r&&(r.innerHTML=c.map(e=>`
    <div class="audit-entry ${e.tampered?"tampered":""}" data-id="${e.id}">
      <div><strong>#${e.id}</strong> ${e.action} by ${e.actor}</div>
      <div>${e.data}</div>
      <div class="audit-entry-hash">prev: ${e.prevHash.substring(0,16)}...</div>
      <div class="audit-entry-hash">hash: ${e.hash.substring(0,16)}...</div>
    </div>
  `).join(""))}function f(){const r=document.getElementById("state-display");r&&(r.textContent=m);const e=document.getElementById("btn-ask"),a=document.getElementById("btn-approve-ctrl"),n=document.getElementById("btn-approve-jarvis");e&&(e.disabled=m!=="proposed"&&m!=="needs_info"),a&&(a.disabled=m!=="proposed"),n&&(n.disabled=m!=="proposed")}function h(r,e=!1){const a=document.getElementById("state-message");a&&(a.textContent=r,a.className=e?"state-message error":"state-message")}function T(){u("INIT","SYSTEM","Work item created");const r=document.getElementById("btn-propose"),e=document.getElementById("btn-ask"),a=document.getElementById("btn-approve-ctrl"),n=document.getElementById("btn-approve-jarvis"),t=document.getElementById("btn-tamper"),o=document.getElementById("btn-verify");r==null||r.addEventListener("click",async()=>{m="proposed",await u("PROPOSE","JarvisERP","Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44"),f(),h("Entry proposed. Awaiting Controller approval.")}),e==null||e.addEventListener("click",async()=>{m="needs_info",await u("REQUEST_INFO","JarvisERP","Unclear transaction: $350 Zelle to R Lopez, no receipt"),f(),h("Asked Controller for clarification.")}),a==null||a.addEventListener("click",async()=>{m="approved",await u("APPROVE","Controller","Approved for posting"),f(),h("Approved by Controller. Ready to post.")}),n==null||n.addEventListener("click",async()=>{await u("APPROVE_ATTEMPT","JarvisERP","Attempted self-approval"),await u("DENY","GATEWAY","HTTP 403: Agent cannot approve own work"),h("❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.",!0)}),t==null||t.addEventListener("click",()=>{c.length>=2&&(c[1].data="TAMPERED DATA - expense all to Software",c[1].tampered=!0,b(),v("",!1))}),o==null||o.addEventListener("click",async()=>{let i=!0,s=-1;for(let d=0;d<c.length;d++){const l=c[d],C=d===0?w:c[d-1].hash;if(l.prevHash!==C){i=!1,s===-1&&(s=d);break}const $=`${l.timestamp}|${l.action}|${l.actor}|${l.data}`,L=await A(l.prevHash,$);l.hash!==L?(i=!1,s===-1&&(s=d),l.tampered=!0):l.tampered=!1}b(),i?v("✓ Audit log verified. Hash chain intact.",!0):v(`❌ Chain broken at entry #${s+1}. Tampering detected.`,!1)}),x(),I(),f()}function v(r,e){const a=document.getElementById("verify-result");a&&(a.textContent=r,a.className=e?"verify-result valid":"verify-result invalid")}function x(){const r=document.querySelectorAll(".btn-challenge"),e=document.getElementById("custom-challenge"),a=document.getElementById("btn-custom-challenge"),n=document.getElementById("challenge-response"),t=document.getElementById("btn-new-evidence"),o={materiality:"Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.",simpler:"Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.",timing:"No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it's convenient. Delaying would misstate both periods."};r.forEach(i=>{i.addEventListener("click",()=>{const s=i.getAttribute("data-challenge");s&&n&&(n.innerHTML=`
          <div><strong>Challenge:</strong> ${i.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${o[s]}</div>
        `)})}),a==null||a.addEventListener("click",()=>{const i=e==null?void 0:e.value.trim();if(i&&n){let s="I understand your concern. Let me look up the relevant policy and precedent...";i.toLowerCase().includes("material")?s=o.materiality:i.toLowerCase().includes("simple")||i.toLowerCase().includes("complex")?s=o.simpler:(i.toLowerCase().includes("next")||i.toLowerCase().includes("later"))&&(s=o.timing),n.innerHTML=`
        <div><strong>Challenge:</strong> ${i}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${s}</div>
      `}}),t==null||t.addEventListener("click",async()=>{n&&(n.innerHTML=`
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `,await u("CONCEDE","JarvisERP","Withdrew entry, re-proposed, precedent added"))})}function I(){const r=document.querySelectorAll(".btn-scenario"),e=document.getElementById("scenario-output"),a={"vendor-scam":`
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
    `};r.forEach(n=>{n.addEventListener("click",()=>{const t=n.getAttribute("data-scenario");t&&e&&(e.innerHTML=a[t]||"")})})}const R=[{term:"Debit",definition:"An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger."},{term:"Credit",definition:"An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side."},{term:"Net Amount",definition:"The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits."},{term:"ERP",definition:"Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations."},{term:"General Ledger (GL)",definition:"The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements."},{term:"Reconcile",definition:"The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies."},{term:"AP (Accounts Payable)",definition:"Money the company owes to vendors and suppliers. A liability on the balance sheet until paid."},{term:"AR (Accounts Receivable)",definition:"Money customers owe to the company. An asset on the balance sheet until collected."},{term:"Accrual",definition:"Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting."},{term:"Prepaid",definition:"An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits)."},{term:"Materiality",definition:"The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification."},{term:"Chart of Accounts",definition:"The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses)."},{term:"Subledger",definition:"A detailed record supporting a GL control account, like individual vendor balances backing up the AP total."},{term:"Journal Entry (JE)",definition:"A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting."},{term:"Approval Matrix",definition:"A control defining who can approve transactions at different dollar thresholds or categories."},{term:"Precedent",definition:"A recorded decision on how similar transactions should be classified in the future, building institutional knowledge."},{term:"Audit Trail",definition:"A chronological record of all changes, showing who did what and when, enabling verification and compliance."},{term:"Hash Chain",definition:"A cryptographic structure where each record includes the hash of the previous one, making tampering detectable."}];function B(){const r=document.getElementById("glossary-grid"),e=document.getElementById("glossary-search");function a(n=""){if(!r)return;const t=R.filter(({term:o,definition:i})=>o.toLowerCase().includes(n.toLowerCase())||i.toLowerCase().includes(n.toLowerCase()));r.innerHTML=t.map(({term:o,definition:i})=>`
      <div class="glossary-term">
        <h4>${o}</h4>
        <p>${i}</p>
      </div>
    `).join("")}a(),e==null||e.addEventListener("input",n=>{a(n.target.value)})}const y=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function g(r){return"$"+r.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}function k(){const r=document.getElementById("bank-line"),e=document.getElementById("split-cards"),a=document.getElementById("balance-table");let n=!1;r==null||r.addEventListener("click",()=>{n||(n=!0,p.to(r,{duration:.5,scale:1.05,borderColor:"#ff7a1a",onComplete:()=>{t()}}))});function t(){if(!e||!a)return;e.innerHTML=y.map(s=>`
      <div class="split-card">
        <div class="split-account">${s.account}</div>
        <div class="split-name">${s.name}</div>
        <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${s.detail}</div>
        <div class="split-amount">${g(s.amount)}</div>
      </div>
    `).join(""),p.to(e,{duration:.8,opacity:1,y:0,ease:"power2.out",onComplete:()=>{o()}}),e.querySelectorAll(".split-card").forEach((s,d)=>{p.from(s,{duration:.6,delay:d*.1,opacity:0,y:30,rotationX:-20,ease:"back.out(1.7)"})})}function o(){if(!a)return;const i=y.reduce((s,d)=>s+d.amount,0);a.innerHTML=`
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
    `,p.to(a,{duration:.8,opacity:1,y:0,ease:"power2.out"})}}function E(){k(),T(),B(),P(),M(),H()}function P(){const r=document.querySelectorAll(".workflow-tab"),e=document.querySelectorAll(".workflow-content");r.forEach(n=>{n.addEventListener("click",()=>{const t=n.getAttribute("data-tab");r.forEach(o=>o.classList.remove("active")),n.classList.add("active"),e.forEach(o=>{o.classList.remove("active"),o.getAttribute("data-content")===t&&o.classList.add("active")})})});const a=document.querySelectorAll(".faq-item");a.forEach(n=>{const t=n.querySelector(".faq-q");t==null||t.addEventListener("click",()=>{const o=n.classList.contains("active");a.forEach(i=>i.classList.remove("active")),o||n.classList.add("active")})}),document.querySelectorAll('a[href^="#"]').forEach(n=>{n.addEventListener("click",t=>{t.preventDefault();const o=document.querySelector(n.getAttribute("href")||"");o&&o.scrollIntoView({behavior:"smooth",block:"start"})})})}function M(){const r=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function e(t){return"$"+t.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}const a=document.getElementById("demo-splits"),n=document.getElementById("demo-table");!a||!n||(setTimeout(()=>{a.innerHTML=r.map(t=>`
      <div style="padding: 1rem; background: var(--color-gray-50); border: 1px solid var(--color-gray-200); border-radius: 8px;">
        <div style="font-size: 0.75rem; color: var(--color-gray-600); margin-bottom: 0.25rem;">${t.account}</div>
        <div style="font-weight: 600; margin-bottom: 0.25rem;">${t.name}</div>
        <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${t.detail}</div>
        <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-orange);">${e(t.amount)}</div>
      </div>
    `).join(""),a.style.opacity="1",a.style.transition="opacity 0.6s ease"},1e3),setTimeout(()=>{const t=r.reduce((o,i)=>o+i.amount,0);n.innerHTML=`
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr>
            <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--color-gray-200);">Account</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Debit</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Credit</th>
          </tr>
        </thead>
        <tbody>
          ${r.map(o=>`
            <tr>
              <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">${o.account} ${o.name}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${e(o.amount)}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            </tr>
          `).join("")}
          <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">1010 Cash - Chase</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${e(t)}</td>
          </tr>
          <tr style="font-weight: 700;">
            <td style="padding: 0.75rem; border-top: 2px solid var(--color-black);">Net Amount</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${e(t)}</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${e(t)}</td>
          </tr>
        </tbody>
      </table>
      <div style="margin-top: 1rem; text-align: center; color: var(--color-orange); font-weight: 600;">
        ✓ Balanced · Awaiting Controller Approval
      </div>
    `,n.style.opacity="1",n.style.transition="opacity 0.6s ease"},2e3))}function H(){const r=document.getElementById("hero-video"),e=document.getElementById("hero-split-card"),a=document.getElementById("hero");if(!r)return;a&&"IntersectionObserver"in window&&new IntersectionObserver(o=>{o.forEach(i=>{i.isIntersecting?r.play().catch(()=>{}):r.pause()})}).observe(a),e&&setTimeout(()=>{e.classList.add("visible")},10500),window.matchMedia("(prefers-reduced-motion: reduce)").matches&&(r.pause(),r.style.display="none")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",E):E();
