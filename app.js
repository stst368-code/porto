import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.7.76/build/pdf.worker.min.mjs";

const PDF_URL = "cv/CV_SimonTaylor.pdf";

const HOTSPOTS = [
  { id:"mrp",      page:1, x:.055, y:.235, w:.89, h:.155, experimental:false },
  { id:"analysis", page:3, x:.055, y:.430, w:.89, h:.150, experimental:false },
  { id:"gbr",      page:4, x:.055, y:.770, w:.89, h:.150, experimental:true  }
];

const CERTIFICATES = [
  {
    id: "cscp",
    file: "cv/certs/CSCP.pdf",
    optional: false
  },
  {
    id: "cmilt",
    file: "cv/certs/CMILT.pdf",
    optional: true
  },
  {
    id: "ibmda",
    file: "cv/certs/IBMDA.pdf",
    optional: false
  },
  {
    id: "googleda",
    file: "cv/certs/GoogleDA.pdf",
    optional: false
  }
];

const pageGrid = document.querySelector("#page-grid");
const hotspotLayer = document.querySelector("#hotspot-layer");
const board = document.querySelector("#document-board");
const desk = document.querySelector("#desk");
const world = document.querySelector("#world");
const viewport = document.querySelector("#desk-viewport");
const connectors = document.querySelector("#connectors");
const themeToggle = document.querySelector("#theme-toggle");
const resetView = document.querySelector("#reset-view");
const resetLayout = document.querySelector("#reset-layout");

const view = {
  scale: 0.72,
  x: -250,
  y: 0,
  minScale: 0.35,
  maxScale: 1.6
};

const objectDefaults = new Map();
const objectOffsets = new Map();

