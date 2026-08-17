var SourceryKitUI=(function(n){"use strict";/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const L=globalThis,K=L.ShadowRoot&&(L.ShadyCSS===void 0||L.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ee=Symbol(),me=new WeakMap;let be=class{constructor(e,t,s){if(this._$cssResult$=!0,s!==ee)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(K&&e===void 0){const s=t!==void 0&&t.length===1;s&&(e=me.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),s&&me.set(t,e))}return e}toString(){return this.cssText}};const Ze=a=>new be(typeof a=="string"?a:a+"",void 0,ee),b=(a,...e)=>{const t=a.length===1?a[0]:e.reduce((s,i,r)=>s+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+a[r+1],a[0]);return new be(t,a,ee)},Je=(a,e)=>{if(K)a.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const t of e){const s=document.createElement("style"),i=L.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=t.cssText,a.appendChild(s)}},ke=K?a=>a:a=>a instanceof CSSStyleSheet?(e=>{let t="";for(const s of e.cssRules)t+=s.cssText;return Ze(t)})(a):a;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:Qe,defineProperty:Xe,getOwnPropertyDescriptor:Ye,getOwnPropertyNames:Ke,getOwnPropertySymbols:et,getPrototypeOf:tt}=Object,V=globalThis,xe=V.trustedTypes,st=xe?xe.emptyScript:"",at=V.reactiveElementPolyfillSupport,z=(a,e)=>a,F={toAttribute(a,e){switch(e){case Boolean:a=a?st:null;break;case Object:case Array:a=a==null?a:JSON.stringify(a)}return a},fromAttribute(a,e){let t=a;switch(e){case Boolean:t=a!==null;break;case Number:t=a===null?null:Number(a);break;case Object:case Array:try{t=JSON.parse(a)}catch{t=null}}return t}},te=(a,e)=>!Qe(a,e),ye={attribute:!0,type:String,converter:F,reflect:!1,useDefault:!1,hasChanged:te};Symbol.metadata??=Symbol("metadata"),V.litPropertyMetadata??=new WeakMap;let O=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=ye){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(e,s,t);i!==void 0&&Xe(this.prototype,e,i)}}static getPropertyDescriptor(e,t,s){const{get:i,set:r}=Ye(this.prototype,e)??{get(){return this[t]},set(o){this[t]=o}};return{get:i,set(o){const p=i?.call(this);r?.call(this,o),this.requestUpdate(e,p,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??ye}static _$Ei(){if(this.hasOwnProperty(z("elementProperties")))return;const e=tt(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(z("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(z("properties"))){const t=this.properties,s=[...Ke(t),...et(t)];for(const i of s)this.createProperty(i,t[i])}const e=this[Symbol.metadata];if(e!==null){const t=litPropertyMetadata.get(e);if(t!==void 0)for(const[s,i]of t)this.elementProperties.set(s,i)}this._$Eh=new Map;for(const[t,s]of this.elementProperties){const i=this._$Eu(t,s);i!==void 0&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const s=new Set(e.flat(1/0).reverse());for(const i of s)t.unshift(ke(i))}else e!==void 0&&t.push(ke(e));return t}static _$Eu(e,t){const s=t.attribute;return s===!1?void 0:typeof s=="string"?s:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const s of t.keys())this.hasOwnProperty(s)&&(e.set(s,this[s]),delete this[s]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Je(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,s){this._$AK(e,s)}_$ET(e,t){const s=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,s);if(i!==void 0&&s.reflect===!0){const r=(s.converter?.toAttribute!==void 0?s.converter:F).toAttribute(t,s.type);this._$Em=e,r==null?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(e,t){const s=this.constructor,i=s._$Eh.get(e);if(i!==void 0&&this._$Em!==i){const r=s.getPropertyOptions(i),o=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:F;this._$Em=i;const p=o.fromAttribute(t,r.type);this[i]=p??this._$Ej?.get(i)??p,this._$Em=null}}requestUpdate(e,t,s,i=!1,r){if(e!==void 0){const o=this.constructor;if(i===!1&&(r=this[e]),s??=o.getPropertyOptions(e),!((s.hasChanged??te)(r,t)||s.useDefault&&s.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,s))))return;this.C(e,t,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:s,reflect:i,wrapped:r},o){s&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),r!==!0||o!==void 0)||(this._$AL.has(e)||(this.hasUpdated||s||(t=void 0),this._$AL.set(e,t)),i===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[i,r]of this._$Ep)this[i]=r;this._$Ep=void 0}const s=this.constructor.elementProperties;if(s.size>0)for(const[i,r]of s){const{wrapped:o}=r,p=this[i];o!==!0||this._$AL.has(i)||p===void 0||this.C(i,void 0,r,p)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(t)):this._$EM()}catch(s){throw e=!1,this._$EM(),s}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};O.elementStyles=[],O.shadowRootOptions={mode:"open"},O[z("elementProperties")]=new Map,O[z("finalized")]=new Map,at?.({ReactiveElement:O}),(V.reactiveElementVersions??=[]).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const se=globalThis,$e=a=>a,q=se.trustedTypes,we=q?q.createPolicy("lit-html",{createHTML:a=>a}):void 0,Se="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,_e="?"+$,it=`<${_e}>`,A=document,B=()=>A.createComment(""),R=a=>a===null||typeof a!="object"&&typeof a!="function",ae=Array.isArray,rt=a=>ae(a)||typeof a?.[Symbol.iterator]=="function",ie=`[ 	
\f\r]`,H=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ae=/-->/g,Ce=/>/g,C=RegExp(`>|${ie}(?:([^\\s"'>=/]+)(${ie}*=${ie}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ee=/'/g,Pe=/"/g,Te=/^(?:script|style|textarea|title)$/i,Oe=a=>(e,...t)=>({_$litType$:a,strings:e,values:t}),d=Oe(1),u=Oe(2),M=Symbol.for("lit-noChange"),c=Symbol.for("lit-nothing"),Me=new WeakMap,E=A.createTreeWalker(A,129);function De(a,e){if(!ae(a)||!a.hasOwnProperty("raw"))throw Error("invalid template strings array");return we!==void 0?we.createHTML(e):e}const ot=(a,e)=>{const t=a.length-1,s=[];let i,r=e===2?"<svg>":e===3?"<math>":"",o=H;for(let p=0;p<t;p++){const l=a[p];let v,m,f=-1,y=0;for(;y<l.length&&(o.lastIndex=y,m=o.exec(l),m!==null);)y=o.lastIndex,o===H?m[1]==="!--"?o=Ae:m[1]!==void 0?o=Ce:m[2]!==void 0?(Te.test(m[2])&&(i=RegExp("</"+m[2],"g")),o=C):m[3]!==void 0&&(o=C):o===C?m[0]===">"?(o=i??H,f=-1):m[1]===void 0?f=-2:(f=o.lastIndex-m[2].length,v=m[1],o=m[3]===void 0?C:m[3]==='"'?Pe:Ee):o===Pe||o===Ee?o=C:o===Ae||o===Ce?o=H:(o=C,i=void 0);const _=o===C&&a[p+1].startsWith("/>")?" ":"";r+=o===H?l+it:f>=0?(s.push(v),l.slice(0,f)+Se+l.slice(f)+$+_):l+$+(f===-2?p:_)}return[De(a,r+(a[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),s]};class N{constructor({strings:e,_$litType$:t},s){let i;this.parts=[];let r=0,o=0;const p=e.length-1,l=this.parts,[v,m]=ot(e,t);if(this.el=N.createElement(v,s),E.currentNode=this.el.content,t===2||t===3){const f=this.el.content.firstChild;f.replaceWith(...f.childNodes)}for(;(i=E.nextNode())!==null&&l.length<p;){if(i.nodeType===1){if(i.hasAttributes())for(const f of i.getAttributeNames())if(f.endsWith(Se)){const y=m[o++],_=i.getAttribute(f).split($),Y=/([.?@])?(.*)/.exec(y);l.push({type:1,index:r,name:Y[2],strings:_,ctor:Y[1]==="."?lt:Y[1]==="?"?dt:Y[1]==="@"?ct:W}),i.removeAttribute(f)}else f.startsWith($)&&(l.push({type:6,index:r}),i.removeAttribute(f));if(Te.test(i.tagName)){const f=i.textContent.split($),y=f.length-1;if(y>0){i.textContent=q?q.emptyScript:"";for(let _=0;_<y;_++)i.append(f[_],B()),E.nextNode(),l.push({type:2,index:++r});i.append(f[y],B())}}}else if(i.nodeType===8)if(i.data===_e)l.push({type:2,index:r});else{let f=-1;for(;(f=i.data.indexOf($,f+1))!==-1;)l.push({type:7,index:r}),f+=$.length-1}r++}}static createElement(e,t){const s=A.createElement("template");return s.innerHTML=e,s}}function D(a,e,t=a,s){if(e===M)return e;let i=s!==void 0?t._$Co?.[s]:t._$Cl;const r=R(e)?void 0:e._$litDirective$;return i?.constructor!==r&&(i?._$AO?.(!1),r===void 0?i=void 0:(i=new r(a),i._$AT(a,t,s)),s!==void 0?(t._$Co??=[])[s]=i:t._$Cl=i),i!==void 0&&(e=D(a,i._$AS(a,e.values),i,s)),e}class nt{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:s}=this._$AD,i=(e?.creationScope??A).importNode(t,!0);E.currentNode=i;let r=E.nextNode(),o=0,p=0,l=s[0];for(;l!==void 0;){if(o===l.index){let v;l.type===2?v=new j(r,r.nextSibling,this,e):l.type===1?v=new l.ctor(r,l.name,l.strings,this,e):l.type===6&&(v=new pt(r,this,e)),this._$AV.push(v),l=s[++p]}o!==l?.index&&(r=E.nextNode(),o++)}return E.currentNode=A,i}p(e){let t=0;for(const s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(e,s,t),t+=s.strings.length-2):s._$AI(e[t])),t++}}class j{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,s,i){this.type=2,this._$AH=c,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=D(this,e,t),R(e)?e===c||e==null||e===""?(this._$AH!==c&&this._$AR(),this._$AH=c):e!==this._$AH&&e!==M&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):rt(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==c&&R(this._$AH)?this._$AA.nextSibling.data=e:this.T(A.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:s}=e,i=typeof s=="number"?this._$AC(e):(s.el===void 0&&(s.el=N.createElement(De(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(t);else{const r=new nt(i,this),o=r.u(this.options);r.p(t),this.T(o),this._$AH=r}}_$AC(e){let t=Me.get(e.strings);return t===void 0&&Me.set(e.strings,t=new N(e)),t}k(e){ae(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let s,i=0;for(const r of e)i===t.length?t.push(s=new j(this.O(B()),this.O(B()),this,this.options)):s=t[i],s._$AI(r),i++;i<t.length&&(this._$AR(s&&s._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const s=$e(e).nextSibling;$e(e).remove(),e=s}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}}class W{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,s,i,r){this.type=1,this._$AH=c,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=c}_$AI(e,t=this,s,i){const r=this.strings;let o=!1;if(r===void 0)e=D(this,e,t,0),o=!R(e)||e!==this._$AH&&e!==M,o&&(this._$AH=e);else{const p=e;let l,v;for(e=r[0],l=0;l<r.length-1;l++)v=D(this,p[s+l],t,l),v===M&&(v=this._$AH[l]),o||=!R(v)||v!==this._$AH[l],v===c?e=c:e!==c&&(e+=(v??"")+r[l+1]),this._$AH[l]=v}o&&!i&&this.j(e)}j(e){e===c?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class lt extends W{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===c?void 0:e}}class dt extends W{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==c)}}class ct extends W{constructor(e,t,s,i,r){super(e,t,s,i,r),this.type=5}_$AI(e,t=this){if((e=D(this,e,t,0)??c)===M)return;const s=this._$AH,i=e===c&&s!==c||e.capture!==s.capture||e.once!==s.once||e.passive!==s.passive,r=e!==c&&(s===c||i);i&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class pt{constructor(e,t,s){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(e){D(this,e)}}const ht=se.litHtmlPolyfillSupport;ht?.(N,j),(se.litHtmlVersions??=[]).push("3.3.3");const ut=(a,e,t)=>{const s=t?.renderBefore??e;let i=s._$litPart$;if(i===void 0){const r=t?.renderBefore??null;s._$litPart$=i=new j(e.insertBefore(B(),r),r,void 0,t??{})}return i._$AI(a),i};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const re=globalThis;class k extends O{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=ut(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return M}}k._$litElement$=!0,k.finalized=!0,re.litElementHydrateSupport?.({LitElement:k});const ft=re.litElementPolyfillSupport;ft?.({LitElement:k}),(re.litElementVersions??=[]).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const w=a=>(e,t)=>{t!==void 0?t.addInitializer(()=>{customElements.define(a,e)}):customElements.define(a,e)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const gt={attribute:!0,type:String,converter:F,reflect:!1,hasChanged:te},vt=(a=gt,e,t)=>{const{kind:s,metadata:i}=t;let r=globalThis.litPropertyMetadata.get(i);if(r===void 0&&globalThis.litPropertyMetadata.set(i,r=new Map),s==="setter"&&((a=Object.create(a)).wrapped=!0),r.set(t.name,a),s==="accessor"){const{name:o}=t;return{set(p){const l=e.get.call(this);e.set.call(this,p),this.requestUpdate(o,l,a,!0,p)},init(p){return p!==void 0&&this.C(o,void 0,a,p),p}}}if(s==="setter"){const{name:o}=t;return function(p){const l=this[o];e.call(this,p),this.requestUpdate(o,l,a,!0,p)}}throw Error("Unsupported decorator location: "+s)};function h(a){return(e,t)=>typeof t=="object"?vt(a,e,t):((s,i,r)=>{const o=i.hasOwnProperty(r);return i.constructor.createProperty(r,s),o?Object.getOwnPropertyDescriptor(i,r):void 0})(a,e,t)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function I(a){return h({...a,state:!0,attribute:!1})}const S=b`
  :host {
    box-sizing: border-box;
    font-family: var(--sk-font-sans, Geist, ui-sans-serif, system-ui, sans-serif);
    color: var(--sk-foreground, #0a0a0a);
  }

  :host *,
  :host *::before,
  :host *::after {
    box-sizing: inherit;
  }

  button {
    appearance: none;
    background: none;
    border: 0;
    padding: 0;
    margin: 0;
    font: inherit;
    color: inherit;
    cursor: pointer;
  }

  button:disabled {
    cursor: default;
    opacity: var(--sk-opacity-disabled, 0.5);
  }

  p {
    margin: 0;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
`,G=b`
  .icon-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: var(--sk-radius-md, 8px);
    background: transparent;
    color: var(--sk-foreground, #0a0a0a);
    flex-shrink: 0;
  }

  .icon-button:hover:not(:disabled) {
    background: var(--sk-muted, #f5f5f5);
  }

  .icon-button:active:not(:disabled) {
    background: var(--sk-input, #e5e5e5);
  }

  .icon-button:focus-visible {
    outline: 2px solid var(--sk-status-healed, #3944ea);
    outline-offset: 1px;
  }

  .icon-button svg {
    width: 16px;
    height: 16px;
    display: block;
  }

  /* Figma uses a 24px square with a 3px radius inside card headers. */
  .icon-button.tight {
    width: 24px;
    height: 24px;
    border-radius: var(--sk-radius-sm, 3px);
  }

  .icon-button.tight svg {
    width: 16px;
    height: 16px;
  }
`,Ue=b`
  .outline-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--sk-space-2, 8px);
    height: 32px;
    padding: var(--sk-space-2, 8px) var(--sk-space-3, 12px);
    border: var(--sk-border-width, 1px) solid var(--sk-input, #e5e5e5);
    border-radius: var(--sk-radius-md, 8px);
    background: var(--sk-card, #ffffff);
    box-shadow: var(--sk-shadow-xs, 0 1px 2px 0 #0000000d);
    font-size: var(--sk-text-xs, 12px);
    line-height: var(--sk-text-xs-leading, 16px);
    font-weight: var(--sk-weight-medium, 500);
  }

  .outline-button:hover:not(:disabled) {
    background: var(--sk-muted, #f5f5f5);
  }

  .outline-button:active:not(:disabled) {
    background: var(--sk-input, #e5e5e5);
  }

  .outline-button:focus-visible {
    outline: 2px solid var(--sk-status-healed, #3944ea);
    outline-offset: 1px;
  }

  .outline-button svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    display: block;
  }
`,g=a=>u`
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >${a}</svg>
`,oe=g(u`<path d="M20 6 9 17l-5-5" />`),mt=g(u`<path d="M18 6 6 18" /><path d="m6 6 12 12" />`),ne=g(u`
  <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
  <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
`),le=g(u`
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
  <polyline points="7 10 12 15 17 10" />
  <line x1="12" x2="12" y1="15" y2="3" />
`),de=g(u`<path d="m6 9 6 6 6-6" />`),bt=g(u`
  <path d="m7 15 5 5 5-5" /><path d="m7 9 5-5 5 5" />
`),kt=g(u`
  <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z" />
  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
  <path d="M12 17h.01" />
`),ze=g(u`
  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
`),xt=g(u`
  <path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" />
  <path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" />
  <path d="M7 12h10" />
`),Be=g(u`
  <path d="M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h1a1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z" />
  <path d="M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h1a1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z" />
`),ce=g(u`
  <path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76" />
  <path d="m9 12 2 2 4-4" />
`),yt=g(u`
  <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
  <line x1="4" x2="4" y1="22" y2="15" />
`),Re=g(u`<path d="M21 12a9 9 0 1 1-6.219-8.56" />`),Z=g(u`
  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
  <path d="M12 9v4" /><path d="M12 17h.01" />
`),$t=g(u`
  <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
`),pe=g(u`
  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
  <path d="M3 3v5h5" />
`),He=g(u`<path d="m18 15-6-6-6 6" />`),wt=g(u`
  <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
  <path d="M14 2v4a2 2 0 0 0 2 2h4" />
`);g(u`
  <path d="M15 3h6v6" /><path d="M10 14 21 3" />
  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
`);const St=g(u`
  <circle cx="12" cy="12" r="10" /><path d="m15 9-6 6" /><path d="m9 9 6 6" />
`),_t=g(u`
  <path d="M12 8V4H8" /><rect width="16" height="12" x="4" y="8" rx="2" />
  <path d="M2 14h2" /><path d="M20 14h2" />
  <path d="M15 13v2" /><path d="M9 13v2" />
`);var At=Object.defineProperty,Ct=Object.getOwnPropertyDescriptor,Ne=(a,e,t,s)=>{for(var i=s>1?void 0:s?Ct(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&At(e,t,i),i};const Et={verified:"Verified",caught:"Caught",error:"Error",healed:"Healed",pending:"Pending",intercepted:"Intercepted"};n.SkActivityBadge=class extends k{constructor(){super(...arguments),this.status="pending"}render(){const e=["verified","caught","error","healed"].includes(this.status);return d`
      <span class="badge" part="badge">
        ${this.status==="intercepted"?xt:c}
        ${this.status==="pending"?Re:c}
        ${e?d`<span class="dot"></span>`:c}
        <span>${Et[this.status]}</span>
      </span>
    `}},n.SkActivityBadge.styles=[S,b`
      :host {
        display: inline-flex;
      }

      .badge {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: var(--sk-space-2, 8px);
        padding: var(--sk-space-0-5, 2px) var(--sk-space-2, 8px);
        border-radius: var(--sk-radius-full, 9999px);
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        font-weight: var(--sk-weight-medium, 500);
        white-space: nowrap;
        color: var(--pill-color, var(--sk-status-verifying, #9ca3af));
      }

      .badge svg {
        width: 12px;
        height: 12px;
        flex-shrink: 0;
        display: block;
      }

      .dot {
        width: 6px;
        height: 6px;
        border-radius: var(--sk-radius-full, 9999px);
        background: currentColor;
        flex-shrink: 0;
      }

      :host([status='intercepted']) .badge {
        --pill-color: var(--sk-status-healed, #3944ea);
      }
      :host([status='verified']) .badge {
        --pill-color: var(--sk-status-verified, #16a34a);
      }
      :host([status='caught']) .badge {
        --pill-color: var(--sk-status-caught, #f59e0b);
      }
      :host([status='error']) .badge {
        --pill-color: var(--sk-status-error, #ef4444);
      }
      :host([status='healed']) .badge {
        --pill-color: var(--sk-status-healed, #3944ea);
      }
      :host([status='pending']) .badge {
        --pill-color: var(--sk-status-verifying, #9ca3af);
      }

      :host([status='pending']) svg {
        animation: spin 1s linear infinite;
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }

      @media (prefers-reduced-motion: reduce) {
        :host([status='pending']) svg {
          animation: none;
        }
      }
    `],Ne([h({type:String,reflect:!0})],n.SkActivityBadge.prototype,"status",2),n.SkActivityBadge=Ne([w("sk-activity-badge")],n.SkActivityBadge);var Pt=Object.defineProperty,Tt=Object.getOwnPropertyDescriptor,x=(a,e,t,s)=>{for(var i=s>1?void 0:s?Tt(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&Pt(e,t,i),i};const Ot={question:kt,tool_call:ze,claim:Be,handover:_t,proof:ce,evaluation:Z,final:yt};function Mt(a,e){return e==="error"?St:e==="caught"?Z:a==="proof"?ce:Ot[a]}n.SkActivityStep=class extends k{constructor(){super(...arguments),this.kind="tool_call",this.label="",this.subtitle="",this.tone="default",this.first=!1,this.last=!1,this.open=!1,this.noContent=!1,this.separator=!1,this.position=0,this.setSize=0}get labelId(){return"label"}get contentId(){return"content"}toggle(){this.dispatchEvent(new CustomEvent("sk-toggle",{detail:{open:!this.open},bubbles:!0,composed:!0}))}renderHeaderContent(){return d`
      <span class="title" part="title">
        <span id=${this.labelId} title=${this.label}>${this.label}</span>
        ${this.subtitle?d`<span class="subtitle">${this.subtitle}</span>`:c}
        <slot name="title-badge"></slot>
      </span>
      <span class="trailing">
        <slot name="status"></slot>
        ${this.noContent?c:d`<span class="chevron" aria-hidden="true">
              ${de}
            </span>`}
      </span>
    `}render(){const e=this.subtitle?`${this.label} ${this.subtitle}`:this.label,t=this.position?`${e}, step ${this.position} of ${this.setSize}`:e;return d`
      <div class="rail" aria-hidden="true">
        <span class="line top"></span>
        <span class="glyph" part="glyph">
          ${Mt(this.kind,this.tone)}
        </span>
        <span class="line rest"></span>
      </div>
      <div class="body">
        <div class="card" part="card">
          ${this.noContent?d`<div class="header" part="header">
                ${this.renderHeaderContent()}
              </div>`:d`
                <button
                  class="header"
                  part="header"
                  aria-expanded=${this.open?"true":"false"}
                  aria-controls=${this.open?this.contentId:c}
                  aria-label=${this.open?`Collapse ${t}`:`Expand ${t}`}
                  @click=${this.toggle}
                >
                  ${this.renderHeaderContent()}
                </button>
              `}
          ${!this.noContent&&this.open?d`
                <div
                  id=${this.contentId}
                  class="content"
                  part="content"
                  role="region"
                  aria-labelledby=${this.labelId}
                >
                  <slot></slot>
                </div>
              `:c}
        </div>
      </div>
    `}},n.SkActivityStep.styles=[S,b`
      :host {
        display: flex;
        gap: var(--sk-space-4, 16px);
        align-items: stretch;
        width: 100%;
      }

      .rail {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1px;
        flex-shrink: 0;
      }

      .rail .line {
        width: 1px;
        background: var(--sk-border, #e5e5e5);
      }

      .rail .line.top {
        height: 6px;
      }

      .rail .line.rest {
        flex: 1 0 0;
        min-height: 0;
      }

      :host([first]) .rail .line.top {
        opacity: 0;
      }

      :host([last]) .rail .line.rest {
        opacity: 0;
      }

      .glyph {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        padding: 6px;
        border-radius: var(--sk-radius-full, 9999px);
        background: rgb(156 163 175 / 0.1);
        color: var(--sk-glyph, #4b5563);
        flex-shrink: 0;
      }

      .glyph svg {
        width: 18px;
        height: 18px;
        display: block;
      }

      :host([kind='tool_call']) .glyph {
        background: rgb(57 68 234 / 0.1);
        color: var(--sk-status-healed, #3944ea);
      }

      :host([tone='caught']) .glyph {
        background: rgb(245 158 11 / 0.1);
        color: var(--sk-status-caught, #f59e0b);
      }

      :host([tone='error']) .glyph {
        background: rgb(239 68 68 / 0.1);
        color: var(--sk-status-error, #ef4444);
      }

      .body {
        display: flex;
        flex: 1 0 0;
        min-width: 0;
        flex-direction: column;
        align-items: stretch;
        padding-bottom: var(--sk-space-4, 16px);
      }

      .card {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        overflow: hidden;
        border-radius: var(--sk-radius-md, 8px);
        background: var(--sk-card, #ffffff);
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-border, #e5e5e5);
      }

      :host([tone='caught']) .card {
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-status-caught, #f59e0b);
      }

      :host([tone='error']) .card {
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-status-error, #ef4444);
      }

      :host([separator]) .card {
        box-shadow: none;
        background: transparent;
      }

      :host([separator]) .header {
        padding-left: 0;
        padding-right: 0;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--sk-space-2, 8px);
        padding: var(--sk-space-2, 8px) var(--sk-space-2, 8px)
          var(--sk-space-2, 8px) var(--sk-space-4, 16px);
        width: 100%;
        text-align: left;
        min-height: 48px;
      }

      button.header:hover {
        background: var(--sk-muted, #f5f5f5);
      }

      button.header:focus-visible {
        outline: 2px solid var(--sk-status-healed, #3944ea);
        outline-offset: -2px;
      }

      .title {
        display: flex;
        align-items: center;
        gap: var(--sk-space-2, 8px);
        min-width: 0;
        /* Long tool names must yield to the status and chevron beside them
           rather than run underneath. */
        flex: 0 1 auto;
        overflow: hidden;
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        font-weight: var(--sk-weight-medium, 500);
      }

      .title > span:first-child {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        min-width: 0;
      }

      .subtitle {
        color: var(--sk-muted-foreground, #737373);
        font-weight: var(--sk-weight-normal, 400);
        white-space: nowrap;
      }

      .trailing {
        display: flex;
        align-items: center;
        gap: var(--sk-space-1, 4px);
        flex-shrink: 0;
      }

      /* Matches the ghost icon-sm footprint without being a nested control. */
      .chevron {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        color: var(--sk-foreground, #0a0a0a);
        flex-shrink: 0;
      }

      .chevron svg {
        width: 16px;
        height: 16px;
        display: block;
        transition: transform 150ms ease;
      }

      :host([open]) .chevron svg {
        transform: rotate(180deg);
      }

      .content {
        padding: var(--sk-space-4, 16px);
        border-top: var(--sk-border-width, 1px) solid var(--sk-border, #e5e5e5);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
      }

      @media (prefers-reduced-motion: reduce) {
        .chevron svg {
          transition: none;
        }
      }
    `],x([h({type:String,reflect:!0})],n.SkActivityStep.prototype,"kind",2),x([h({type:String})],n.SkActivityStep.prototype,"label",2),x([h({type:String})],n.SkActivityStep.prototype,"subtitle",2),x([h({type:String,reflect:!0})],n.SkActivityStep.prototype,"tone",2),x([h({type:Boolean,reflect:!0})],n.SkActivityStep.prototype,"first",2),x([h({type:Boolean,reflect:!0})],n.SkActivityStep.prototype,"last",2),x([h({type:Boolean,reflect:!0})],n.SkActivityStep.prototype,"open",2),x([h({type:Boolean,reflect:!0,attribute:"no-content"})],n.SkActivityStep.prototype,"noContent",2),x([h({type:Boolean,reflect:!0})],n.SkActivityStep.prototype,"separator",2),x([h({type:Number})],n.SkActivityStep.prototype,"position",2),x([h({type:Number,attribute:"set-size"})],n.SkActivityStep.prototype,"setSize",2),n.SkActivityStep=x([w("sk-activity-step")],n.SkActivityStep);var Dt=Object.defineProperty,Ut=Object.getOwnPropertyDescriptor,he=(a,e,t,s)=>{for(var i=s>1?void 0:s?Ut(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&Dt(e,t,i),i};n.SkClaimCard=class extends k{constructor(){super(...arguments),this.claim=null,this.tone="default"}willUpdate(e){if(!e.has("claim"))return;const t=this.claim;this.tone=!t||t.agrees?"default":t.outcome==="ERROR"?"error":"caught"}render(){const e=this.claim;if(!e)return c;const t=e.agrees?"Agrees":e.outcome==="ERROR"?"Not verified":"Disagrees";return d`
      <div class="card" part="card">
        <div class="head">
          ${e.path?d`<span class="path" title=${e.path}>${e.path}</span>`:c}
          ${e.verificationMode?d`<span class="chip">${e.verificationMode}</span>`:c}
          <span class="action">${e.actionName}</span>
          <span class="mark" title=${t}>
            <span class="dot"></span>
            <span class="sr-only">${t}</span>
          </span>
        </div>
        <div class="rows">
          <div class="row">
            <span class="label">Claimed:</span>
            <span class="value claimed">${e.claimed}</span>
          </div>
          <div class="row">
            <span class="label">Indexed:</span>
            <span class="value">
              ${e.indexed===null?d`<span class="missing">nothing indexed</span>`:e.indexed}
            </span>
          </div>
        </div>
        ${!e.agrees&&e.details?d`<p class="details">${e.details}</p>`:c}
      </div>
    `}},n.SkClaimCard.styles=[S,b`
      :host {
        display: block;
      }

      .card {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-4, 16px);
        border-radius: var(--sk-radius-md, 8px);
        padding: var(--sk-space-4, 16px);
        background: var(--sk-card, #ffffff);
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-border, #e5e5e5);
      }

      :host([tone='caught']) .card {
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-status-caught, #f59e0b);
      }

      :host([tone='error']) .card {
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-status-error, #ef4444);
      }

      .head {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }

      .path {
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        font-weight: var(--sk-weight-medium, 500);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .chip {
        padding: var(--sk-space-0-5, 2px) var(--sk-space-2, 8px);
        border-radius: 6px;
        background: rgb(75 85 99 / 0.1);
        color: var(--sk-glyph, #4b5563);
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        white-space: nowrap;
        flex-shrink: 0;
      }

      .action {
        color: var(--sk-muted-foreground, #737373);
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        font-weight: var(--sk-weight-medium, 500);
        white-space: nowrap;
      }

      /* Figma 203:8690: a px-8 py-2 pill carrying only the dot. */
      .mark {
        margin-left: auto;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: var(--sk-space-0-5, 2px) var(--sk-space-2, 8px);
        border-radius: var(--sk-radius-full, 9999px);
        flex-shrink: 0;
        color: var(--sk-status-verified, #16a34a);
      }

      :host([tone='caught']) .mark {
        color: var(--sk-status-caught, #f59e0b);
      }

      :host([tone='error']) .mark {
        color: var(--sk-status-error, #ef4444);
      }

      .dot {
        width: 6px;
        height: 6px;
        border-radius: var(--sk-radius-full, 9999px);
        background: currentColor;
        flex-shrink: 0;
      }

      .rows {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-3, 12px);
      }

      .row {
        display: flex;
        align-items: baseline;
        gap: var(--sk-space-2, 8px);
        min-width: 0;
      }

      .label {
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        font-weight: var(--sk-weight-medium, 500);
        color: var(--sk-muted-foreground, #737373);
        flex-shrink: 0;
      }

      .value {
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        word-break: break-word;
        min-width: 0;
      }

      :host([tone='caught']) .value {
        color: var(--sk-status-caught-text, #d97706);
      }

      :host([tone='error']) .value {
        color: var(--sk-status-error, #ef4444);
      }

      .missing {
        color: var(--sk-muted-foreground, #737373);
      }

      /* Figma I223:5736;203:8729: a bordered band under a failing comparison. */
      .details {
        margin: var(--sk-space-4, 16px) calc(-1 * var(--sk-space-4, 16px))
          calc(-1 * var(--sk-space-4, 16px));
        padding: var(--sk-space-4, 16px);
        border-top: var(--sk-border-width, 1px) solid var(--sk-border, #e5e5e5);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        color: var(--sk-status-caught-text, #d97706);
      }

      :host([tone='error']) .details {
        color: var(--sk-status-error, #ef4444);
      }

      :host([tone='caught']) .details {
        border-top-color: var(--sk-status-caught, #f59e0b);
      }
    `],he([h({type:Object})],n.SkClaimCard.prototype,"claim",2),he([h({type:String,reflect:!0})],n.SkClaimCard.prototype,"tone",2),n.SkClaimCard=he([w("sk-claim-card")],n.SkClaimCard);var zt=Object.defineProperty,Bt=Object.getOwnPropertyDescriptor,U=(a,e,t,s)=>{for(var i=s>1?void 0:s?Bt(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&zt(e,t,i),i};n.SkDetailBlock=class extends k{constructor(){super(...arguments),this.caption="",this.tag="",this.value="",this.tone="default",this.copied=!1}async copy(){try{await navigator.clipboard.writeText(this.value),this.copied=!0,window.setTimeout(()=>this.copied=!1,1500)}catch{}}render(){return d`
      ${this.caption?d`<span class="caption" part="caption">${this.caption}</span>`:c}
      <div class="box" part="block">
        ${this.tag?d`<div class="tag">${this.tag}</div>`:c}
        <pre class="value">${this.value}</pre>
        <button
          class="icon-button copy"
          aria-label=${this.copied?"Copied":`Copy ${this.caption}`}
          @click=${this.copy}
        >
          ${this.copied?oe:ne}
        </button>
      </div>
    `}},n.SkDetailBlock.styles=[S,G,b`
      :host {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-2, 8px);
      }

      .caption {
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        font-weight: var(--sk-weight-medium, 500);
        color: var(--sk-muted-foreground, #737373);
      }

      .box {
        position: relative;
        border-radius: var(--sk-radius-lg, 10px);
        background: var(--sk-card, #ffffff);
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-border, #e5e5e5);
        padding: var(--sk-space-4, 16px);
      }

      .tag {
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        color: var(--sk-muted-foreground, #737373);
        margin-bottom: var(--sk-space-2, 8px);
      }

      .value {
        margin: 0;
        padding-right: 40px;
        font-family: var(--sk-font-mono, ui-monospace, monospace);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        white-space: pre-wrap;
        word-break: break-word;
        overflow-x: auto;
      }

      .copy {
        position: absolute;
        right: 9px;
        top: 9px;
      }

      :host([tone='caught']) .value {
        color: var(--sk-status-caught-text, #d97706);
      }

      :host([tone='error']) .value {
        color: var(--sk-status-error, #ef4444);
      }

      :host([tone='verified']) .value {
        color: var(--sk-status-verified, #16a34a);
      }
    `],U([h({type:String})],n.SkDetailBlock.prototype,"caption",2),U([h({type:String})],n.SkDetailBlock.prototype,"tag",2),U([h({type:String})],n.SkDetailBlock.prototype,"value",2),U([h({type:String,reflect:!0})],n.SkDetailBlock.prototype,"tone",2),U([I()],n.SkDetailBlock.prototype,"copied",2),n.SkDetailBlock=U([w("sk-detail-block")],n.SkDetailBlock);var Rt=Object.defineProperty,Ht=Object.getOwnPropertyDescriptor,J=(a,e,t,s)=>{for(var i=s>1?void 0:s?Ht(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&Rt(e,t,i),i};const Nt={verified:"Verified",caught:"Caught",error:"Error",healed:"Healed",pending:"Pending"};n.SkProofList=class extends k{constructor(){super(...arguments),this.proofs=[],this.collapsed=!1,this.actionsEnabled=!1}emit(e,t){this.dispatchEvent(new CustomEvent(e,{detail:{queryId:t},bubbles:!0,composed:!0}))}renderItem(e,t){const s=Nt[e.status];return d`
      <div class="item ${t?"last":""}">
        <div class="item-head">
          <span class="file-glyph">${wt}</span>
          <span class="meta">
            <span class="name">
              <span class="status" data-status=${e.status}>
                <span class="dot"></span>
                <span>${s}</span>
              </span>
              <span class="text" title=${e.queryId}>${e.queryId}</span>
            </span>
            <span class="date">${jt(e.generatedAt)}</span>
          </span>
        </div>
        <div class="item-actions">
          <button
            class="outline-button"
            aria-disabled=${!this.actionsEnabled}
            ?disabled=${!this.actionsEnabled}
            @click=${()=>this.emit("sk-reverify",e.queryId)}
          >
            ${pe}
            <span>Re-verify</span>
          </button>
          <button
            class="outline-button square"
            aria-disabled=${!this.actionsEnabled}
            ?disabled=${!this.actionsEnabled}
            aria-label="Download proof ${e.queryId}"
            @click=${()=>this.emit("sk-download",e.queryId)}
          >
            ${le}
          </button>
        </div>
      </div>
    `}render(){const e=this.proofs.length>1;return d`
      <section class="card" part="card" aria-labelledby="proofs-heading">
        <div class="head">
          <h2 id="proofs-heading">${e?"Proofs":"Proof"}</h2>
          ${e?d`<span class="count">${this.proofs.length}</span>`:c}
          <span class="actions" style="min-height:24px">
            ${e?d`
                  <button
                    class="icon-button tight"
                    aria-disabled=${!this.actionsEnabled}
                    ?disabled=${!this.actionsEnabled}
                    aria-label="Re-verify all proofs"
                    @click=${()=>this.emit("sk-reverify-all",null)}
                  >
                    ${pe}
                  </button>
                  <button
                    class="icon-button tight"
                    aria-disabled=${!this.actionsEnabled}
                    ?disabled=${!this.actionsEnabled}
                    aria-label="Download all proofs"
                    @click=${()=>this.emit("sk-download-all",null)}
                  >
                    ${le}
                  </button>
                `:c}
            ${e?d`
                  <button
                    class="icon-button tight"
                    aria-expanded=${this.collapsed?"false":"true"}
                    aria-label=${this.collapsed?"Expand proofs":"Collapse proofs"}
                    @click=${()=>this.collapsed=!this.collapsed}
                  >
                    ${this.collapsed?de:He}
                  </button>
                `:c}
          </span>
        </div>
        ${this.collapsed?c:this.proofs.length===0?d`<p class="empty">No proofs recorded for this trace.</p>`:d`
                ${this.proofs.map((t,s)=>this.renderItem(t,s===this.proofs.length-1))}

                ${e?d`
                      <div class="footer">
                        <button
                          class="outline-button"
                          aria-disabled=${!this.actionsEnabled}
                          ?disabled=${!this.actionsEnabled}
                          @click=${()=>this.emit("sk-reverify-all",null)}
                        >
                          ${pe}
                          <span>Re-verify all</span>
                        </button>
                        <button
                          class="outline-button"
                          aria-disabled=${!this.actionsEnabled}
                          ?disabled=${!this.actionsEnabled}
                          @click=${()=>this.emit("sk-download-all",null)}
                        >
                          ${le}
                          <span>Download all</span>
                        </button>
                      </div>
                    `:c}
              `}
      </section>
    `}},n.SkProofList.styles=[S,G,Ue,b`
      :host {
        display: block;
      }

      .card {
        position: relative;
        border-radius: var(--sk-radius-md, 8px);
        background: var(--sk-card, #ffffff);
        overflow: hidden;
      }

      /* Rows fill the card edge to edge, so an inset ring on .card itself gets
         painted over. Drawing it above them keeps the outline closed. */
      .card::after {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: inherit;
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-border, #e5e5e5);
        pointer-events: none;
      }

      .head {
        display: flex;
        align-items: center;
        padding: var(--sk-space-2, 8px) var(--sk-space-2, 8px)
          var(--sk-space-2, 8px) var(--sk-space-4, 16px);
        box-shadow: inset 0 -1px 0 0 var(--sk-border, #e5e5e5);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        font-weight: var(--sk-weight-medium, 500);
      }

      h2 {
        margin: 0;
        font-size: inherit;
        line-height: inherit;
        font-weight: inherit;
      }

      .head .count {
        color: var(--sk-muted-foreground, #737373);
        font-weight: var(--sk-weight-normal, 400);
        margin-left: var(--sk-space-2, 8px);
      }

      .head .actions {
        display: flex;
        align-items: center;
        gap: var(--sk-space-2, 8px);
        margin-left: auto;
      }

      :host([collapsed]) .head {
        box-shadow: none;
      }

      /* Rows paint over the card ring, so they carry the side rules themselves. */
      .item {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-4, 16px);
        padding: var(--sk-space-4, 16px);
        box-shadow:
          inset 0 -1px 0 0 var(--sk-border, #e5e5e5),
          inset 1px 0 0 0 var(--sk-border, #e5e5e5),
          inset -1px 0 0 0 var(--sk-border, #e5e5e5);
        /* Figma 256:5905: white at 50% over the sidebar surface. */
        background:
          linear-gradient(90deg, rgb(255 255 255 / 0.5), rgb(255 255 255 / 0.5)),
          var(--sk-sidebar, #fafafa);
      }

      .item.last {
        box-shadow:
          inset 1px 0 0 0 var(--sk-border, #e5e5e5),
          inset -1px 0 0 0 var(--sk-border, #e5e5e5);
      }

      .item-head {
        display: flex;
        align-items: center;
        gap: var(--sk-space-2, 8px);
        min-width: 0;
      }

      .file-glyph {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        border-radius: var(--sk-radius-md, 8px);
        background: rgb(156 163 175 / 0.1);
        color: var(--sk-glyph, #4b5563);
        flex-shrink: 0;
      }

      .file-glyph svg {
        width: 18px;
        height: 18px;
        display: block;
      }

      .meta {
        display: flex;
        flex-direction: column;
        min-width: 0;
        flex: 1 0 0;
      }

      .name {
        display: flex;
        align-items: center;
        gap: var(--sk-space-2, 8px);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        font-weight: var(--sk-weight-medium, 500);
        min-width: 0;
      }

      .name .text {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .status {
        display: flex;
        align-items: center;
        gap: var(--sk-space-1, 4px);
        flex-shrink: 0;
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        color: var(--dot-color, var(--sk-status-verifying, #9ca3af));
      }

      .dot {
        width: 6px;
        height: 6px;
        border-radius: var(--sk-radius-full, 9999px);
        flex-shrink: 0;
        background: currentColor;
      }

      .status[data-status='verified'] {
        --dot-color: var(--sk-status-verified, #16a34a);
      }
      .status[data-status='caught'] {
        --dot-color: var(--sk-status-caught, #f59e0b);
      }
      .status[data-status='error'] {
        --dot-color: var(--sk-status-error, #ef4444);
      }
      .status[data-status='healed'] {
        --dot-color: var(--sk-status-healed, #3944ea);
      }

      .date {
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading-none, 1);
        color: var(--sk-muted-foreground, #737373);
        opacity: 0.5;
        margin-top: var(--sk-space-1, 4px);
      }

      .item-actions {
        display: flex;
        gap: var(--sk-space-2, 8px);
      }

      .item-actions .outline-button:first-child {
        flex: 1 0 0;
      }

      .item-actions .outline-button.square,
      .footer .outline-button.square {
        width: 32px;
        padding: 0;
        flex: 0 0 auto;
      }

      .footer {
        display: flex;
        gap: var(--sk-space-2, 8px);
        padding: var(--sk-space-4, 16px);
        background: var(--sk-card, #ffffff);
        box-shadow:
          inset 0 1px 0 0 var(--sk-border, #e5e5e5),
          inset 1px 0 0 0 var(--sk-border, #e5e5e5),
          inset -1px 0 0 0 var(--sk-border, #e5e5e5);
      }

      .footer .outline-button:first-child {
        flex: 1 0 0;
      }

      .footer .outline-button:last-child {
        flex: 0 0 auto;
      }

      .empty {
        padding: var(--sk-space-4, 16px);
        font-size: var(--sk-text-sm, 14px);
        color: var(--sk-muted-foreground, #737373);
      }

      a.icon-button {
        text-decoration: none;
      }
    `],J([h({type:Array})],n.SkProofList.prototype,"proofs",2),J([h({type:Boolean,reflect:!0})],n.SkProofList.prototype,"collapsed",2),J([h({type:Boolean,attribute:"actions-enabled"})],n.SkProofList.prototype,"actionsEnabled",2),n.SkProofList=J([w("sk-proof-list")],n.SkProofList);function jt(a){if(!a)return"—";const e=new Date(a.endsWith("Z")?a:`${a}Z`);if(Number.isNaN(e.getTime()))return"—";const t=i=>String(i).padStart(2,"0");return`${`${e.getUTCFullYear()}-${t(e.getUTCMonth()+1)}-${t(e.getUTCDate())}`} ${t(e.getUTCHours())}:${t(e.getUTCMinutes())} UTC`}const It={verified:[.2,1,.2,1,.2,1,.2,1,.2],error:[1,.2,1,.2,1,.2,1,.2,1],caught:[1,1,1,1,.2,1,1,1,1],healed:[1,.2,1,1,1,1,1,.2,1],verifying:[.6,.8,1,.4,0,0,.2,.1,0]},je=[0,7.5,15],Ie=[0,1,2,5,8,7,6,3];function Le(a,e,t=""){const s=je[a%3],i=je[Math.floor(a/3)];return u`<path
    class=${t}
    style=${t?`--i:${Ie.indexOf(a)}`:""}
    d="M${s} ${i}H${s+5}V${i+5}H${s}V${i}Z"
    fill="currentColor"
    fill-opacity="${e}"
  />`}function Ve(a){const e=a==="verifying"?Ie.map(t=>Le(t,1,"chase")):It[a].map((t,s)=>({opacity:t,i:s})).filter(({opacity:t})=>t!==0).map(({opacity:t,i:s})=>Le(s,t));return u`
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">${e}</svg>
  `}const Lt=b`
  .chase {
    animation: sk-chase 1s linear infinite;
    animation-delay: calc(var(--i) * -0.125s);
  }

  @keyframes sk-chase {
    0% {
      fill-opacity: 1;
    }
    70%,
    100% {
      fill-opacity: 0.15;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .chase {
      animation: none;
      fill-opacity: 0.6;
    }
  }
`;var Vt=Object.defineProperty,Ft=Object.getOwnPropertyDescriptor,P=(a,e,t,s)=>{for(var i=s>1?void 0:s?Ft(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&Vt(e,t,i),i};const qt={verified:oe,caught:Z,error:mt,verifying:Re,healed:oe};n.SkTraceStatusBadge=class extends k{constructor(){super(...arguments),this.status="verifying",this.variant="chip",this.iconOnly=!1,this.size="default",this.interactive=!1,this.disabled=!1}get label(){return this.status.charAt(0).toUpperCase()+this.status.slice(1)}render(){const e=this.variant==="mark"?Ve(this.status):qt[this.status];return d`
      <span class="sr-only">
        Trace status: ${this.iconOnly?this.label:""}
      </span>
      <span class="badge" part="badge">
        ${this.iconOnly||this.variant==="mark"?d`<span class="bare" part="mark">${e}</span>`:d`<span class="chip" part="chip">${e}</span>`}
        ${this.iconOnly?c:d`<span part="label">${this.label}</span>`}
      </span>
    `}},n.SkTraceStatusBadge.styles=[S,Lt,b`
      :host {
        display: inline-flex;
      }

      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip: rect(0 0 0 0);
        white-space: nowrap;
      }

      .badge {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: var(--sk-space-1-5, 6px);
        height: var(--badge-size, 32px);
        padding: var(--sk-space-2, 8px) var(--sk-space-3, 12px);
        border-radius: var(--sk-radius-md, 8px);
        overflow: hidden;
        position: relative;
        background: var(--badge-color);
        color: var(--sk-status-on-solid, #fafafa);
        font-size: var(--badge-text, var(--sk-text-xs, 12px));
        line-height: var(--sk-text-xs-leading, 16px);
        font-weight: var(--sk-weight-medium, 500);
        white-space: nowrap;
      }

      /* Figma layers hover and pressed as white overlays over the fill. */
      :host([interactive]) .badge:hover::after,
      :host([interactive]) .badge:active::after {
        content: '';
        position: absolute;
        inset: 0;
        pointer-events: none;
      }

      :host([interactive]) .badge:hover::after {
        background: var(--sk-overlay-hover, #ffffff1a);
      }

      :host([interactive]) .badge:active::after {
        background: var(--sk-overlay-pressed, #ffffff4d);
      }

      :host([disabled]) {
        opacity: var(--sk-opacity-disabled, 0.5);
        pointer-events: none;
      }

      .chip {
        display: flex;
        align-items: center;
        justify-content: center;
        width: var(--chip-size, 16px);
        height: var(--chip-size, 16px);
        padding: 3px;
        border-radius: var(--sk-radius-full, 9999px);
        background: var(--sk-status-on-solid-chip, #ffffff);
        color: var(--badge-color);
        flex-shrink: 0;
      }

      .chip svg,
      .bare svg {
        width: 100%;
        height: 100%;
        display: block;
      }

      /* Figma 272:7329: the Trace Trigger pill is pure white, not #fafafa. */
      :host([variant='mark']) .badge {
        color: #ffffff;
      }

      /* 272:7328 boxes the 12px mark inside a 16px slot with 2px around it. */
      .bare {
        display: flex;
        align-items: center;
        justify-content: center;
        width: var(--chip-size, 16px);
        height: var(--chip-size, 16px);
        padding: 2px;
        color: currentColor;
        flex-shrink: 0;
      }

      /* Figma sizes: Default 32, Small 26, X-Small 20. */
      :host([size='small']) .badge {
        --badge-size: 26px;
        --chip-size: 14px;
        padding: var(--sk-space-1, 4px) var(--sk-space-2, 8px);
      }

      :host([size='x-small']) .badge {
        --badge-size: 20px;
        --chip-size: 12px;
        padding: var(--sk-space-0-5, 2px) var(--sk-space-1-5, 6px);
      }

      :host([status='verified']) .badge {
        --badge-color: var(--sk-status-verified, #16a34a);
      }
      :host([status='verifying']) .badge {
        --badge-color: var(--sk-status-verifying, #9ca3af);
      }
      :host([status='caught']) .badge {
        --badge-color: var(--sk-status-caught, #f59e0b);
      }
      :host([status='error']) .badge {
        --badge-color: var(--sk-status-error, #ef4444);
      }
      :host([status='healed']) .badge {
        --badge-color: var(--sk-status-healed, #3944ea);
      }

      /* The mark runs its own chase, from markStyles. The Lucide loader in the
         chip variant has nothing to chase, so it still spins. */
      :host([status='verifying']) .chip svg {
        animation: spin 1s linear infinite;
        transform-origin: 50% 50%;
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }

      @media (prefers-reduced-motion: reduce) {
        :host([status='verifying']) .chip svg {
          animation: none;
        }
      }
    `],P([h({type:String,reflect:!0})],n.SkTraceStatusBadge.prototype,"status",2),P([h({type:String,reflect:!0})],n.SkTraceStatusBadge.prototype,"variant",2),P([h({type:Boolean,reflect:!0,attribute:"icon-only"})],n.SkTraceStatusBadge.prototype,"iconOnly",2),P([h({type:String,reflect:!0})],n.SkTraceStatusBadge.prototype,"size",2),P([h({type:Boolean,reflect:!0})],n.SkTraceStatusBadge.prototype,"interactive",2),P([h({type:Boolean,reflect:!0})],n.SkTraceStatusBadge.prototype,"disabled",2),n.SkTraceStatusBadge=P([w("sk-trace-status-badge")],n.SkTraceStatusBadge);var Wt=Object.defineProperty,Gt=Object.getOwnPropertyDescriptor,ue=(a,e,t,s)=>{for(var i=s>1?void 0:s?Gt(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&Wt(e,t,i),i};n.SkTraceSummary=class extends k{constructor(){super(...arguments),this.counts={toolCalls:0,proofs:0,claims:0,caught:0,durationSeconds:null},this.collapsed=!1}row(e,t,s){return d`
      <div class="row">
        <span class="name">${e}<span>${t}</span></span>
        <span class="value">${s}</span>
      </div>
    `}render(){const e=this.counts;return d`
      <section class="card" part="card" aria-labelledby="summary-heading">
        <div class="head">
          <h2 id="summary-heading">Summary</h2>
          <button
            class="icon-button"
            aria-expanded=${this.collapsed?"false":"true"}
            aria-label=${this.collapsed?"Expand summary":"Collapse summary"}
            @click=${()=>this.collapsed=!this.collapsed}
          >
            ${this.collapsed?de:He}
          </button>
        </div>
        ${this.collapsed?c:d`
              <div class="rows">
                ${this.row(ze,"Tool calls",String(e.toolCalls))}
                ${this.row(ce,"Proofs",String(e.proofs))}
                ${this.row(Be,"Claims",String(e.claims))}
                ${this.row(Z,"Caught",String(e.caught))}
                ${e.durationSeconds===null?c:this.row($t,"Duration",`${e.durationSeconds.toFixed(1)}s`)}
              </div>
            `}
      </section>
    `}},n.SkTraceSummary.styles=[S,G,b`
      :host {
        display: block;
      }

      .card {
        border-radius: var(--sk-radius-md, 8px);
        background: var(--sk-card, #ffffff);
        overflow: hidden;
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-border, #e5e5e5);
      }

      .head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--sk-space-2, 8px) var(--sk-space-2, 8px)
          var(--sk-space-2, 8px) var(--sk-space-4, 16px);
        box-shadow: inset 0 -1px 0 0 var(--sk-border, #e5e5e5);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        font-weight: var(--sk-weight-medium, 500);
      }

      h2 {
        margin: 0;
        font-size: inherit;
        line-height: inherit;
        font-weight: inherit;
      }

      :host([collapsed]) .head {
        box-shadow: none;
      }

      .rows {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-4, 16px);
        padding: var(--sk-space-4, 16px);
      }

      .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--sk-space-2, 8px);
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        font-weight: var(--sk-weight-medium, 500);
      }

      .row .name {
        display: flex;
        align-items: center;
        gap: var(--sk-space-1-5, 6px);
        color: var(--sk-muted-foreground, #737373);
      }

      .row .name svg {
        width: 12px;
        height: 12px;
        flex-shrink: 0;
        display: block;
        opacity: 0.5;
      }

      .row .value {
        font-variant-numeric: tabular-nums;
      }
    `],ue([h({type:Object})],n.SkTraceSummary.prototype,"counts",2),ue([h({type:Boolean,reflect:!0})],n.SkTraceSummary.prototype,"collapsed",2),n.SkTraceSummary=ue([w("sk-trace-summary")],n.SkTraceSummary);function fe(a){switch(a){case"PASS":return"verified";case"CAUGHT":return"caught";case"ERROR":return"error";default:return"pending"}}function Fe(a){if(a.length===0)return"error";const e=a.map(t=>t.outcome);return e.includes("CAUGHT")?"caught":e.includes("ERROR")?"error":e.includes(null)?"verifying":"verified"}function Q(a){if(a==null)return"";if(typeof a=="string")return a;if(typeof a=="number"||typeof a=="boolean")return String(a);try{return JSON.stringify(a)}catch{return String(a)}}function qe(a,e){if(a==null)return null;if(typeof a!="object")return Q(a);const t=a;if(e in t)return Q(t[e]);const s=e.replace(/^\$\.?/,"").split(".").filter(Boolean);let i=a;for(const r of s){if(i===null||typeof i!="object")return null;i=i[r]}return i===void 0?null:Q(i)}function ge(a){const e={actionName:a.action_name,verificationMode:a.verification_mode,agrees:a.outcome==="PASS",outcome:a.outcome,details:a.details??""};if(!a.claimed_value)return[];let t;try{t=JSON.parse(a.claimed_value)}catch{return[{...e,path:"",claimed:a.claimed_value,indexed:qe(a.actual_value,"")}]}return(Array.isArray(t)?t:[t]).map(i=>{const r=i??{},o=typeof r.path=="string"?r.path:"";return{...e,path:o,claimed:Q(r.value??i),indexed:qe(a.actual_value,o)}})}function X(a){return a.flatMap(ge)}const Zt=/(\*\*[^*]+\*\*|`[^`]+`)/g,Jt=/^\s*[-*]\s+(.*)$/;function We(a){return a.split(Zt).map(e=>e.startsWith("**")&&e.endsWith("**")&&e.length>4?d`<strong>${e.slice(2,-2)}</strong>`:e.startsWith("`")&&e.endsWith("`")&&e.length>2?d`<code>${e.slice(1,-1)}</code>`:e)}function Ge(a){if(!a)return[];const e=[];let t=[],s=[];const i=()=>{t.length!==0&&(e.push(d`<ul>
        ${t.map(o=>d`<li>${We(o)}</li>`)}
      </ul>`),t=[])},r=()=>{if(s.length===0)return;const o=s.join(`
`);e.push(d`<p class="prose">${We(o)}</p>`),s=[]};for(const o of a.split(`
`)){const p=Jt.exec(o);if(p){r(),t.push(p[1]??"");continue}if(o.trim()===""){i(),r();continue}i(),s.push(o)}return i(),r(),e}var Qt=Object.defineProperty,Xt=Object.getOwnPropertyDescriptor,T=(a,e,t,s)=>{for(var i=s>1?void 0:s?Xt(e,t):e,r=a.length-1,o;r>=0;r--)(o=a[r])&&(i=(s?o(e,t,i):o(i))||i);return s&&i&&Qt(e,t,i),i};n.SkTraceView=class extends k{constructor(){super(...arguments),this.baseUrl="",this.traceId="",this.data=null,this.error="",this.loading=!1,this.openSteps=new Set,this.inFlight=null}connectedCallback(){super.connectedCallback(),this.load()}disconnectedCallback(){this.inFlight?.abort(),super.disconnectedCallback()}updated(e){(e.has("baseUrl")||e.has("traceId"))&&this.load()}get origin(){return this.baseUrl||window.location.origin}async load(){if(!this.traceId)return;this.inFlight?.abort();const e=new AbortController;this.inFlight=e,this.loading=!0,this.error="";try{const t=await fetch(`${this.origin.replace(/\/$/,"")}/api/traces/${encodeURIComponent(this.traceId)}`,{signal:e.signal});if(!t.ok){const s=await t.json().catch(()=>null);throw new Error(s?.detail??`Request failed with ${t.status}`)}this.data=await t.json(),this.openSteps=new Set(this.steps.flatMap((s,i)=>s.openByDefault?[i]:[]))}catch(t){if(e.signal.aborted)return;this.error=t instanceof Error?t.message:String(t),this.data=null}finally{e.signal.aborted||(this.loading=!1)}}get steps(){const e=this.data;if(!e)return[];const t=[{kind:"question",label:"Question",subtitle:"",blocks:[],prose:e.trace.task,richProse:!1,claims:[],separator:!1,status:null,duration:"",tone:"default",openByDefault:!0}];for(const l of e.intercepts)t.push({kind:"tool_call",label:l.action_name,subtitle:"",blocks:as(l),prose:"",richProse:!1,claims:[],separator:!1,status:"intercepted",duration:"",tone:"default",openByDefault:!1});const s=X(e.intercepts);s.length>0&&t.push({kind:"claim",label:s.length===1?"Drafted claim":`Drafted ${s.length} claims`,subtitle:"",blocks:s.map(l=>({caption:"Claimed",tag:l.path||l.actionName,value:l.claimed})),prose:"",richProse:!1,claims:[],separator:!1,status:null,duration:"",tone:"default",openByDefault:!1});const i=e.intercepts.filter(l=>l.query_id);for(const[l,v]of i.entries()){const m=fe(v.outcome);t.push({kind:"proof",label:"Proof",subtitle:`${l+1} of ${i.length}`,blocks:is(v),prose:"",richProse:!1,claims:[],separator:!1,status:m,duration:"",tone:m==="caught"?"caught":m==="error"?"error":"default",openByDefault:!1})}i.length>0&&t.push({kind:"handover",label:"Claims handed over to agent",subtitle:"",blocks:[],prose:"",richProse:!1,claims:[],separator:!0,status:null,duration:"",tone:"default",openByDefault:!1});const r=X(e.intercepts),o=r.filter(l=>l.outcome==="CAUGHT"),p=r.filter(l=>l.outcome==="ERROR");return(o.length>0||p.length>0)&&t.push({kind:"evaluation",label:o.length>0?"Drift caught":"Verification error",subtitle:es(o.length,p.length,r.length),blocks:[],prose:"",richProse:!1,claims:r,separator:!1,status:o.length>0?"caught":"error",duration:"",tone:o.length>0?"caught":"error",openByDefault:!0}),t.push({kind:"final",label:e.trace.answer?"Final Answer":Kt,subtitle:"",blocks:[],prose:e.trace.answer,richProse:!!e.trace.answer,claims:[],separator:!e.trace.answer,status:null,duration:"",tone:"default",openByDefault:!0}),t}get counts(){const e=this.data;return{toolCalls:e?.intercepts.length??0,proofs:e?.intercepts.filter(t=>t.query_id).length??0,claims:e?X(e.intercepts).length:0,caught:e?.intercepts.filter(t=>t.outcome==="CAUGHT").length??0,durationSeconds:null}}get proofItems(){return(this.data?.intercepts??[]).filter(e=>e.query_id).map(e=>({queryId:e.query_id,generatedAt:null,status:Yt(e.outcome)}))}get status(){return this.data?Fe(this.data.intercepts):"verifying"}get allOpen(){const e=this.steps.filter(ve);return this.openSteps.size>=e.length&&e.length>0}copy(e){navigator.clipboard?.writeText(e)}toggleStep(e){const t=new Set(this.openSteps);t.has(e)?t.delete(e):t.add(e),this.openSteps=t}toggleAll(){if(this.allOpen){this.openSteps=new Set;return}this.openSteps=new Set(this.steps.flatMap((e,t)=>ve(e)?[t]:[]))}renderStep(e,t,s){const i=ve(e);return d`
      <li>
        <sk-activity-step
          kind=${e.kind}
          label=${e.label}
          subtitle=${e.subtitle}
          tone=${e.tone}
          ?first=${t===0}
          ?last=${t===s-1}
          ?open=${this.openSteps.has(t)}
          ?no-content=${!i}
          ?separator=${e.separator}
          position=${t+1}
          set-size=${s}
          @sk-toggle=${()=>this.toggleStep(t)}
        >
          ${e.status?d`<sk-activity-badge
                slot="status"
                status=${e.status}
              ></sk-activity-badge>`:c}
          ${e.prose?e.richProse?Ge(e.prose):d`<p class="prose">${e.prose}</p>`:c}
          ${e.claims.length?d`
                <div class="claim-cards">
                  ${e.claims.map(r=>d`<sk-claim-card .claim=${r}></sk-claim-card>`)}
                </div>
              `:c}
          ${e.blocks.length?d`
                <div class="blocks">
                  ${e.blocks.map(r=>d`
                      <sk-detail-block
                        caption=${r.caption}
                        tag=${r.tag??""}
                        .value=${r.value}
                        tone=${r.tone??"default"}
                      ></sk-detail-block>
                    `)}
                </div>
              `:c}
        </sk-activity-step>
      </li>
    `}render(){if(this.error)return d`<p class="state error" role="alert">${this.error}</p>`;if(!this.traceId&&!this.loading)return d`<p class="state">
        No trace selected. Open this page with <code>?id=&lt;trace id&gt;</code>,
        or run <code>sourcerykit trace &lt;id&gt;</code>.
      </p>`;if(this.loading||!this.data)return d`
        <div class="layout" aria-busy="true">
          <div class="main">
            <div class="title-bar">
              <span class="skeleton-bar skeleton-title"></span>
            </div>
            <div class="trail-bar">
              <span class="skeleton-bar skeleton-trail"></span>
            </div>
            <div class="trail-skeleton" aria-label="Loading trace">
              ${[0,1,2,3,4].map(()=>d`
                  <div class="skeleton-row">
                    <span class="skeleton-bar glyph"></span>
                    <span class="skeleton-bar card"></span>
                  </div>
                `)}
            </div>
          </div>
          <div class="divider" aria-hidden="true"></div>
          <div class="aside">
            <div class="aside-inner">
              <span class="skeleton-bar skeleton-side"></span>
              <span class="skeleton-bar skeleton-side"></span>
            </div>
          </div>
        </div>
      `;const{trace:e}=this.data,t=this.steps;return d`
      <div class="layout">
        <div class="main">
          <div class="title-bar">
            <h1>Trace</h1>
            <div class="title-actions">
              <button
                class="outline-button trace-id"
                @click=${()=>this.copy(e.id)}
                title=${e.id}
                aria-label="Copy trace id"
              >
                <span class="muted">ID:</span>
                <span class="value">${e.id}</span>
                ${ne}
              </button>
              <!-- Trace Trigger / Badge, Style=Pill (272:7328): the mark on
                   the fill, not the chipped Lucide glyph. -->
              <sk-trace-status-badge
                status=${this.status}
                variant="mark"
              ></sk-trace-status-badge>
            </div>
          </div>

          <div class="trail-bar">
            <div class="trail-left">
              <h2 id="trail-heading">Activity Trail</h2>
              <span class="steps-pill">
                ${t.filter(s=>!s.separator).length} steps
              </span>
              <span class="timestamp">${ts(e.created_at)}</span>
            </div>
            <span class="title-actions">
              <button
                class="icon-button"
                aria-label="Copy trace link"
                @click=${()=>this.copy(window.location.href)}
              >
                ${ne}
              </button>
              <button
                class="icon-button"
                aria-expanded=${this.allOpen?"true":"false"}
                aria-label=${this.allOpen?"Collapse all steps":"Expand all steps"}
                @click=${this.toggleAll}
              >
                ${bt}
              </button>
            </span>
          </div>

          <!--
            tabindex makes the scroller reachable, so PageDown and the arrow
            keys work. Chromium's focusable-scroller heuristic does not cover
            it: the trail is full of buttons.
          -->
          <ol
            class="trail"
            role="list"
            tabindex="0"
            aria-labelledby="trail-heading"
          >
            ${t.map((s,i)=>this.renderStep(s,i,t.length))}
          </ol>
        </div>

        <div class="divider" aria-hidden="true"></div>
        <!-- Scrolls when a trace carries enough proofs, so it needs a name
             and a tab stop of its own. -->
        <div
          class="aside"
          role="region"
          tabindex="0"
          aria-label="Trace summary and proofs"
        >
          <div class="aside-inner">
            ${e.answer?d`
                  <section class="answer-card" aria-labelledby="answer-heading">
                    <div class="answer-head">
                      <h2 id="answer-heading">Final answer</h2>
                    </div>
                    <div class="answer-body">${Ge(e.answer)}</div>
                  </section>
                `:c}
            <sk-trace-summary .counts=${this.counts}></sk-trace-summary>
            <sk-proof-list .proofs=${this.proofItems}></sk-proof-list>
          </div>
        </div>
      </div>
    `}},n.SkTraceView.styles=[S,G,Ue,b`
      :host {
        display: flex;
        flex-direction: column;
        min-height: 0;
        /* The grid field shows through the 1px gutter between the panels. */
        background: #e9e9e9;
      }

      .layout {
        display: grid;
        /*
         * Figma 236:11525 splits the column as main, a 1px band gap, then a
         * sidebar (236:11527 and 236:11624). Its halves land on .5, so the
         * sidebar is rounded up to keep the divider on Figma's own integer
         * boundary, x=927 to 928 at 1440, where it rasterises crisp.
         */
        grid-template-columns: minmax(0, 1fr) 1px 344px;
        align-items: stretch;
        width: 100%;
        max-width: 1104px;
        margin: 0 auto;
        flex: 1 1 auto;
        min-height: 0;
      }

      .main {
        min-width: 0;
        min-height: 0;
        display: flex;
        flex-direction: column;
        background: var(--sk-card, #ffffff);
        border-radius: 4px 0 0 4px;
        overflow: hidden;
      }

      .divider {
        background: transparent;
      }

      /* No overflow clip here: it would cancel the sticky sidebar. */
      .aside {
        border-radius: 0 4px 4px 0;
      }

      .title-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--sk-space-4, 16px);
        padding: 24px;
        /* Inset so the 80px Figma frame is the height that renders. */
        box-shadow: inset 0 -1px 0 0 var(--sk-border, #e5e5e5);
      }

      h1 {
        margin: 0;
        font-family: var(--sk-font-display, 'Space Grotesk', Geist, sans-serif);
        font-size: var(--sk-text-lg, 18px);
        line-height: var(--sk-text-lg-leading-none, 1);
        font-weight: var(--sk-weight-bold, 700);
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .title-actions {
        display: flex;
        align-items: center;
        gap: var(--sk-space-2, 8px);
        flex-shrink: 0;
      }

      .trace-id {
        max-width: 224px;
        min-width: 0;
      }

      .trace-id .muted {
        color: rgb(115 115 115 / 0.5);
        white-space: nowrap;
        flex-shrink: 0;
      }

      .trace-id .value {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .trail-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--sk-space-2, 8px);
        padding: var(--sk-space-4, 16px) 24px;
        box-shadow: inset 0 -1px 0 0 var(--sk-border, #e5e5e5);
      }

      .trail-left {
        display: flex;
        align-items: center;
        gap: var(--sk-space-2, 8px);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        font-weight: var(--sk-weight-medium, 500);
      }

      h2 {
        margin: 0;
        font-size: inherit;
        line-height: inherit;
        font-weight: inherit;
      }

      .steps-pill {
        padding: var(--sk-space-0-5, 2px) var(--sk-space-2, 8px);
        border-radius: 6px;
        background: rgb(57 68 234 / 0.1);
        color: var(--sk-status-healed, #3944ea);
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
      }

      .timestamp {
        font-family: var(--sk-font-mono, ui-monospace, monospace);
        font-size: var(--sk-text-xs, 12px);
        line-height: var(--sk-text-xs-leading, 16px);
        font-weight: var(--sk-weight-medium, 500);
        color: var(--sk-muted-foreground, #737373);
        opacity: 0.5;
      }

      /* The page chrome stays put; this is the only thing that scrolls. */
      .trail-skeleton,
      ol.trail {
        display: flex;
        flex-direction: column;
        margin: 0;
        padding: var(--sk-space-4, 16px) 24px;
        list-style: none;
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
        overscroll-behavior: contain;
        background: var(--sk-sidebar, #fafafa);
      }

      ol.trail > li {
        display: flex;
      }

      /* Both scrollers take focus for the keyboard, so only draw the ring when
         the keyboard is what put it there. */
      ol.trail:focus,
      .aside:focus {
        outline: none;
      }

      ol.trail:focus-visible,
      .aside:focus-visible {
        outline: 2px solid var(--sk-status-healed, #3944ea);
        outline-offset: -2px;
      }

      .aside {
        display: block;
        min-height: 0;
        overflow-y: auto;
        overscroll-behavior: contain;
        padding: var(--sk-space-4, 16px);
        background: var(--sk-sidebar, #fafafa);
      }

      .aside-inner {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-4, 16px);
      }

      /* A long trail pushes the Final Answer step off the bottom, so the
         answer is repeated here where it stays in view. */
      .answer-card {
        border-radius: var(--sk-radius-md, 8px);
        background: var(--sk-card, #ffffff);
        overflow: hidden;
        box-shadow: inset 0 0 0 var(--sk-border-width, 1px)
          var(--sk-border, #e5e5e5);
      }

      .answer-head {
        display: flex;
        align-items: center;
        padding: var(--sk-space-2, 8px) var(--sk-space-2, 8px)
          var(--sk-space-2, 8px) var(--sk-space-4, 16px);
        min-height: 48px;
        box-shadow: inset 0 -1px 0 0 var(--sk-border, #e5e5e5);
      }

      .answer-head h2 {
        margin: 0;
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
        font-weight: var(--sk-weight-medium, 500);
      }

      .answer-body {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-2, 8px);
        padding: var(--sk-space-4, 16px);
        font-size: var(--sk-text-sm, 14px);
        line-height: var(--sk-text-sm-leading, 20px);
      }

      .answer-body .prose {
        margin: 0;
      }

      .muted {
        color: var(--sk-muted-foreground, #737373);
      }

      .prose {
        white-space: pre-wrap;
        word-break: break-word;
      }

      /* The markdown the old dashboard rendered in the agent's answer. */
      .prose strong {
        font-weight: var(--sk-weight-semibold, 600);
      }

      .prose code,
      li code {
        font-family: var(--sk-font-mono, ui-monospace, monospace);
        font-size: 0.9em;
        padding: 1px var(--sk-space-1, 4px);
        border-radius: var(--sk-radius-sm, 3px);
        background: var(--sk-muted, #f5f5f5);
      }

      ul {
        margin: 0;
        padding-left: var(--sk-space-5, 20px);
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-1, 4px);
      }

      li strong {
        font-weight: var(--sk-weight-semibold, 600);
      }

      .blocks,
      .claim-cards {
        display: flex;
        flex-direction: column;
        gap: var(--sk-space-4, 16px);
      }

      /* The skeleton mirrors the real trail so the swap is not a jump. */
      .skeleton-bar {
        display: block;
        border-radius: var(--sk-radius-md, 8px);
        background: linear-gradient(
          90deg,
          var(--sk-muted, #f5f5f5) 25%,
          #ececec 37%,
          var(--sk-muted, #f5f5f5) 63%
        );
        background-size: 400% 100%;
        animation: shimmer 1.4s ease infinite;
      }

      .skeleton-row {
        display: flex;
        gap: var(--sk-space-4, 16px);
        padding-bottom: var(--sk-space-4, 16px);
      }

      .skeleton-row .glyph {
        width: 36px;
        height: 36px;
        margin-top: 7px;
        border-radius: var(--sk-radius-full, 9999px);
        flex-shrink: 0;
      }

      .skeleton-row .card {
        flex: 1 0 0;
        height: 48px;
      }

      .skeleton-title {
        height: 32px;
        width: 320px;
      }

      .skeleton-trail {
        height: 32px;
        width: 220px;
      }

      .skeleton-side {
        height: 192px;
      }

      .skeleton-side + .skeleton-side {
        height: 204px;
      }

      .state {
        padding: 48px 24px;
        text-align: center;
        color: var(--sk-muted-foreground, #737373);
        font-size: var(--sk-text-sm, 14px);
      }

      .state.error {
        color: var(--sk-status-error, #ef4444);
      }

      @keyframes shimmer {
        0% {
          background-position: 100% 50%;
        }
        100% {
          background-position: 0 50%;
        }
      }

      @media (prefers-reduced-motion: reduce) {
        .skeleton-bar {
          animation: none;
        }
      }

      @media (max-width: 1103px) {
        .layout {
          grid-template-columns: minmax(0, 1fr);
        }
        .divider {
          display: none;
        }
        .main,
        .aside {
          border-radius: 4px;
        }
      }

      /*
       * Stacked or too short for a fixed frame, the page scrolls as a whole and
       * nothing here may clip. page.css releases the frame on the same two
       * conditions; if the pair ever drifts apart, the trail overflows a
       * clipped .main with no scroller anywhere and the steps become
       * unreachable.
       */
      @media (max-width: 1103px), (max-height: 640px) {
        .main {
          overflow: visible;
        }

        .trail-skeleton,
        ol.trail,
        .aside {
          overflow: visible;
        }
      }
    `],T([h({type:String,attribute:"base-url"})],n.SkTraceView.prototype,"baseUrl",2),T([h({type:String,attribute:"trace-id"})],n.SkTraceView.prototype,"traceId",2),T([I()],n.SkTraceView.prototype,"data",2),T([I()],n.SkTraceView.prototype,"error",2),T([I()],n.SkTraceView.prototype,"loading",2),T([I()],n.SkTraceView.prototype,"openSteps",2),n.SkTraceView=T([w("sk-trace-view")],n.SkTraceView);function Yt(a){const e=fe(a);return e==="intercepted"?"pending":e}const Kt="No answer recorded";function ve(a){return a.blocks.length>0||a.prose.length>0||a.claims.length>0}function es(a,e,t){const s=t===1?"claim":"claims";return a>0&&e>0?`${a} of ${t} ${s} disagreed, ${e} could not be verified`:a>0?`${a} of ${t} ${s} disagreed`:`${e} of ${t} ${s} could not be verified`}function ts(a){if(!a)return"";const e=new Date(a.endsWith("Z")?a:`${a}Z`);if(Number.isNaN(e.getTime()))return"";const t=s=>String(s).padStart(2,"0");return`${e.getUTCFullYear()}-${t(e.getUTCMonth()+1)}-${t(e.getUTCDate())} ${t(e.getUTCHours())}:${t(e.getUTCMinutes())} UTC`}function ss(a){if(typeof a=="string")return a;try{return JSON.stringify(a,null,2)}catch{return String(a)}}function as(a){const e=[{caption:"URL",value:a.source_url}];return a.actual_value!==void 0&&a.actual_value!==null&&e.push({caption:"Response",tag:"JSON",value:ss(a.actual_value)}),e}function is(a){const e=[];a.query_id&&e.push({caption:"Query record",value:a.query_id}),e.push({caption:"Verification mode",value:a.verification_mode});for(const t of ge(a))e.push({caption:"Claimed",tag:t.path,value:t.claimed}),e.push({caption:"Indexed",tag:t.path,value:t.indexed??"nothing indexed"});return a.details&&e.push({caption:"Details",value:a.details}),e}return n.activityStatusFromOutcome=fe,n.allFieldClaims=X,n.fieldClaims=ge,n.rollUpStatus=Fe,n.statusMark=Ve,Object.defineProperty(n,Symbol.toStringTag,{value:"Module"}),n})({});
//# sourceMappingURL=sourcerykit-ui.iife.js.map
