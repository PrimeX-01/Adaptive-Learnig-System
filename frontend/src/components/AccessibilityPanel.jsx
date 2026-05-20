import { useState } from 'react';
export default function AccessibilityPanel() {
  const [open, setOpen]   = useState(false);
  const [size, setSize]   = useState('medium');
  const [hc,   setHC]     = useState(false);
  const sizes = { small:'13px', medium:'15px', large:'18px' };
  document.documentElement.style.fontSize = sizes[size];
  if (hc) document.documentElement.classList.add('high-contrast');
  else    document.documentElement.classList.remove('high-contrast');
  return (
    <div className='fixed bottom-6 right-6 z-50'>
      <button onClick={()=>setOpen(o=>!o)} className='w-10 h-10 rounded-xl bg-card border border-border hover:border-teal/50 flex items-center justify-center text-muted hover:text-teal transition-all shadow-card'>♿</button>
      {open && (<div className='absolute bottom-12 right-0 w-56 card p-4 shadow-teal-glow'>
        <p className='text-primary text-xs font-semibold mb-3'>Accessibility</p>
        <p className='text-muted text-xs mb-2'>Text Size</p>
        <div className='flex gap-1 mb-4'>{['small','medium','large'].map(s=><button key={s} onClick={()=>setSize(s)} className={`flex-1 py-1.5 rounded-lg text-xs capitalize ${size===s?'bg-teal text-app font-semibold':'bg-input text-muted hover:text-primary'}`}>{s}</button>)}</div>
        <label className='flex items-center gap-2 text-xs text-muted cursor-pointer'><input type='checkbox' checked={hc} onChange={e=>setHC(e.target.checked)} className='rounded accent-teal' />High Contrast</label>
      </div>)}
    </div>
  );
}
