/* Dedicated Manage-volumes page: reached from the server widgets' "Manage
 * volumes" action (Home hero + Servers list). Reuses the VolumeReset panel so
 * resetting a user's volumes never drops the admin into the full Configure-user
 * screen. */
import { useParams } from 'react-router-dom'
import { Card } from 'antd'
import { PageHeader } from '../components/PageHeader'
import { VolumeReset } from '../components/VolumeReset'

export default function ManageVolumes() {
  const { name = '' } = useParams()
  return (
    <>
      <PageHeader title={`Manage volumes - ${name}`} sub="Reset this user's persistent volumes" />
      <Card style={{ maxWidth: 880 }}>
        <VolumeReset name={name} />
      </Card>
    </>
  )
}
