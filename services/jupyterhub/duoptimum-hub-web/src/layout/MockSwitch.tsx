/* Mock-only helper (Home only) - flip between the admin and user view and jump
 * to the design-system palette, without editing URLs. Explicitly not part of the
 * product design. */
import { useNavigate } from 'react-router-dom'
import { useRole } from '../app/RoleContext'

export function MockSwitch() {
  const { role, setRole } = useRole()
  const navigate = useNavigate()
  return (
    <div className="doh-mock-switch" title="Mock navigation helper - not part of the design">
      <b>mock</b>
      <a className={role === 'admin' ? 'on' : ''} onClick={() => setRole('admin')}>
        Admin
      </a>
      <a className={role === 'user' ? 'on' : ''} onClick={() => setRole('user')}>
        User
      </a>
      <a onClick={() => navigate('/design-system')} title="Design language palette - mock only">
        design
      </a>
    </div>
  )
}
