export default function SuggestionBullets({ bullets }) {
  if (!bullets || bullets.length === 0) return null

  return (
    <div className="flex gap-2 max-w-2xl w-full px-1 flex-wrap">
      {bullets.map((bullet, i) => (
        <span
          key={i}
          className="bg-white/10 text-white text-xs rounded-lg px-3 py-1 backdrop-blur-sm border border-white/10 whitespace-nowrap"
        >
          {bullet}
        </span>
      ))}
    </div>
  )
}
