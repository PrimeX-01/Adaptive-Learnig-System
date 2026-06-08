import { useEffect, useRef } from 'react';

export default function CustomCursor() {
  const cursorDot = useRef(null);
  const cursorRing = useRef(null);
  const isMobile = useRef(false);

  useEffect(() => {
    // Check for touch device
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
      isMobile.current = true;
      return;
    }

    const dot = cursorDot.current;
    const ring = cursorRing.current;
    if (!dot || !ring) return;

    let mouseX = 0, mouseY = 0;
    let ringX = 0, ringY = 0;

    const onMouseMove = (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      dot.style.left = `${mouseX}px`;
      dot.style.top = `${mouseY}px`;
    };

    const animateRing = () => {
      ringX += (mouseX - ringX) * 0.12;
      ringY += (mouseY - ringY) * 0.12;
      ring.style.left = `${ringX}px`;
      ring.style.top = `${ringY}px`;
      requestAnimationFrame(animateRing);
    };

    window.addEventListener('mousemove', onMouseMove);
    animateRing();

    const interactive = document.querySelectorAll('a, button, input, select, .card-hover, .btn-primary, .btn-ghost');
    const onMouseEnter = () => {
      dot.style.width = '16px';
      dot.style.height = '16px';
      ring.style.width = '60px';
      ring.style.height = '60px';
    };
    const onMouseLeave = () => {
      dot.style.width = '10px';
      dot.style.height = '10px';
      ring.style.width = '40px';
      ring.style.height = '40px';
    };
    interactive.forEach(el => {
      el.addEventListener('mouseenter', onMouseEnter);
      el.addEventListener('mouseleave', onMouseLeave);
    });

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      interactive.forEach(el => {
        el.removeEventListener('mouseenter', onMouseEnter);
        el.removeEventListener('mouseleave', onMouseLeave);
      });
    };
  }, []);

  if (isMobile.current) return null;

  return (
    <>
      <div ref={cursorDot} className="fixed w-[10px] h-[10px] bg-teal rounded-full pointer-events-none z-[9999] mix-blend-difference transform -translate-x-1/2 -translate-y-1/2 transition-all duration-75" />
      <div ref={cursorRing} className="fixed w-[40px] h-[40px] border border-teal rounded-full pointer-events-none z-[9998] mix-blend-difference transform -translate-x-1/2 -translate-y-1/2 transition-all duration-150" />
    </>
  );
}