/* Sign in - standalone screen outside the app shell. NativeAuthenticator-style
 * username + password. Mocked: a valid submit drops the operator on Home. */
import { Button, Form, Input } from 'antd'
import { Link, useNavigate } from 'react-router-dom'

export default function Login() {
  const navigate = useNavigate()
  const logoSrc = `${import.meta.env.BASE_URL}brand/jh-logo.svg`
  return (
    <div className="oh-auth">
      <div className="oh-auth-card">
        <div className="oh-auth-brand"><img src={logoSrc} alt="Optimum Hub" /></div>
        <h1 className="oh-auth-title">Sign in</h1>
        <p className="oh-auth-sub">Optimum Hub</p>
        <Form layout="vertical" requiredMark={false} onFinish={() => navigate('/home')}>
          <Form.Item label="Username" name="username" rules={[{ required: true, message: 'Enter your username' }]}>
            <Input autoFocus placeholder="username" autoComplete="username" />
          </Form.Item>
          <Form.Item label="Password" name="password" rules={[{ required: true, message: 'Enter your password' }]}>
            <Input.Password placeholder="password" autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>Sign in</Button>
        </Form>
        <div className="oh-auth-foot">New here? <Link to="/signup">Create an account</Link></div>
      </div>
    </div>
  )
}
