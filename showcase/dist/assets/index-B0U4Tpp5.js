import{g as h}from"./gsap-SFc2wnMY.js";(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))r(e);new MutationObserver(e=>{for(const n of e)if(n.type==="childList")for(const a of n.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&r(a)}).observe(document,{childList:!0,subtree:!0});function i(e){const n={};return e.integrity&&(n.integrity=e.integrity),e.referrerPolicy&&(n.referrerPolicy=e.referrerPolicy),e.crossOrigin==="use-credentials"?n.credentials="include":e.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function r(e){if(e.ep)return;e.ep=!0;const n=i(e);fetch(e.href,n)}})();let u="new";const d=[];let x=0;const E="0000000000000000000000000000000000000000000000000000000000000000";async function A(o,t){const i=o+t,r=new TextEncoder().encode(i),e=await crypto.subtle.digest("SHA-256",r);return Array.from(new Uint8Array(e)).map(a=>a.toString(16).padStart(2,"0")).join("")}async function m(o,t,i){const r=new Date().toISOString(),e=d.length>0?d[d.length-1].hash:E,n=`${r}|${o}|${t}|${i}`,a=await A(e,n);d.push({id:++x,timestamp:r,action:o,actor:t,data:i,prevHash:e,hash:a}),b()}function b(){const o=document.getElementById("audit-log");o&&(o.innerHTML=d.map(t=>`
    <div class="audit-entry ${t.tampered?"tampered":""}" data-id="${t.id}">
      <div><strong>#${t.id}</strong> ${t.action} by ${t.actor}</div>
      <div>${t.data}</div>
      <div class="audit-entry-hash">prev: ${t.prevHash.substring(0,16)}...</div>
      <div class="audit-entry-hash">hash: ${t.hash.substring(0,16)}...</div>
    </div>
  `).join(""))}function g(){const o=document.getElementById("state-display");o&&(o.textContent=u);const t=document.getElementById("btn-ask"),i=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis");t&&(t.disabled=u!=="proposed"&&u!=="needs_info"),i&&(i.disabled=u!=="proposed"),r&&(r.disabled=u!=="proposed")}function f(o,t=!1){const i=document.getElementById("state-message");i&&(i.textContent=o,i.className=t?"state-message error":"state-message")}function T(){m("INIT","SYSTEM","Work item created");const o=document.getElementById("btn-propose"),t=document.getElementById("btn-ask"),i=document.getElementById("btn-approve-ctrl"),r=document.getElementById("btn-approve-jarvis"),e=document.getElementById("btn-tamper"),n=document.getElementById("btn-verify");o==null||o.addEventListener("click",async()=>{u="proposed",await m("PROPOSE","JarvisERP","Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44"),g(),f("Entry proposed. Awaiting Controller approval.")}),t==null||t.addEventListener("click",async()=>{u="needs_info",await m("REQUEST_INFO","JarvisERP","Unclear transaction: $350 Zelle to R Lopez, no receipt"),g(),f("Asked Controller for clarification.")}),i==null||i.addEventListener("click",async()=>{u="approved",await m("APPROVE","Controller","Approved for posting"),g(),f("Approved by Controller. Ready to post.")}),r==null||r.addEventListener("click",async()=>{await m("APPROVE_ATTEMPT","JarvisERP","Attempted self-approval"),await m("DENY","GATEWAY","HTTP 403: Agent cannot approve own work"),f("❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.",!0)}),e==null||e.addEventListener("click",()=>{d.length>=2&&(d[1].data="TAMPERED DATA - expense all to Software",d[1].tampered=!0,b(),v("",!1))}),n==null||n.addEventListener("click",async()=>{let a=!0,s=-1;for(let c=0;c<d.length;c++){const l=d[c],L=c===0?E:d[c-1].hash;if(l.prevHash!==L){a=!1,s===-1&&(s=c);break}const S=`${l.timestamp}|${l.action}|${l.actor}|${l.data}`,$=await A(l.prevHash,S);l.hash!==$?(a=!1,s===-1&&(s=c),l.tampered=!0):l.tampered=!1}b(),a?v("✓ Audit log verified. Hash chain intact.",!0):v(`❌ Chain broken at entry #${s+1}. Tampering detected.`,!1)}),I(),R(),g()}function v(o,t){const i=document.getElementById("verify-result");i&&(i.textContent=o,i.className=t?"verify-result valid":"verify-result invalid")}function I(){const o=document.querySelectorAll(".btn-challenge"),t=document.getElementById("custom-challenge"),i=document.getElementById("btn-custom-challenge"),r=document.getElementById("challenge-response"),e=document.getElementById("btn-new-evidence"),n={materiality:"Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.",simpler:"Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.",timing:"No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it's convenient. Delaying would misstate both periods."};o.forEach(a=>{a.addEventListener("click",()=>{const s=a.getAttribute("data-challenge");s&&r&&(r.innerHTML=`
          <div><strong>Challenge:</strong> ${a.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${n[s]}</div>
        `)})}),i==null||i.addEventListener("click",()=>{const a=t==null?void 0:t.value.trim();if(a&&r){let s="I understand your concern. Let me look up the relevant policy and precedent...";a.toLowerCase().includes("material")?s=n.materiality:a.toLowerCase().includes("simple")||a.toLowerCase().includes("complex")?s=n.simpler:(a.toLowerCase().includes("next")||a.toLowerCase().includes("later"))&&(s=n.timing),r.innerHTML=`
        <div><strong>Challenge:</strong> ${a}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${s}</div>
      `}}),e==null||e.addEventListener("click",async()=>{r&&(r.innerHTML=`
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `,await m("CONCEDE","JarvisERP","Withdrew entry, re-proposed, precedent added"))})}function R(){const o=document.querySelectorAll(".btn-scenario"),t=document.getElementById("scenario-output"),i={"vendor-scam":`
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
    `};o.forEach(r=>{r.addEventListener("click",()=>{const e=r.getAttribute("data-scenario");e&&t&&(t.innerHTML=i[e]||"")})})}const k=[{term:"Debit",definition:"An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger."},{term:"Credit",definition:"An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side."},{term:"Net Amount",definition:"The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits."},{term:"ERP",definition:"Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations."},{term:"General Ledger (GL)",definition:"The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements."},{term:"Reconcile",definition:"The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies."},{term:"AP (Accounts Payable)",definition:"Money the company owes to vendors and suppliers. A liability on the balance sheet until paid."},{term:"AR (Accounts Receivable)",definition:"Money customers owe to the company. An asset on the balance sheet until collected."},{term:"Accrual",definition:"Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting."},{term:"Prepaid",definition:"An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits)."},{term:"Materiality",definition:"The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification."},{term:"Chart of Accounts",definition:"The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses)."},{term:"Subledger",definition:"A detailed record supporting a GL control account, like individual vendor balances backing up the AP total."},{term:"Journal Entry (JE)",definition:"A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting."},{term:"Approval Matrix",definition:"A control defining who can approve transactions at different dollar thresholds or categories."},{term:"Precedent",definition:"A recorded decision on how similar transactions should be classified in the future, building institutional knowledge."},{term:"Audit Trail",definition:"A chronological record of all changes, showing who did what and when, enabling verification and compliance."},{term:"Hash Chain",definition:"A cryptographic structure where each record includes the hash of the previous one, making tampering detectable."}];function B(){const o=document.getElementById("glossary-grid"),t=document.getElementById("glossary-search");function i(r=""){if(!o)return;const e=k.filter(({term:n,definition:a})=>n.toLowerCase().includes(r.toLowerCase())||a.toLowerCase().includes(r.toLowerCase()));o.innerHTML=e.map(({term:n,definition:a})=>`
      <div class="glossary-term">
        <h4>${n}</h4>
        <p>${a}</p>
      </div>
    `).join("")}i(),t==null||t.addEventListener("input",r=>{i(r.target.value)})}const y=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function p(o){return"$"+o.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}function M(){const o=document.getElementById("bank-line");let t=!1;o==null||o.addEventListener("click",()=>{t||(t=!0,h.to(o,{duration:.5,scale:1.05,borderColor:"#ff7a1a",onComplete:()=>{C()}}))})}function C(){const o=document.getElementById("split-cards"),t=document.getElementById("balance-table");if(!o||!t)return;o.innerHTML=y.map(e=>`
    <div class="split-card">
      <div class="split-account">${e.account}</div>
      <div class="split-name">${e.name}</div>
      <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${e.detail}</div>
      <div class="split-amount">${p(e.amount)}</div>
    </div>
  `).join(""),h.to(o,{duration:.8,opacity:1,y:0,ease:"power2.out",onComplete:()=>{r()}}),o.querySelectorAll(".split-card").forEach((e,n)=>{h.from(e,{duration:.6,delay:n*.1,opacity:0,y:30,rotationX:-20,ease:"back.out(1.7)"})});function r(){if(!t)return;const e=y.reduce((n,a)=>n+a.amount,0);t.innerHTML=`
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          ${y.map(n=>`
            <tr>
              <td>${n.account} ${n.name}</td>
              <td>${p(n.amount)}</td>
              <td>—</td>
            </tr>
          `).join("")}
          <tr>
            <td>1010 Cash - Chase</td>
            <td>—</td>
            <td>${p(e)}</td>
          </tr>
          <tr class="total-row">
            <td>Net Amount</td>
            <td>${p(e)}</td>
            <td>${p(e)}</td>
          </tr>
        </tbody>
      </table>
      <div class="status-row">
        <strong>✓ Balanced · Awaiting Controller Approval</strong>
      </div>
    `,h.to(t,{duration:.8,opacity:1,y:0,ease:"power2.out"})}}function w(){M(),T(),B(),P(),H(),D(),q()}function P(){const o=document.querySelectorAll(".workflow-tab"),t=document.querySelectorAll(".workflow-content");o.forEach(r=>{r.addEventListener("click",()=>{const e=r.getAttribute("data-tab");o.forEach(n=>n.classList.remove("active")),r.classList.add("active"),t.forEach(n=>{n.classList.remove("active"),n.getAttribute("data-content")===e&&(n.classList.add("active"),e==="split"&&C())})})});const i=document.querySelectorAll(".faq-item");i.forEach(r=>{const e=r.querySelector(".faq-q");e==null||e.addEventListener("click",()=>{const n=r.classList.contains("active");i.forEach(a=>a.classList.remove("active")),n||r.classList.add("active")})}),document.querySelectorAll('a[href^="#"]').forEach(r=>{r.addEventListener("click",e=>{e.preventDefault();const n=document.querySelector(r.getAttribute("href")||"");n&&n.scrollIntoView({block:"start"})})})}function H(){const o=[{account:"1310",name:"Prepaid Tour Costs",detail:"EUR crew deposit",amount:3451.5},{account:"6810",name:"Bank & FX Fees",detail:"Transfer fees",amount:147.5},{account:"6410",name:"Software",detail:"Claude API",amount:200},{account:"1250",name:"Employee Receivable",detail:"Maya - Steam",amount:113.44}];function t(e){return"$"+e.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}const i=document.getElementById("demo-splits"),r=document.getElementById("demo-table");!i||!r||(setTimeout(()=>{i.innerHTML=o.map(e=>`
      <div style="padding: 1rem; background: var(--color-gray-50); border: 1px solid var(--color-gray-200); border-radius: 8px;">
        <div style="font-size: 0.75rem; color: var(--color-gray-600); margin-bottom: 0.25rem;">${e.account}</div>
        <div style="font-weight: 600; margin-bottom: 0.25rem;">${e.name}</div>
        <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${e.detail}</div>
        <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-orange);">${t(e.amount)}</div>
      </div>
    `).join(""),i.style.opacity="1",i.style.transition="opacity 0.6s ease"},1e3),setTimeout(()=>{const e=o.reduce((n,a)=>n+a.amount,0);r.innerHTML=`
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
    `,r.style.opacity="1",r.style.transition="opacity 0.6s ease"},2e3))}function D(){const o=document.getElementById("hero-video"),t=document.getElementById("hero-split-card"),i=document.getElementById("hero");if(!o)return;if(window.matchMedia("(prefers-reduced-motion: reduce)").matches&&t){t.classList.add("visible"),o.pause(),o.style.display="none";return}let e=!1;setTimeout(()=>{!e&&t&&(t.classList.add("visible"),e=!0)},2e3),i&&"IntersectionObserver"in window&&new IntersectionObserver(s=>{s.forEach(c=>{c.isIntersecting?o.play().catch(()=>{}):o.pause()})}).observe(i)}function q(){if(!("IntersectionObserver"in window)||window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;const t=document.querySelectorAll(".section:not(.hero-section)"),i=new IntersectionObserver(r=>{r.forEach(e=>{e.isIntersecting&&(e.target.classList.add("reveal","visible"),e.target.querySelectorAll(".problem-card, .trust-item, .simple-card, .demo-panel, .real-vs-col, .glossary-term").forEach((a,s)=>{s<5?(a.classList.add("reveal",`delay-${Math.min(s,4)}`),setTimeout(()=>{a.classList.add("visible")},50)):a.classList.add("reveal","visible")}))})},{threshold:.1,rootMargin:"0px 0px -80px 0px"});t.forEach(r=>{i.observe(r)})}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",w):w();
