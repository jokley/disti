import { Provider } from 'next-auth/client';
import Head from 'next/head';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { CacheProvider } from '@emotion/react';
import createEmotionCache from '../styles/createEmotionCache';

import "../styles/globals.css";
import { SWRConfig } from 'swr'
import theme from '../styles/theme';
import Header from "@components/Header";


// Client-side cache, shared for the whole session of the user in the browser.
const clientSideEmotionCache = createEmotionCache();

const fetcher = (...args) => fetch(...args).then((res) => res.json())

export default function MyApp(props) {
  const { Component, emotionCache = clientSideEmotionCache, pageProps } = props;

  return (
    <Provider>
    <CacheProvider value={emotionCache}>
       <SWRConfig value={{ fetcher }}>
      <Head>
        <title>planty</title>
        <meta name="viewport" content="initial-scale=1, width=device-width" />
      </Head>
      <ThemeProvider theme={theme}>
        {/* CssBaseline kickstart an elegant, consistent, and simple baseline to build upon. */}
        <CssBaseline />
        <Header />
        <Component {...pageProps} />
      </ThemeProvider>
      </SWRConfig>
    </CacheProvider>
    </Provider>
  );
}
