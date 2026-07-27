import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

// NOTE: no <StrictMode> on purpose — the CulinAI logic is imperative and
// initializes the DOM once in an effect; StrictMode's double-invoke would
// re-run init against a torn-down node. Re-enable once the logic is componentized.
createRoot(document.getElementById('root')).render(<App />)
