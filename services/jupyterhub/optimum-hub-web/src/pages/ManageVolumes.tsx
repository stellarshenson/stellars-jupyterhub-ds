/* Dedicated Manage-volumes page: reached from the server widgets' "Manage
 * volumes" action (Home hero + Servers list). Reuses the VolumeReset panel so
 * resetting a user's volumes never drops the admin into the full Configure-user
 * screen. */
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Card } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { VolumeReset } from '../components/VolumeReset'

export default function ManageVolumes() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const { state } = useLocation()
  // Cancel / Done return to where the admin opened this from (Servers list OR
  // Home), per the nav-origin state; falls back to the Servers list on a deep link.
  const backTo = (state as { from?: { to: string } } | null)?.from?.to ?? '/servers'
  return (
    <>
      <PageHeader title={`Manage volumes - ${name}`} sub="Reset this user's persistent volumes" />
      <Card style={{ maxWidth: 880 }}>
        <VolumeReset name={name} onClose={() => navigate(backTo)} />
      </Card>
    </>
  )
}
