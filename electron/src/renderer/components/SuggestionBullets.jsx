import { useState, useEffect } from 'react'

function Bullet({ text }) {
  const [opacity, setOpacity] = useState(0)

  useEffect(() => {
    const id = requestAnimationFrame(() => setOpacity(1))
    return () => cancelAnimationFrame(id)
  }, [])

  return (
    <span
      style={{ opacity, transition: 'opacity 300ms ease-in' }}
      className="bg-white/10 text-white text-xs rounded-lg px-3 py-1 backdrop-blur-sm border border-white/10 whitespace-nowrap"
    >
      {text}
    </span>
  )
}

export default function SuggestionBullets({ bullets }) {
  if (!bullets || bullets.length === 0) return null

  return (
    <div className="flex gap-2 max-w-2xl w-full px-1 flex-wrap">
      {bullets.map((bullet, i) => (
        <Bullet key={`${i}:${bullet}`} text={bullet} />
      ))}
    </div>
  )
}
