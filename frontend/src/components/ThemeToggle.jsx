import { useTheme } from '../contexts/ThemeContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      className="relative w-9 h-9 rounded-full border border-border bg-card/60 backdrop-blur-sm flex items-center justify-center transition-all hover:border-teal/40"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? (
        <span className="text-lg">☀️</span>
      ) : (
        <span className="text-lg">🌙</span>
      )}
    </button>
  );
}