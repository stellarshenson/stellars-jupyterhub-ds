/* Sign up - account creation is owned by the hub, so this route immediately
 * hands off to the hub's NativeAuthenticator signup page. */
import { useEffect } from 'react'
import { hubUrl } from '../services/hub/client'

export default function Signup() {
  useEffect(() => {
    window.location.assign(hubUrl('/signup'))
  }, [])
  return null
}
