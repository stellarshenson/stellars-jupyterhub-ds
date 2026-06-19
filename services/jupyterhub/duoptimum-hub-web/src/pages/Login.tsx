/* Sign in - standalone screen outside the app shell. NativeAuthenticator-style
 * username + password. Mock mode: a valid submit drops the operator on Home.
 * Live mode: real auth is owned by the hub, so this screen hands off to the
 * hub's NativeAuthenticator login page. */
import { useEffect } from 'react'
import { Button, Form, Input } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import { isMock } from '../services/dataMode'
import { hubUrl, portalAssetBase } from '../services/hub/client'

export default function Login() {
  const navigate = useNavigate()
  const logoSrc = `${portalAssetBase()}brand/jh-logo.svg`
  useEffect(() => {
    if (!isMock()) window.location.assign(hubUrl('/login'))
  }, [])
  if (!isMock()) return null
  return (
    <div className="oh-auth">
      <div className="oh-auth-card">
        <div className="oh-auth-brand"><img src={logoSrc} alt="Duoptimum Hub" /></div>
        <h1 className="oh-auth-title">Sign In</h1>
        <p className="oh-auth-sub">Duoptimum Hub</p>
        <Form layout="vertical" requiredMark={false} onFinish={() => navigate('/home')}>
          <Form.Item label="Username" name="username" rules={[{ required: true, message: 'Enter your username' }]}>
            <Input autoFocus placeholder="username" autoComplete="username" />
          </Form.Item>
          <Form.Item label="Password" name="password" rules={[{ required: true, message: 'Enter your password' }]}>
            <Input.Password placeholder="password" autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>Sign In</Button>
        </Form>
        <div className="oh-auth-foot">New here? <Link to="/signup">Create an account</Link></div>
      </div>
    </div>
  )
}
