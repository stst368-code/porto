import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.min.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc="https://cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.worker.min.mjs";

const workspace=document.querySelector("#workspace");
const mobileFeed=document.querySelector("#mobile-feed");
const viewport=document.querySelector("#viewport");
const world=document.querySelector("#world");
const themeToggle=document.querySelector("#theme-toggle");
const resetViewBtn=document.querySelector("#reset-view");
const resetLayoutBtn=document.querySelector("#reset-layout");

const view={scale:.72,x:-20,y:-20,min:.35,max:1.3};

function setTheme(theme,persist=true){
  document.documentElement.dataset.theme=theme;
  themeToggle.textContent=theme==="dark"?"LIGHT":"DARK";
  if(persist)localStorage.setItem("portfolio-theme",theme);
}
function initTheme(){
  const saved=localStorage.getItem("portfolio-theme");
  const theme=(saved==="light"||saved==="dark")
    ? saved
    : (matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");
  setTheme(theme,false);
}
themeToggle.addEventListener("click",()=>setTheme(document.documentElement.dataset.theme==="dark"?"light":"dark"));

function applyView(){
  world.style.transform=`translate(${view.x}px,${view.y}px) scale(${view.scale})`;
}
function resetView(){
  view.scale=.72;view.x=-20;view.y=-20;applyView();
}
resetViewBtn.addEventListener("click",resetView);

/* Layout is filesystem-driven now, so RESET LAYOUT just returns the world to
   its generated top-to-bottom order. There are no per-card x/y offsets. */
resetLayoutBtn.addEventListener("click",()=>window.scrollTo?.(0,0));

function markdownBase(file){
  return `content/${file}`;
}
function resolveRelativeAssets(html,file){
  const base=file.includes("/")?file.slice(0,file.lastIndexOf("/")+1):"";
  return html
    .replace(/src="(?!https?:|\/|data:)([^"]+)"/g,(_,path)=>`src="content/${base}${path}"`)
    .replace(/href="(?!https?:|\/|#|mailto:)([^"]+)"/g,(_,path)=>`href="content/${base}${path}"`);
}
async function loadMarkdown(file){
  const r=await fetch(markdownBase(file));
  if(!r.ok)throw new Error(`${file}: ${r.status}`);
  return resolveRelativeAssets(marked.parse(await r.text(),{gfm:true}),file);
}

async function renderCertificate(item,mobile=false){
  const el=document.createElement("div");
  el.className=mobile?"mobile-certificate certificate-view":"certificate certificate-view";
  el.dataset.href=item.file;
  el.setAttribute("role","link");
  el.setAttribute("tabindex","0");
  el.draggable=false;

  const mat=document.createElement("div");
  mat.className="certificate__mat";
  el.appendChild(mat);

  el.addEventListener("dragstart",e=>e.preventDefault());
  el.addEventListener("click",()=>window.open(item.file,"_blank","noopener"));
  el.addEventListener("keydown",e=>{
    if(e.key==="Enter"||e.key===" "){
      e.preventDefault();
      window.open(item.file,"_blank","noopener");
    }
  });

  try{
    const pdf=await pdfjsLib.getDocument(item.file).promise;
    const page=await pdf.getPage(1);
    const base=page.getViewport({scale:1});
    const target=mobile?900:620;
    const vp=page.getViewport({scale:target/base.width});
    const c=document.createElement("canvas");
    const dpr=Math.min(devicePixelRatio||1,1.5);
    c.width=vp.width*dpr;
    c.height=vp.height*dpr;
    c.draggable=false;
    await page.render({
      canvasContext:c.getContext("2d"),
      viewport:vp,
      transform:dpr!==1?[dpr,0,0,dpr,0,0]:null
    }).promise;
    mat.appendChild(c);
  }catch(err){
    if(!item.optional)console.warn(err);
    const ph=document.createElement("div");
    ph.className="certificate__placeholder";
    ph.textContent=item.optional?"CMILT.pdf":"CERTIFICATE";
    mat.appendChild(ph);
  }

  return el;
}

function renderPolaroid(item,mobile=false){
  const el=document.createElement("div");
  el.className=mobile?"mobile-polaroid":"polaroid grouped-polaroid";
  el.innerHTML=`
    <div class="polaroid__image"><strong>GBR</strong></div>
    <div class="polaroid__caption">
      <h3>${item.title}</h3>
      <p>${item.subtitle}</p>
      <p>${item.body}</p>
      <a href="${item.href}">OPEN GBR →</a>
      &nbsp;&nbsp;
      <a href="${item.systemHref}">VIEW THE SYSTEM →</a>
    </div>`;
  return el;
}

