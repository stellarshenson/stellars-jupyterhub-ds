/* Sign in - real auth is owned by the hub, so this route immediately hands off
 * to the hub's NativeAuthenticator login page. */
import { useEffect } from 'react'
import { hubUrl } from '../services/hub/client'

export default function Login() {
  useEffect(() => {
    window.location.assign(hubUrl('/login'))
  }, [])
  return null
}
