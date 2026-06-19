/* Live auth screens, rendered when the hub serves the overridden login/signup
 * templates (window.jhdata.authPage). These are the real auth UI: antd forms that
 * do a native browser POST to NativeAuth's unchanged endpoints (/hub/login,
 * /hub/signup), so the proven server-side auth + redirect flow is preserved and
 * we only replace the presentation. Rendered outside the router (the auth pages
 * live at /hub/login, outside the /hub/portal basename). */
import { Alert, Button, Form, Input } from 'antd'
import { ThemeProvider } from '../theme/ThemeProvider'
import { Notice } from '../components/Notice'
import { hubUrl, portalAssetBase, xsrfToken } from '../services/hub/client'

// Native browser POST so the hub's 302 redirect + Set-Cookie work as on the stock
// form (fetch can't follow the auth redirect / set the session cookie cleanly).
function postForm(action: string, fields: Record<string, string>) {
  const f = document.createElement('form')
  f.method = 'POST'
  f.action = action
  for (const [k, v] of Object.entries(fields)) {
    if (v === undefined || v === null) continue
    const i = document.createElement('input')
    i.type = 'hidden'
    i.name = k
    i.value = v
    f.appendChild(i)
  }
  document.body.appendChild(f)
  f.submit()
}

function Brand() {
  return (
    <div className="doh-auth-brand">
      <img src={`${portalAssetBase()}brand/jh-logo.svg`} alt="Duoptimum Hub" />
    </div>
  )
}

function AuthLogin() {
  const error = window.jhdata?.authError || ''
  const next = window.jhdata?.authNext || ''
  const submit = (v: { username: string; password: string }) =>
    postForm(`${hubUrl('/login')}${next ? `?next=${next}` : ''}`, { username: v.username, password: v.password, _xsrf: xsrfToken() })
  return (
    <div className="doh-auth">
      <div className="doh-auth-card">
        <Brand />
        <h1 className="doh-auth-title">Sign In</h1>
        <p className="doh-auth-sub">Duoptimum Hub</p>
        {error && <div style={{ marginBottom: 16 }}><Alert type="error" showIcon message={error} /></div>}
        <Form layout="vertical" requiredMark={false} onFinish={submit}>
          <Form.Item label="Username" name="username" rules={[{ required: true, message: 'Enter your username' }]}>
            <Input autoFocus placeholder="username" autoComplete="username" />
          </Form.Item>
          <Form.Item label="Password" name="password" rules={[{ required: true, message: 'Enter your password' }]}>
            <Input.Password placeholder="password" autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>Sign In</Button>
        </Form>
        <div className="doh-auth-foot">New here? <a href={hubUrl('/signup')}>Create an account</a></div>
      </div>
    </div>
  )
}

function AuthSignup() {
  const message = window.jhdata?.authMessage || ''
  const alert = window.jhdata?.authAlert || ''
  const askEmail = !!window.jhdata?.askEmail
  // NativeAuth alert classes -> notice tone
  const tone = alert.includes('success') ? 'success' : alert.includes('danger') ? 'error' : 'info'
  const submit = (v: { username: string; email?: string; password: string; repeat: string }) =>
    postForm(hubUrl('/signup'), {
      username: v.username,
      email: v.email ?? '',
      signup_password: v.password,
      signup_password_confirmation: v.repeat,
      _xsrf: xsrfToken(),
    })
  return (
    <div className="doh-auth">
      <div className="doh-auth-card">
        <Brand />
        <h1 className="doh-auth-title">Create an Account</h1>
        <p className="doh-auth-sub">Duoptimum Hub</p>
        {message && <div style={{ marginBottom: 16 }}><Notice type={tone}>{message}</Notice></div>}
        <Form layout="vertical" requiredMark={false} onFinish={submit}>
          <Form.Item label="Username" name="username" rules={[{ required: true, message: 'Choose a username' }]}>
            <Input autoFocus placeholder="username" autoComplete="username" />
          </Form.Item>
          {askEmail && (
            <Form.Item label="Email" name="email" rules={[{ type: 'email', message: 'Enter a valid email' }]}>
              <Input placeholder="email" autoComplete="email" />
            </Form.Item>
          )}
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
        <div className="doh-auth-foot">Already have an account? <a href={hubUrl('/login')}>Sign in</a></div>
      </div>
    </div>
  )
}

export default function AuthApp() {
  const page = window.jhdata?.authPage
  return (
    <ThemeProvider>
      {page === 'signup' ? <AuthSignup /> : <AuthLogin />}
    </ThemeProvider>
  )
}
