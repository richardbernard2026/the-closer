import { useAudioLevel } from '../hooks/useAudioLevel'

const BAR_COUNT = 14
const OFFSETS = Array.from({ length: BAR_COUNT }, (_, i) => Math.abs(Math.sin(i * 1.7)))

export default function Waveform({ isListening }) {
  const level = useAudioLevel()

  return (
    <div className="flex items-center gap-px h-5 shrink-0">
      {OFFSETS.map((offset, i) => {
        const height = isListening
          ? Math.max(0.15, Math.min(level + offset * 0.3, 1.0))
          : 0.15
        return (
          <div
            key={i}
            className="w-0.5 rounded-full bg-green-400/80 transition-all duration-75"
            style={{ height: `${height * 100}%` }}
          />
        )
      })}
    </div>
  )
}