function applyView(){
  world.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`;
}

function centreInitialView(){
  if(window.innerWidth <= 900) return;
  const vw = viewport.clientWidth;
  const worldFocusX = 1300;
  const worldFocusY = 840;
  view.x = vw/2 - worldFocusX*view.scale;
  view.y = Math.max(-180, viewport.clientHeight/2 - worldFocusY*view.scale);
  applyView();
}

function resetWorkspace(){
  view.scale = 0.72;
  centreInitialView();
}

function setTheme(theme, persist=true){
  document.documentElement.dataset.theme = theme;
  themeToggle.textContent = theme === "dark" ? "LIGHT" : "DARK";
  themeToggle.setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
  if(persist) localStorage.setItem("cv-theme", theme);
}

function initTheme(){
  const saved = localStorage.getItem("cv-theme");
  if(saved === "dark" || saved === "light"){
    setTheme(saved, false);
    return;
  }
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  setTheme(prefersDark ? "dark" : "light", false);
}

function buildHeaders(){
  const cols=document.querySelector(".sheet-columns");
  const rows=document.querySelector(".sheet-rows");
  for(let i=0;i<26;i++){
    const s=document.createElement("span");
    s.textContent=String.fromCharCode(65+i);
    s.style.left=`${46+i*92}px`; cols.appendChild(s);
  }
  for(let i=1;i<=90;i++){
    const s=document.createElement("span");
    s.textContent=i; s.style.top=`${12+(i-1)*24}px`; rows.appendChild(s);
  }
}

async function renderPdf(){
  pageGrid.innerHTML="";
  const pdf=await pdfjsLib.getDocument(PDF_URL).promise;

  for(let pageNo=1;pageNo<=pdf.numPages;pageNo++){
    const page=await pdf.getPage(pageNo);
    const base=page.getViewport({scale:1});
    const targetWidth=560;
    const viewportPdf=page.getViewport({scale:targetWidth/base.width});

    const holder=document.createElement("article");
    holder.className="cv-page";
    holder.dataset.page=String(pageNo);

    const canvas=document.createElement("canvas");
    const outputScale=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.floor(viewportPdf.width*outputScale);
    canvas.height=Math.floor(viewportPdf.height*outputScale);
    canvas.style.width=`${viewportPdf.width}px`;
    canvas.style.height=`${viewportPdf.height}px`;

    holder.appendChild(canvas);
    pageGrid.appendChild(holder);

    await page.render({
      canvasContext:canvas.getContext("2d"),
      viewport:viewportPdf,
      transform:outputScale!==1?[outputScale,0,0,outputScale,0,0]:null
    }).promise;
  }

  requestAnimationFrame(()=>{
    layoutHotspots();
    drawConnectors();
  });
}

function layoutHotspots(){
  hotspotLayer.innerHTML="";
  const br=board.getBoundingClientRect();
  const scale=view.scale || 1;

  HOTSPOTS.forEach(spec=>{
    const page=pageGrid.querySelector(`.cv-page[data-page="${spec.page}"]`);
    if(!page)return;
    const r=page.getBoundingClientRect();

    const h=document.createElement("div");
    h.className="hotspot";
    h.dataset.target=spec.id;

    h.style.left=`${(r.left-br.left)/scale + (r.width/scale)*spec.x}px`;
    h.style.top=`${(r.top-br.top)/scale + (r.height/scale)*spec.y}px`;
    h.style.width=`${(r.width/scale)*spec.w}px`;
    h.style.height=`${(r.height/scale)*spec.h}px`;
    hotspotLayer.appendChild(h);
  });
}

function getCard(id){
  if(id==="gbr") return document.querySelector(".polaroid");
  return document.querySelector(`[data-card="${id}"]`);
}

function drawConnectors(){
  const dr=desk.getBoundingClientRect();
  const inv=view.scale || 1;

  connectors.setAttribute("viewBox","0 0 1800 1700");
  connectors.innerHTML="";

  HOTSPOTS.forEach(spec=>{
    const h=hotspotLayer.querySelector(`[data-target="${spec.id}"]`);
    const card=getCard(spec.id);
    if(!h||!card)return;

    const hr=h.getBoundingClientRect();
    const cr=card.getBoundingClientRect();
    const cardIsLeft=cr.left<hr.left;

    const x1=((cardIsLeft?hr.left:hr.right)-dr.left)/inv;
    const y1=(hr.top+hr.height/2-dr.top)/inv;
    const x2=((cardIsLeft?cr.right:cr.left)-dr.left)/inv;
    const y2=(cr.top+Math.min(65,cr.height/2)-dr.top)/inv;
    const bend=x1+(x2-x1)*.48;

    const p=document.createElementNS("http://www.w3.org/2000/svg","path");
    p.setAttribute("d",`M ${x1} ${y1} H ${bend} V ${y2} H ${x2}`);
    if(spec.experimental)p.classList.add("experiment");
    connectors.appendChild(p);
  });
}


async function renderCertificateIntoFrame(cert){
  const holder = document.querySelector(`[data-cert-preview="${cert.id}"]`);
  if(!holder) return;

  try{
    const pdf = await pdfjsLib.getDocument(cert.file).promise;
    const page = await pdf.getPage(1);
    const base = page.getViewport({scale:1});

    // Every supplied certificate is landscape. The preview keeps the PDF's
    // real page ratio instead of forcing it into a predefined box.
    const targetWidth = 520;
    const viewportPdf = page.getViewport({scale:targetWidth / base.width});

    const canvas = document.createElement("canvas");
    const outputScale = Math.min(window.devicePixelRatio || 1, 1.75);
    canvas.width = Math.floor(viewportPdf.width * outputScale);
    canvas.height = Math.floor(viewportPdf.height * outputScale);
    canvas.style.aspectRatio = `${viewportPdf.width} / ${viewportPdf.height}`;

    await page.render({
      canvasContext: canvas.getContext("2d"),
      viewport: viewportPdf,
      transform: outputScale !== 1 ? [outputScale,0,0,outputScale,0,0] : null
    }).promise;

    holder.replaceChildren(canvas);
  }catch(error){
    if(!cert.optional){
      console.warn(`Could not render certificate ${cert.file}`, error);
    }
    const fallback = document.createElement("div");
    fallback.className = "certificate-frame__placeholder";
    fallback.textContent = cert.id === "cmilt" ? "CMILT.pdf" : "CERTIFICATE";
    holder.replaceChildren(fallback);
  }
}

async function renderCertificates(){
  await Promise.all(CERTIFICATES.map(renderCertificateIntoFrame));
}

function wireCards(){
  document.querySelectorAll("[data-card]").forEach(card=>{
    const id=card.dataset.card;
    const hotspot=()=>hotspotLayer.querySelector(`[data-target="${id}"]`);
    const on=()=>{card.classList.add("active");hotspot()?.classList.add("active")};
    const off=()=>{card.classList.remove("active");hotspot()?.classList.remove("active")};
    card.addEventListener("mouseenter",on);
    card.addEventListener("mouseleave",off);
    card.addEventListener("focus",on);
    card.addEventListener("blur",off);
  });
}

/* Camera zoom around cursor */
viewport.addEventListener("wheel",event=>{
  if(window.innerWidth<=900)return;
  event.preventDefault();

  const rect=viewport.getBoundingClientRect();
  const mouseX=event.clientX-rect.left;
  const mouseY=event.clientY-rect.top;
  const worldX=(mouseX-view.x)/view.scale;
  const worldY=(mouseY-view.y)/view.scale;

  const factor=Math.exp(-event.deltaY*0.00125);
  const next=Math.min(view.maxScale,Math.max(view.minScale,view.scale*factor));

  view.scale=next;
  view.x=mouseX-worldX*next;
  view.y=mouseY-worldY*next;
  applyView();

  requestAnimationFrame(()=>{layoutHotspots();drawConnectors()});
},{passive:false});

/* Camera pan on empty spreadsheet */
let cameraPan=null;

viewport.addEventListener("pointerdown",event=>{
  if(window.innerWidth<=900)return;
  if(event.button!==0)return;
  if(event.target.closest("[data-draggable],a,button"))return;

  cameraPan={
    id:event.pointerId,
    sx:event.clientX, sy:event.clientY,
    vx:view.x, vy:view.y
  };
  viewport.classList.add("is-panning");
  viewport.setPointerCapture?.(event.pointerId);
});

viewport.addEventListener("pointermove",event=>{
  if(!cameraPan || event.pointerId!==cameraPan.id)return;
  view.x=cameraPan.vx+(event.clientX-cameraPan.sx);
  view.y=cameraPan.vy+(event.clientY-cameraPan.sy);
  applyView();
});

function endCameraPan(event){
  if(!cameraPan || event.pointerId!==cameraPan.id)return;
  cameraPan=null;
  viewport.classList.remove("is-panning");
  try{viewport.releasePointerCapture?.(event.pointerId)}catch{}
}
viewport.addEventListener("pointerup",endCameraPan);
viewport.addEventListener("pointercancel",endCameraPan);

/* Independently draggable surface objects */
function registerDraggable(el,index){
  const key=el.dataset.card || el.dataset.cert || `free-${index}`;
  objectDefaults.set(key,{
    transform:el.style.transform || "",
    left:el.offsetLeft,
    top:el.offsetTop
  });
  objectOffsets.set(key,{x:0,y:0});

  let drag=null;
  let suppressClick=false;

  el.addEventListener("pointerdown",event=>{
    if(window.innerWidth<=900)return;
    if(event.button!==0)return;
    const interactiveChild = event.target.closest("button, a");
    if(interactiveChild && interactiveChild !== el && !el.matches("a[data-draggable='true']")) return;

    event.stopPropagation();
    const current=objectOffsets.get(key) || {x:0,y:0};
    drag={
      id:event.pointerId,
      sx:event.clientX,
      sy:event.clientY,
      ox:current.x,
      oy:current.y
    };
    suppressClick=false;
    el.classList.add("dragging");
    el.setPointerCapture?.(event.pointerId);
  });

  el.addEventListener("pointermove",event=>{
    if(!drag || event.pointerId!==drag.id)return;
    const dx=(event.clientX-drag.sx)/view.scale;
    const dy=(event.clientY-drag.sy)/view.scale;
    if(Math.abs(dx)+Math.abs(dy)>3)suppressClick=true;

    const next={x:drag.ox+dx,y:drag.oy+dy};
    objectOffsets.set(key,next);
    el.style.translate=`${next.x}px ${next.y}px`;
    drawConnectors();
  });

  function end(event){
    if(!drag || event.pointerId!==drag.id)return;
    drag=null;
    el.classList.remove("dragging");
    try{el.releasePointerCapture?.(event.pointerId)}catch{}
  }

  el.addEventListener("pointerup",end);
  el.addEventListener("pointercancel",end);

  el.addEventListener("click",event=>{
    if(suppressClick){
      event.preventDefault();
      event.stopPropagation();
      suppressClick=false;
    }
  },true);
}

function resetObjects(){
  document.querySelectorAll("[data-draggable]").forEach((el,index)=>{
    const key=el.dataset.card || el.dataset.cert || `free-${index}`;
    objectOffsets.set(key,{x:0,y:0});
    el.style.translate="0px 0px";
  });
  drawConnectors();
}

themeToggle.addEventListener("click",()=>{
  const current=document.documentElement.dataset.theme || "light";
  setTheme(current==="dark"?"light":"dark");
});
resetView.addEventListener("click",resetWorkspace);
resetLayout.addEventListener("click",resetObjects);

let resizeRaf=0;
window.addEventListener("resize",()=>{
  cancelAnimationFrame(resizeRaf);
  resizeRaf=requestAnimationFrame(()=>{
    if(window.innerWidth>900)centreInitialView();
    layoutHotspots();
    drawConnectors();
  });
});

initTheme();
buildHeaders();
wireCards();
document.querySelectorAll("[data-draggable]").forEach(registerDraggable);
applyView();
renderCertificates();

renderPdf()
  .then(()=>{
    centreInitialView();
    setTimeout(()=>{layoutHotspots();drawConnectors()},60);
  })
  .catch(error=>{
    console.error(error);
    pageGrid.innerHTML=`
      <div style="grid-column:1/-1;background:#fff;color:#222;padding:30px;border:1px solid #bbb;box-shadow:0 20px 45px rgba(0,0,0,.18)">
        <h2>CV PDF not found</h2>
        <p>Place your PDF at <code>cv/CV_SimonTaylor.pdf</code>, then refresh.</p>
      </div>`;
  });
