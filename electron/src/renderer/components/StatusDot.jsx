export default function StatusDot({ isListening, bridgeConnected }) {
  const color = !bridgeConnected
    ? 'bg-red-500'
    : isListening
    ? 'bg-green-400'
    : 'bg-yellow-400'

  return (
    <div className="relative flex items-center justify-center w-3 h-3 shrink-0">
      <div className={`w-2.5 h-2.5 rounded-full ${color}`} />
      {isListening && bridgeConnected && (
        <div className="absolute w-2.5 h-2.5 rounded-full bg-green-400 animate-ping opacity-75" />
      )}
    </div>
  )
}
