import { useState, useEffect } from 'react'

const WAV_HEADER_BYTES = 44

export function useAudioLevel() {
  const [level, setLevel] = useState(0)

  useEffect(() => {
    window.closer.onAudioBinary((buf) => {
      // buf arrives as Uint8Array via IPC structured clone
      if (buf.byteLength <= WAV_HEADER_BYTES) return
      const view = new DataView(buf.buffer, buf.byteOffset + WAV_HEADER_BYTES)
      const sampleCount = (buf.byteLength - WAV_HEADER_BYTES) / 2
      let sumSq = 0
      for (let i = 0; i < sampleCount; i++) {
        const s = view.getInt16(i * 2, true) / 32768
        sumSq += s * s
      }
      const rms = Math.sqrt(sumSq / sampleCount)
      setLevel(Math.min(rms * 5, 1.0))
    })
  }, [])

  return level
}
