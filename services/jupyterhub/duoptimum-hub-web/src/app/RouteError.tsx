import { useRouteError, useNavigate } from 'react-router-dom'
import { Button, Result } from 'antd'

// Router-level error boundary. A render throw in ANY route lands here instead of
// React Router's raw default screen, which otherwise replaces the whole portal
// (one malformed row from the hub used to take down an admin's entire session).
// Wired as errorElement on the root route so it catches every child.
export function RouteError() {
  const error = useRouteError() as Error | undefined
  const navigate = useNavigate()
  return (
    <Result
      status="error"
      title="Something went wrong"
      subTitle={error?.message || 'An unexpected error occurred while rendering this page.'}
      extra={[
        <Button type="primary" key="reload" onClick={() => window.location.reload()}>
          Reload
        </Button>,
        <Button key="home" onClick={() => navigate('/home')}>
          Go to Home
        </Button>,
      ]}
    />
  )
}
