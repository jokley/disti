import AppBar from '../components/AppBar'
import { SWRConfig } from 'swr'

const fetcher = (...args) => fetch(...args).then((res) => res.json())

function MyApp({ Component, pageProps }) {
  return (
  <>
  <SWRConfig value={{ fetcher }}>
    <AppBar/>
      <Component {...pageProps} />
  </SWRConfig>
  
  </>
  )
}

export default MyApp
