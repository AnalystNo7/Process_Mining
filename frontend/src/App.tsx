import { Layout, ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { BrowserRouter } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

export default function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <Header style={{ color: '#fff', fontSize: 18 }}>Process Mining</Header>
          <Layout>
            <Sider width={200} theme="light">
              Меню
            </Sider>
            <Content style={{ padding: 24 }}>Контент будет здесь</Content>
          </Layout>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
}
