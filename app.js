const state={elements:[],patterns:[],rules:[],rng:Math.random};
const $=id=>document.getElementById(id);

async function loadJSON(path){
  const r=await fetch(path,{cache:"no-store"});
  if(!r.ok) throw new Error(`No se pudo cargar ${path} (${r.status})`);
  return r.json();
}
async function loadData(){
  const [elements,patterns,rules]=await Promise.all([
    loadJSON("data/elements.json"),loadJSON("data/patterns.json"),loadJSON("data/rules.json")
  ]);
  if(!Array.isArray(elements)||!Array.isArray(patterns)||!Array.isArray(rules))
    throw new Error("Los archivos JSON no tienen el formato esperado.");
  state.elements=elements;
  state.patterns=patterns.map(p=>({
    ...p,
    slots:Array.isArray(p.slots)?p.slots:[],
    modes:Array.isArray(p.modes)?p.modes:["documental","vasco","historico","proto"],
    weight:Number(p.weight??1),
    name:p.name??p.id??"Patrón",
    meaning_template:p.meaning_template??"{A}"
  })).filter(p=>p.slots.length);
  state.rules=rules;
  document.getElementById("element-count").textContent=elements.length;
}
function choice(a,w){if(!a.length)return null;let ws=a.map(x=>Math.max(.01,Number(w(x))||.01)),n=Math.random()*ws.reduce((a,b)=>a+b,0);for(let i=0;i<a.length;i++){n-=ws[i];if(n<=0)return a[i]}return a.at(-1)}
function candidates(slot,mode){
  return state.elements.filter(e=>{
    const tags=Array.isArray(e.combination_tags)?e.combination_tags:[];
    if(!(slot===e.category||tags.includes(slot)||slot===e.kind))return false;
    if(mode==="documental"&&e.antiquity==="MODERNA")return false;
    if(Number(e.productivity)<=.25&&e.kind==="LEXEMA")return false;
    return true;
  });
}
function element(slot,mode){
  const exact=state.elements.find(e=>e.id===slot);
  if(exact)return exact;
  const a=candidates(slot,mode);
  if(!a.length)throw new Error(`No hay elementos compatibles con "${slot}".`);
  return choice(a,e=>e.productivity);
}
function compatible(a,b){
  if(!a||!b)return false;
  if(a.kind==="SUFIJO"&&b.kind==="SUFIJO")return false;
  if(["AGA","ETA","DI","TI","TEGI"].includes(a.id))return false;
  const tags=Array.isArray(a.combination_tags)?a.combination_tags:[];
  if(["DI","TI"].includes(b.id)&&!tags.includes("VEGETACION"))return false;
  if(b.id==="TEGI"&&!tags.some(x=>["ASENTAMIENTO","ACTIVIDAD","PERSONA","OFICIO","LEXEMA"].includes(x)))return false;
  if(["AGA","ETA"].includes(b.id)&&!tags.some(x=>["VEGETACION","RELIEVE","AGUA","FAUNA","ASENTAMIENTO","LEXEMA_GEOGRAFICO"].includes(x)))return false;
  return true;
}
function join(form,b){
  const applied=[];
  if(["AGA","ETA"].includes(b.id))return{form:form+b.form,applied};
  if(/(di|gi)$/.test(form)){form=form.replace(/(di|gi)$/,"t");applied.push("F01_DI_GI_TO_T")}
  if(/[eou]$/.test(form)){form=form.replace(/[eou]$/,"a");applied.push("F03_FINAL_VOWEL_TO_A")}
  if(/n$/.test(form)){form=form.replace(/n$/,"r");applied.push("F04_FINAL_N_TO_R")}
  if(/(ra|re|ri)$/.test(form)){form=form.replace(/r$/,"l");applied.push("F05_R_TO_L")}
  return{form:form+b.form,applied};
}
function historical(form,mode){
  const applied=[];
  if((mode==="historico"||mode==="proto")&&form.startsWith("h")&&Math.random()<.35){form=form.slice(1);applied.push("H01_INITIAL_H_LOSS_OPTIONAL")}
  if(mode==="proto"&&Math.random()<.12){form=form.replace(/rr/g,"r");applied.push("P01_RR_SIMPLIFICATION_EXPERIMENTAL")}
  return{form,applied};
}
function generate(mode){
  const explicit=state.patterns.filter(p=>{
    const ms=Array.isArray(p.modes)&&p.modes.length
      ? p.modes : ["documental","vasco","historico","proto"];
    return Array.isArray(p.slots)&&p.slots.length&&ms.includes(mode);
  });
  const ps=explicit.length ? explicit :
    state.patterns.filter(p=>Array.isArray(p.slots)&&p.slots.length);

  if(!ps.length) throw new Error("patterns.json no contiene patrones utilizables.");

  const p=choice(ps,x=>x.weight);
  if(!p||!Array.isArray(p.slots)||!p.slots.length)
    throw new Error("El patrón seleccionado no tiene slots válidos.");

  for(let attempt=0;attempt<100;attempt++){
    const c=p.slots.map(slot=>element(slot,mode));
    if(!c.slice(0,-1).every((x,i)=>compatible(x,c[i+1]))) continue;

    let form=c[0].form, applied=[];
    for(let i=1;i<c.length;i++){
      const j=join(form,c[i]);
      form=j.form; applied.push(...j.applied);
    }

    const h=historical(form,mode);
    form=h.form; applied.push(...h.applied);

    let meaning=p.meaning_template;
    c.forEach((x,i)=>{
      meaning=meaning.replaceAll(`{${String.fromCharCode(65+i)}}`,x.meaning);
    });

    return {
      toponym:form[0].toUpperCase()+form.slice(1),
      meaning, pattern:p.name, components:c, rules:applied, mode
    };
  }
  throw new Error(`No se pudo resolver el patrón "${p.name}".`);
}
function esc(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
function render(rs){
  document.getElementById("results").innerHTML=rs.map(r=>`
  <article class="result-card"><div class="result-top"><div>
  <p class="meta">${esc(r.mode)} · ${esc(r.pattern)}</p><h2 class="toponym">${esc(r.toponym)}</h2>
  </div><button class="copy" data-copy="${esc(r.toponym)}">Copiar</button></div>
  <p class="meaning">${esc(r.meaning)}</p><div class="components">${r.components.map(c=>`<span class="component"><strong>${esc(c.form)}</strong> — ${esc(c.meaning)}</span>`).join("")}</div>
  <details><summary>Ver reglas y análisis</summary>
  <p class="small">Una construcción generativa no implica que exista como topónimo histórico documentado.</p>
  ${r.rules.length?r.rules.map(x=>`<div class="rule">${esc(x)}</div>`).join(""):"<p class='small'>No se aplicaron alternancias.</p>"}
  </details></article>`).join("");
  document.querySelectorAll(".copy").forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(b.dataset.copy)}catch(e){}b.textContent="¡Copiado!";setTimeout(()=>b.textContent="Copiar",1000)});
}
document.getElementById("generate").onclick=()=>{
  try{let n=Math.min(100,Math.max(1,Number(document.getElementById("amount").value)||1));let m=document.getElementById("mode").value;render(Array.from({length:n},()=>generate(m)))}
  catch(e){console.error(e);document.getElementById("results").innerHTML=`<div class="panel empty">Error: ${esc(e.message)}</div>`}
};
loadData().then(()=>render([generate("vasco")])).catch(e=>document.getElementById("results").innerHTML=`<div class="panel empty">No se han podido cargar los datos.<br><br>${esc(e.message)}</div>`);
