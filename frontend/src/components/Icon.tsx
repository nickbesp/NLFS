// Material Symbols Outlined glyph (font loaded in the root layout). Decorative only.
export default function Icon({ name, filled = false, className }: { name: string; filled?: boolean; className?: string }) {
  return (
    <span className={`icon${filled ? " filled" : ""}${className ? ` ${className}` : ""}`} aria-hidden="true">
      {name}
    </span>
  );
}
