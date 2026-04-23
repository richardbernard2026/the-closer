import StatusDot from './StatusDot'
import Waveform from './Waveform'
import SuggestionBullets from './SuggestionBullets'

export default function LiveHUD({ isListening, bridgeConnected, transcript, suggestions, onToggle }) {
  return (
    <div className="flex flex-col items-center w-full px-4 pt-2 gap-1.5">
      <div className="flex items-center gap-3 w-full max-w-2xl bg-black/75 rounded-xl px-4 py-2 backdrop-blur-sm border border-white/5">
        <StatusDot isListening={isListening} bridgeConnected={bridgeConnected} />
        <Waveform isListening={isListening} />
        <p className="flex-1 min-w-0 text-white/40 text-xs truncate">
          {transcript || (bridgeConnected ? 'Ready' : 'Bridge offline')}
        </p>
        <button
          onClick={onToggle}
          className="text-xs text-white/60 hover:text-white transition-colors px-2 py-0.5 rounded border border-white/15 hover:border-white/40 shrink-0"
        >
          {isListening ? 'Stop' : 'Start'}
        </button>
      </div>
      <SuggestionBullets bullets={suggestions} />
    </div>
  )
}
