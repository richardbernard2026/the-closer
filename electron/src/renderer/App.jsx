import { useState, useEffect } from 'react'
import LiveHUD from './components/LiveHUD'

export default function App() {
  const [isListening, setIsListening] = useState(false)
  const [bridgeConnected, setBridgeConnected] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [suggestions, setSuggestions] = useState([])

  useEffect(() => {
    window.closer.onBridgeStatus(({ connected }) => setBridgeConnected(connected))
    window.closer.onTranscriptUpdate((text) => setTranscript(text))
    window.closer.onSuggestionUpdate((bullets) => setSuggestions(bullets))
    window.closer.onToggleListening((isCapturing) => {
      if (isCapturing === null) {
        setIsListening((prev) => {
          const next = !prev
          next ? window.closer.startListening() : window.closer.stopListening()
          return next
        })
      } else {
        setIsListening(isCapturing)
      }
    })
  }, [])

  async function handleToggle() {
    if (isListening) {
      await window.closer.stopListening()
      setIsListening(false)
    } else {
      const result = await window.closer.startListening()
      if (result?.success) setIsListening(true)
    }
  }

  return (
    <LiveHUD
      isListening={isListening}
      bridgeConnected={bridgeConnected}
      transcript={transcript}
      suggestions={suggestions}
      onToggle={handleToggle}
    />
  )
}