async function buildGroup(group,index,manifest){
  const section=document.createElement("section");
  section.className="content-group";
  section.dataset.group=group.folder;

  const head=document.createElement("header");
  head.className="content-group__head";
  head.innerHTML=`
    <span class="content-group__index">${String(index+1).padStart(2,"0")}</span>
    <div>
      <small>${group.folder}</small>
      <h2>${group.label}</h2>
    </div>`;
  section.appendChild(head);

  const grid=document.createElement("div");
  grid.className="content-group__grid";
  section.appendChild(grid);

  for(const entry of group.entries){
    const article=document.createElement("article");
    article.className="group-card";
    article.dataset.entry=entry.id;
    try{
      article.innerHTML=await loadMarkdown(entry.file);
    }catch(err){
      console.error(err);
      article.innerHTML=`<h1>${entry.file}</h1><p>Could not load content.</p>`;
    }
    grid.appendChild(article);
  }

  if(group.folder.startsWith("5-certifications")){
    const certGrid=document.createElement("div");
    certGrid.className="group-certificates";
    for(const cert of manifest.certificates||[]){
      certGrid.appendChild(await renderCertificate(cert,false));
    }
    section.appendChild(certGrid);
  }

  if(group.folder.startsWith("6-independent")){
    for(const obj of manifest.objects||[]){
      if(obj.type==="polaroid")section.appendChild(renderPolaroid(obj,false));
    }
  }

  return section;
}

async function buildDesktop(manifest){
  workspace.innerHTML="";
  for(let i=0;i<manifest.groups.length;i++){
    workspace.appendChild(await buildGroup(manifest.groups[i],i,manifest));
  }
}

async function buildMobile(manifest){
  mobileFeed.innerHTML="";
  for(let i=0;i<manifest.groups.length;i++){
    const group=manifest.groups[i];
    const section=document.createElement("section");
    section.className="mobile-group";
    section.innerHTML=`
      <header class="mobile-group__head">
        <span>${String(i+1).padStart(2,"0")}</span>
        <div><small>${group.folder}</small><h2>${group.label}</h2></div>
      </header>`;
    for(const entry of group.entries){
      const article=document.createElement("article");
      article.className="mobile-section";
      try{article.innerHTML=await loadMarkdown(entry.file)}
      catch{article.innerHTML=`<h1>${entry.file}</h1>`}
      section.appendChild(article);
    }
    if(group.folder.startsWith("5-certifications")){
      const certs=document.createElement("div");
      certs.className="mobile-certificates";
      for(const cert of manifest.certificates||[]){
        certs.appendChild(await renderCertificate(cert,true));
      }
      section.appendChild(certs);
    }
    if(group.folder.startsWith("6-independent")){
      for(const obj of manifest.objects||[]){
        if(obj.type==="polaroid")section.appendChild(renderPolaroid(obj,true));
      }
    }
    mobileFeed.appendChild(section);
  }
}

/* Camera pan/zoom remains desktop-only. The content itself is now normal-flow. */
let pan=null;
viewport.addEventListener("pointerdown",e=>{
  if(innerWidth<=900||e.button!==0||e.target.closest("a,button,.certificate-view"))return;
  pan={id:e.pointerId,sx:e.clientX,sy:e.clientY,x:view.x,y:view.y};
  viewport.classList.add("is-panning");
  viewport.setPointerCapture?.(e.pointerId);
});
viewport.addEventListener("pointermove",e=>{
  if(!pan||e.pointerId!==pan.id)return;
  view.x=pan.x+(e.clientX-pan.sx);
  view.y=pan.y+(e.clientY-pan.sy);
  applyView();
});
function endPan(e){
  if(!pan||e.pointerId!==pan.id)return;
  pan=null;
  viewport.classList.remove("is-panning");
  try{viewport.releasePointerCapture?.(e.pointerId)}catch{}
}
viewport.addEventListener("pointerup",endPan);
viewport.addEventListener("pointercancel",endPan);

viewport.addEventListener("wheel",e=>{
  if(innerWidth<=900)return;
  e.preventDefault();
  const r=viewport.getBoundingClientRect();
  const mx=e.clientX-r.left,my=e.clientY-r.top;
  const wx=(mx-view.x)/view.scale,wy=(my-view.y)/view.scale;
  const n=Math.max(view.min,Math.min(view.max,view.scale*Math.exp(-e.deltaY*.0012)));
  view.scale=n;
  view.x=mx-wx*n;
  view.y=my-wy*n;
  applyView();
},{passive:false});

async function init(){
  initTheme();applyView();
  const manifest=await (await fetch("content/content-manifest.json")).json();
  document.querySelector("#site-title").textContent=manifest.title;
  document.querySelector("#site-subtitle").textContent=manifest.subtitle;
  document.querySelector("#linkedin-link").href=manifest.linkedin;
  await buildDesktop(manifest);
  await buildMobile(manifest);
}
init().catch(err=>{
  console.error(err);
  workspace.innerHTML="<section class='content-group'><h1>Portfolio failed to load</h1><p>Run tools/build_content_manifest.py and check the content folders.</p></section>";
});
