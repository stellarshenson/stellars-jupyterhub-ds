/* Profile - self-service for both roles. A Profile tab (own name / email / password;
 * username read-only, admin-only controls absent) and an Environment tab for the
 * user's own container env vars. Name + email persist to the hub profile store, the
 * password change is real, and env vars inject into the user's lab on spawn. */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, Space, Tabs } from 'antd'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/PageHeader'
import { FormFooter } from '../components/FormFooter'
import { EnvVarEditor } from '../components/EnvVarEditor'
import type { EnvVar } from '../components/EnvVarEditor'
import { envVarsHaveErrors } from '../lib/envVars'
import { useRole } from '../app/RoleContext'
import { useUserEnvVars, useUserProfile } from '../hooks/queries'
import { changeOwnPassword, saveUserEnvVars, saveUserProfile } from '../services/ops'
import { notify } from '../services/actions'
import { genPassword } from '../lib/password'

export default function Profile() {
  const { username } = useRole()
  const navigate = useNavigate()
  const { data: profile } = useUserProfile(username)
  const { data: envData } = useUserEnvVars(username)
  const [form] = Form.useForm()
  const [pw, setPw] = useState('')
  const [cur, setCur] = useState('')
  const [tab, setTab] = useState('profile')
  const [envVars, setEnvVars] = useState<EnvVar[]>([])
  const reserved = { names: envData?.reservedNames ?? [], prefixes: envData?.reservedPrefixes ?? [] }

  // React Query resolves after mount; push the async sources into local state imperatively
  useEffect(() => {
    if (profile) form.setFieldsValue({ first: profile.firstName, last: profile.lastName, email: profile.email })
  }, [profile, form])
  useEffect(() => {
    if (envData) setEnvVars(envData.envVars.map((e) => ({ name: e.name, value: e.value, desc: e.description })))
  }, [envData])

  const save = async () => {
    try {
      const v = await form.validateFields()
      // only touch env vars when they CHANGED vs the loaded set - never REPLACE-wipe a
      // set we never loaded (envData undefined) or one the user left untouched
      const wireEnv = envVars.map((e) => ({ name: e.name, value: e.value, description: e.desc }))
      const envChanged = !!envData && JSON.stringify(wireEnv) !== JSON.stringify(envData.envVars)
      // env set never loaded (GET failed/pending) but the user typed vars -> cannot safely
      // REPLACE (prior state unknown); surface it instead of silently dropping the input
      if (!envData && envVars.some((e) => e.name.trim())) {
        setTab('environment')
        notify.error('Could not load environment variables - reload the page before editing them')
        return
      }
      // block save on a bad env-var name (reserved/invalid/duplicate) before any write
      if (envChanged && envVarsHaveErrors(envVars, reserved)) {
        setTab('environment')
        notify.error('Fix the highlighted environment variable names before saving')
        return
      }
      await saveUserProfile(username, { firstName: v.first ?? '', lastName: v.last ?? '', email: v.email ?? '' })
      if (envChanged) await saveUserEnvVars(username, wireEnv)
      if (pw) {
        await changeOwnPassword(cur, pw)
        setPw('')
        setCur('')
      }
    } catch {
      /* ops surfaced the error */
    }
  }

  const profileTab = (
    <Form form={form} layout="vertical" initialValues={{ username, first: '', last: '', email: '' }} key={username}>
      <Form.Item label="Username" name="username" extra="Your username cannot be changed">
        <Input disabled />
      </Form.Item>
      <Form.Item label="First name" name="first">
        <Input />
      </Form.Item>
      <Form.Item label="Last name" name="last">
        <Input />
      </Form.Item>
      <Form.Item label="Email" name="email">
        <Input />
      </Form.Item>
      {pw && (
        <Form.Item label="Current password" extra="Required to change your password">
          <Input.Password value={cur} onChange={(e) => setCur(e.target.value)} placeholder="current password" autoComplete="current-password" />
        </Form.Item>
      )}
      <Form.Item label="New password" extra="Leave blank to keep your current password, or generate one">
        <Space.Compact style={{ width: '100%' }}>
          <Input className="doh-mono" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="••••••••" />
          <Button onClick={() => setPw(genPassword())}>Generate</Button>
        </Space.Compact>
      </Form.Item>
    </Form>
  )

  const envTab = (
    <div>
      <div className="doh-page-sub" style={{ marginBottom: 12 }}>
        Variables injected into your lab container when it starts. Platform- and policy-owned names are reserved and cannot be set. Descriptions are notes only - they are not passed to the container.
      </div>
      <EnvVarEditor value={envVars} onChange={setEnvVars} reserved={reserved} />
    </div>
  )

  const widths: Record<string, number> = { profile: 640, environment: 880 }

  return (
    <>
      <PageHeader title="Profile" sub="Edit your own name, email, password and environment" />
      <Card style={{ maxWidth: widths[tab], transition: 'max-width .18s ease' }}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: 'profile', label: 'Profile', children: profileTab },
            { key: 'environment', label: 'Environment', children: envTab },
          ]}
        />
        <FormFooter onCancel={() => navigate(-1)} onSave={save} />
      </Card>
    </>
  )
}
