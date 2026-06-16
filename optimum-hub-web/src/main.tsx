import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'antd/dist/reset.css'
import './styles/global.css'
import App from './App'
import AuthApp from './app/AuthApp'

// The hub serves the overridden login/signup templates with window.jhdata.authPage
// set; render just the auth screen (no router/data layer) there, else the full app.
const authPage = typeof window !== 'undefined' ? window.jhdata?.authPage : undefined

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {authPage ? <AuthApp /> : <App />}
  </StrictMode>,
)
