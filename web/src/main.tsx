import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
// Initialize theme before first render (sets CSS vars on :root)
import "./stores/theme"
import App from "./App"

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <App />
    </StrictMode>,
)
