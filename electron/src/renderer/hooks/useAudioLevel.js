import { useState, useEffect } from 'react'

export function useAudioLevel() {
  const [level, setLevel] = useState(0)

  useEffect(() => {
    window.closer.onAudioLevel((l) => setLevel(l))
  }, [])

  return level
}
