/* The two-panel server block reused on both Homes: left is status + controls +
 * TTL, right is the lab's resources. Controls are mocked. */
import { Button, Card } from 'antd'
import { Icon } from './Icon'
import { StatusPill } from './StatusPill'
import { ActivityMeterFill, ResourceBars, TtlGadget } from './meters'
import { restartServer, stopServer, extendSession } from '../services/ops'
import { userServerUrl } from '../services/hub/client'
import type { ServerHero as Hero } from '../services/types'

export function ServerHero({ hero, resourcesTitle }: { hero: Hero; resourcesTitle: string }) {
  const running = hero.status === 'active' || hero.status === 'idle'
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h2 style={{ fontSize: 16, margin: 0 }}>Server status</h2>
          <StatusPill status={hero.status} label={hero.statusLabel} />
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap' }}>
          <Button type="primary" icon={<Icon name="play" size={15} filled />} onClick={() => window.location.assign(userServerUrl(hero.user))}>
            Open lab
          </Button>
          <Button icon={<Icon name="restart" size={16} />} onClick={() => restartServer(hero.user)}>
            Restart
          </Button>
          <Button danger icon={<Icon name="stop" size={14} filled />} onClick={() => stopServer(hero.user)}>
            Stop
          </Button>
        </div>
        <div style={{ marginTop: 20 }}>
          <TtlGadget timeLeftMin={hero.ttl.timeLeftMin} maxMin={hero.ttl.maxMin} onExtend={() => extendSession(hero.user, 2)} />
        </div>
      </Card>
      <Card>
        <h3 style={{ fontSize: 14, margin: '0 0 12px' }}>{resourcesTitle}</h3>
        <ResourceBars
          rows={[
            { label: 'CPU', value: hero.resources.cpu },
            { label: 'Memory', value: hero.resources.mem, tip: hero.resources.memTip },
            { label: 'GPU', value: hero.resources.gpu, gpus: hero.resources.gpus },
            {
              label: 'Activity',
              value: 0,
              valueLabel: '',
              meter: <ActivityMeterFill value={running ? hero.activity : 0} title={`${hero.activity}% active · 24h sampled`} />,
            },
          ]}
        />
      </Card>
    </div>
  )
}
