import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.min.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc="https://cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.worker.min.mjs";

const workspace=document.querySelector("#workspace"),mobileFeed=document.querySelector("#mobile-feed"),
viewport=document.querySelector("#viewport"),world=document.querySelector("#world"),
themeToggle=document.querySelector("#theme-toggle"),resetViewBtn=document.querySelector("#reset-view"),
resetLayoutBtn=document.querySelector("#reset-layout");
const view={scale:.58,x:-210,y:-65,min:.28,max:1.35},positions=new Map();

function setTheme(theme,persist=true){document.documentElement.dataset.theme=theme;themeToggle.textContent=theme==="dark"?"LIGHT":"DARK";if(persist)localStorage.setItem("portfolio-theme",theme)}
function initTheme(){const s=localStorage.getItem("portfolio-theme");setTheme(s==="light"||s==="dark"?s:(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"),false)}
themeToggle.addEventListener("click",()=>setTheme(document.documentElement.dataset.theme==="dark"?"light":"dark"));
function applyView(){world.style.transform=`translate(${view.x}px,${view.y}px) scale(${view.scale})`}
function resetView(){view.scale=.58;view.x=-210;view.y=-65;applyView()} resetViewBtn.addEventListener("click",resetView);

async function loadMarkdown(file){const r=await fetch(`content/${file}`);if(!r.ok)throw new Error(file);return marked.parse(await r.text(),{gfm:true}).replaceAll('src="images/','src="content/images/')}
function cellLabel(i){return `${String.fromCharCode(65+i%26)}${4+i*7}`}
function place(el,item){el.style.left=`${item.x}px`;el.style.top=`${item.y}px`;el.style.width=`${item.w}px`;el.dataset.baseTransform=`translateZ(${item.z||0}px) rotateX(2deg) rotateZ(${item.rotate||0}deg)`;el.style.transform=el.dataset.baseTransform;positions.set(el,{x:0,y:0})}
function drag(el){
 let d=null,m=false;
 el.addEventListener("pointerdown",e=>{if(innerWidth<=900||e.button!==0)return;const interactive=e.target.closest("a,button");if(interactive&&interactive!==el&&!el.matches("a.certificate"))return;e.stopPropagation();const p=positions.get(el)||{x:0,y:0};d={id:e.pointerId,sx:e.clientX,sy:e.clientY,ox:p.x,oy:p.y};m=false;el.classList.add("dragging");el.setPointerCapture?.(e.pointerId)});
 el.addEventListener("pointermove",e=>{if(!d||e.pointerId!==d.id)return;const dx=(e.clientX-d.sx)/view.scale,dy=(e.clientY-d.sy)/view.scale;if(Math.abs(dx)+Math.abs(dy)>3)m=true;const p={x:d.ox+dx,y:d.oy+dy};positions.set(el,p);el.style.translate=`${p.x}px ${p.y}px`});
 const end=e=>{if(!d||e.pointerId!==d.id)return;d=null;el.classList.remove("dragging");try{el.releasePointerCapture?.(e.pointerId)}catch{}};
 el.addEventListener("pointerup",end);el.addEventListener("pointercancel",end);el.addEventListener("click",e=>{if(m){e.preventDefault();e.stopPropagation();m=false}},true)
}
resetLayoutBtn.addEventListener("click",()=>document.querySelectorAll(".paper,.certificate,.polaroid").forEach(el=>{positions.set(el,{x:0,y:0});el.style.translate="0 0"}));

async function cert(item,mobile=false){
 const a=document.createElement("a");a.href=item.file;a.target="_blank";a.rel="noopener";a.className=mobile?"mobile-certificate":"certificate";
 if(!mobile){place(a,item);drag(a)}
 const mat=document.createElement("div");mat.className="certificate__mat";a.appendChild(mat);
 try{const pdf=await pdfjsLib.getDocument(item.file).promise,page=await pdf.getPage(1),base=page.getViewport({scale:1}),vp=page.getViewport({scale:Math.max(320,(item.w||420)*1.3)/base.width}),c=document.createElement("canvas"),dpr=Math.min(devicePixelRatio||1,1.6);c.width=vp.width*dpr;c.height=vp.height*dpr;await page.render({canvasContext:c.getContext("2d"),viewport:vp,transform:dpr!==1?[dpr,0,0,dpr,0,0]:null}).promise;mat.appendChild(c)}
 catch(e){if(!item.optional)console.warn(e);const ph=document.createElement("div");ph.className="certificate__placeholder";ph.textContent=item.optional?"CMILT.pdf":"CERTIFICATE";mat.appendChild(ph)}
 return a
}
function polaroid(item,mobile=false){const e=document.createElement("div");e.className=mobile?"mobile-polaroid":"polaroid";if(!mobile){place(e,item);drag(e)}e.innerHTML=`<div class="polaroid__image"><strong>GBR</strong></div><div class="polaroid__caption"><h3>${item.title}</h3><p>${item.subtitle}</p><p>${item.body}</p><a href="${item.href}">OPEN GBR →</a>&nbsp;&nbsp;<a href="${item.systemHref}">VIEW THE SYSTEM →</a></div>`;return e}

async function desktop(m){
 workspace.innerHTML="";
 for(let i=0;i<m.sections.length;i++){const item=m.sections[i],p=document.createElement("article");p.className="paper";p.dataset.cell=cellLabel(i);p.dataset.section=item.file.replace(/\.md$/,"");place(p,item);drag(p);workspace.appendChild(p);try{p.innerHTML=await loadMarkdown(item.file)}catch{p.innerHTML=`<h1>${item.file}</h1><p>Could not load content.</p>`}}
 for(const c of m.certificates)workspace.appendChild(await cert(c,false));
 for(const o of m.objects||[])if(o.type==="polaroid")workspace.appendChild(polaroid(o,false))
}
async function mobile(m){
 mobileFeed.innerHTML="";
 for(const item of m.sections){const s=document.createElement("article");s.className="mobile-section";try{s.innerHTML=await loadMarkdown(item.file)}catch{s.innerHTML=`<h1>${item.file}</h1>`}mobileFeed.appendChild(s)}
 const csec=document.createElement("section");csec.className="mobile-section";csec.innerHTML="<h1>Certificates</h1><div class='mobile-certificates'></div>";mobileFeed.appendChild(csec);
 const ct=csec.querySelector(".mobile-certificates");for(const c of m.certificates)ct.appendChild(await cert(c,true));
 for(const o of m.objects||[])if(o.type==="polaroid")mobileFeed.appendChild(polaroid(o,true))
}
let pan=null;
viewport.addEventListener("pointerdown",e=>{if(innerWidth<=900||e.button!==0||e.target.closest(".paper,.certificate,.polaroid,a,button"))return;pan={id:e.pointerId,sx:e.clientX,sy:e.clientY,x:view.x,y:view.y};viewport.classList.add("is-panning");viewport.setPointerCapture?.(e.pointerId)});
viewport.addEventListener("pointermove",e=>{if(!pan||e.pointerId!==pan.id)return;view.x=pan.x+e.clientX-pan.sx;view.y=pan.y+e.clientY-pan.sy;applyView()});
function end(e){if(!pan||e.pointerId!==pan.id)return;pan=null;viewport.classList.remove("is-panning");try{viewport.releasePointerCapture?.(e.pointerId)}catch{}} viewport.addEventListener("pointerup",end);viewport.addEventListener("pointercancel",end);
viewport.addEventListener("wheel",e=>{if(innerWidth<=900)return;e.preventDefault();const r=viewport.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,wx=(mx-view.x)/view.scale,wy=(my-view.y)/view.scale,n=Math.max(view.min,Math.min(view.max,view.scale*Math.exp(-e.deltaY*.0012)));view.scale=n;view.x=mx-wx*n;view.y=my-wy*n;applyView()},{passive:false});

async function init(){initTheme();applyView();const m=await (await fetch("content/manifest.json")).json();document.querySelector("#site-title").textContent=m.title;document.querySelector("#site-subtitle").textContent=m.subtitle;document.querySelector("#linkedin-link").href=m.linkedin;await desktop(m);await mobile(m)}
init().catch(e=>{console.error(e);workspace.innerHTML="<article class='paper' style='left:400px;top:200px;width:600px'><h1>Portfolio failed to load</h1><p>Check content/manifest.json.</p></article>"});
