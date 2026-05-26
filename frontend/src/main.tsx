import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { ErrorBoundary } from './components/ErrorBoundary';
import { getErrorMessage, notifyError } from './lib/notify';
import { AppRouter } from './router';
import './styles/tokens.css';
import './styles/shell.css';
import './styles/components.css';
import './styles/antd-overrides.css';

dayjs.locale('ru');

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => notifyError(getErrorMessage(error, 'Ошибка загрузки данных')),
  }),
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ConfigProvider
        locale={ruRU}
        theme={{
          token: {
            colorPrimary: '#0079C2',
            colorInfo: '#0079C2',
            colorSuccess: '#1F9D5E',
            colorWarning: '#E89A14',
            colorError: '#D43232',
            colorBgLayout: '#F2F5F8',
            colorBorder: '#E4E8EC',
            colorBorderSecondary: '#EEF1F4',
            borderRadius: 8,
            fontFamily:
              "'Inter', 'Helvetica Neue', Arial, sans-serif",
            fontSize: 13,
          },
          components: {
            Layout: { siderBg: '#0079C2', headerBg: '#FFFFFF' },
          },
        }}
      >
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
        </QueryClientProvider>
      </ConfigProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
