/* GBR deterministic audio-time visual driver. */
class GBRDanceController {
  constructor(audio, playback, hooks={}) {
    this.audio=audio; this.playback=playback||{}; this.dance=this.playback.dance||{}; this.hooks=hooks;
    this.frameHz=Number(this.dance.frame_hz||10); this.scale=Number(this.dance.scale||255);
    this.frames=Array.isArray(this.dance.frames)?this.dance.frames:[]; this.beats=Array.isArray(this.dance.beats)?this.dance.beats:[];
    this.events=[...(Array.isArray(this.dance.events)?this.dance.events:[]),...(Array.isArray(this.playback.manual_events)?this.playback.manual_events:[])].sort((a,b)=>Number(a.time||0)-Number(b.time||0));
    this.running=false; this.raf=0; this.lastTime=-1; this.beatCursor=0; this.eventCursor=0;
    this._tick=this._tick.bind(this); this._seek=this._seek.bind(this); audio.addEventListener('seeked',this._seek); audio.addEventListener('loadedmetadata',this._seek);
  }
  destroy(){this.stop();this.audio.removeEventListener('seeked',this._seek);this.audio.removeEventListener('loadedmetadata',this._seek)}
  start(){if(this.running)return;this.running=true;this._reset(Number(this.audio.currentTime||0));this.raf=requestAnimationFrame(this._tick)}
  stop(){this.running=false;if(this.raf)cancelAnimationFrame(this.raf);this.raf=0}
  _seek(){this._reset(Number(this.audio.currentTime||0))}
  _lower(list,t){let lo=0,hi=list.length;while(lo<hi){const m=(lo+hi)>>1,x=list[m],v=Array.isArray(x)?Number(x[0]||0):Number(x.time||0);if(v<t)lo=m+1;else hi=m}return lo}
  _reset(t){this.lastTime=t;this.beatCursor=this._lower(this.beats,t);this.eventCursor=this._lower(this.events,t)}
  reactionFor(item){const r=item?.reaction||{},a=r.auto||{},m=r.manual;if(m==null)return a;if(typeof m==='number')return {...a,pulsar:m};if(typeof m==='object')return {...a,...m};return a}
  _frame(t){if(!this.frames.length||this.frameHz<=0)return {energy:0,bass:0,brightness:0,change:0};const i=Math.max(0,Math.min(this.frames.length-1,Math.floor(t*this.frameHz))),f=this.frames[i]||[0,0,0,0],s=this.scale||255;return {energy:Number(f[0]||0)/s,bass:Number(f[1]||0)/s,brightness:Number(f[2]||0)/s,change:Number(f[3]||0)/s}}
  _emit(list,cursorName,from,to,hook){let c=this[cursorName];while(c<list.length){const x=list[c],t=Array.isArray(x)?Number(x[0]||0):Number(x.time||0);if(t>to)break;if(t>=from&&typeof this.hooks[hook]==='function')this.hooks[hook](x);c++}this[cursorName]=c}
  _tick(){if(!this.running)return;const t=Number(this.audio.currentTime||0);if(this.lastTime<0||t<this.lastTime-.25||t>this.lastTime+1)this._reset(t);const state=this._frame(t);state.time=t;if(typeof this.hooks.onFrame==='function')this.hooks.onFrame(state);if(!this.audio.paused&&!this.audio.ended){this._emit(this.beats,'beatCursor',this.lastTime,t,'onBeat');this._emit(this.events,'eventCursor',this.lastTime,t,'onEvent')}this.lastTime=t;this.raf=requestAnimationFrame(this._tick)}
}
if(typeof window!=='undefined')window.GBRDanceController=GBRDanceController;
if(typeof module!=='undefined'&&module.exports)module.exports=GBRDanceController;
