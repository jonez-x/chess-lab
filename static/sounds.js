'use strict';
// Short, locally synthesized wooden taps; no recordings or network requests.
window.ChessSounds = class {
  constructor(){this.context=null;}
  unlock(){
    try {
      const Audio=window.AudioContext||window.webkitAudioContext;
      if(!Audio)return;
      this.context ||= new Audio();
      if(this.context.state==='suspended')this.context.resume().catch(()=>{});
    } catch (_) { /* Audio must never interrupt a game. */ }
  }
  play(capture=false, delay=0){
    const ctx=this.context;
    if(!ctx||ctx.state!=='running')return;
    const tap=(offset,frequency,volume,duration)=>{
      const start=ctx.currentTime+delay+offset;
      const tone=ctx.createOscillator(),gain=ctx.createGain();
      tone.type='sine';tone.frequency.setValueAtTime(frequency,start);
      tone.frequency.exponentialRampToValueAtTime(frequency*.55,start+duration);
      gain.gain.setValueAtTime(.0001,start);gain.gain.exponentialRampToValueAtTime(volume,start+.002);
      gain.gain.exponentialRampToValueAtTime(.0001,start+duration);
      tone.connect(gain).connect(ctx.destination);tone.start(start);tone.stop(start+duration+.01);
      tone.onended=()=>{tone.disconnect();gain.disconnect();};
    };
    tap(0,capture?300:520,capture?.16:.11,capture?.12:.075);
    if(capture)tap(.065,690,.08,.055);
  }
};
