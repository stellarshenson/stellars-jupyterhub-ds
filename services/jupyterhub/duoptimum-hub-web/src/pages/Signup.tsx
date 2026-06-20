/* Sign up - standalone screen, NativeAuthenticator semantics: a new account is
 * created pending admin authorisation. Mocked: a valid submit shows the pending
 * notice instead of signing in. */
import { useEffect, useState } from 'react'
import { Button, Form, Input } from 'antd'
import { Link } from 'react-router-dom'
import { Notice } from '../components/Notice'
import { isMock } from '../services/dataMode'
import { hubUrl, portalAssetBase } from '../services/hub/client'
import { hubName } from '../app/capabilities'

export default function Signup() {
  const [done, setDone] = useState(false)
  const logoSrc = `${portalAssetBase()}brand/jh-logo.svg`
  useEffect(() => {
    if (!isMock()) window.location.assign(hubUrl('/signup'))
  }, [])
  if (!isMock()) return null
  return (
    <div className="doh-auth">
      <div className="doh-auth-card">
        <div className="doh-auth-brand"><img src={logoSrc} alt="Duoptimum Hub" /></div>
        <h1 className="doh-auth-title">Create an Account</h1>
        <p className="doh-auth-sub">{hubName()}</p>
        {done && (
          <div style={{ marginBottom: 16 }}>
            <Notice type="success">Account created - an administrator must authorise it before you can sign in.</Notice>
          </div>
        )}
        <Form layout="vertical" requiredMark={false} onFinish={() => setDone(true)}>
          <Form.Item label="Username" name="username" rules={[{ required: true, message: 'Choose a username' }]}>
            <Input autoFocus placeholder="username" autoComplete="username" />
          </Form.Item>
          <Form.Item label="Password" name="password" rules={[{ required: true, message: 'Choose a password' }]}>
            <Input.Password placeholder="password" autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            label="Repeat password"
            name="repeat"
            dependencies={['password']}
            rules={[
              { required: true, message: 'Repeat your password' },
              ({ getFieldValue }) => ({
                validator: (_, value) => (!value || value === getFieldValue('password') ? Promise.resolve() : Promise.reject(new Error('Passwords do not match'))),
              }),
            ]}
          >
            <Input.Password placeholder="repeat password" autoComplete="new-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>Create Account</Button>
        </Form>
        <div className="doh-auth-foot">Already have an account? <Link to="/login">Sign in</Link></div>
      </div>
    </div>
  )
}
